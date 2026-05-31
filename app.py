# [KAIRO] Main Streamlit chat app — thin UI layer
import os
import re
from datetime import datetime

import streamlit as st

from core import (
    KBManager, LLMClient, LevelSystem, SkillStore,
    KnowledgeGraph, ToolSystem, SessionManager, CronManager,
)
from core import chat_engine as ce
from core import ui_helpers as ui

st.set_page_config(page_title="Chat - Kairo", page_icon="🧠", layout="wide")


@st.cache_resource
def get_kb_manager():
    return KBManager()


def get_llm_client():
    return LLMClient()


kb = get_kb_manager()
llm = get_llm_client()

# --- Session initialization ---
if "current_session_id" not in st.session_state:
    sessions = SessionManager.list_sessions()
    if sessions:
        st.session_state.current_session_id = sessions[0]["id"]
    else:
        new_session = SessionManager.create_session()
        st.session_state.current_session_id = new_session["id"]

if "messages" not in st.session_state:
    session = SessionManager.load_session(st.session_state.current_session_id)
    st.session_state.messages = session["messages"] if session else []
if "interaction_count" not in st.session_state:
    count = kb._parse_interaction_count(kb.read())
    st.session_state.interaction_count = count
if "agent_level" not in st.session_state:
    st.session_state.agent_level = LevelSystem.get_level(st.session_state.interaction_count)
if "graph_discovered" not in st.session_state:
    kb_content = kb.read()
    discovered = KnowledgeGraph.discover_edges_from_kb(kb_content)
    if discovered:
        for edge in discovered:
            kb_content = KnowledgeGraph.add_edge(
                kb_content,
                source=edge["source"],
                target=edge["target"],
                edge_type=edge["type"],
            )
        kb.write(kb_content)
    st.session_state.graph_discovered = True

# --- Sidebar ---
with st.sidebar:
    st.title("Kairo 카이로")

    st.subheader("💬 대화 세션")
    sessions = SessionManager.list_sessions()
    session_options = {f"{s['title']} ({s['message_count']}msg)": s["id"] for s in sessions}
    if session_options:
        option_keys = list(session_options.keys())
        current_id = st.session_state.current_session_id
        current_index = 0
        for i, key in enumerate(option_keys):
            if session_options[key] == current_id:
                current_index = i
                break
        selected = st.selectbox("세션 선택", options=option_keys, index=current_index)

        if st.button("➕ 새 세션"):
            new_s = SessionManager.create_session()
            st.session_state.current_session_id = new_s["id"]
            st.session_state.messages = []
            st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑 삭제"):
                SessionManager.delete_session(st.session_state.current_session_id)
                remaining = SessionManager.list_sessions()
                if remaining:
                    st.session_state.current_session_id = remaining[0]["id"]
                else:
                    new_s = SessionManager.create_session()
                    st.session_state.current_session_id = new_s["id"]
                session = SessionManager.load_session(st.session_state.current_session_id)
                st.session_state.messages = session["messages"] if session else []
                st.rerun()
        with col2:
            new_title = st.text_input("제목 변경", value="", placeholder="새 제목", label_visibility="collapsed")
            if new_title and st.button("✏️ 변경"):
                SessionManager.update_title(st.session_state.current_session_id, new_title)
                st.rerun()

        selected_id = session_options.get(selected)
        if selected_id and selected_id != st.session_state.current_session_id:
            st.session_state.current_session_id = selected_id
            session = SessionManager.load_session(selected_id)
            st.session_state.messages = session["messages"] if session else []
            st.rerun()

    st.divider()
    current_level = st.session_state.agent_level
    level_info = LevelSystem.get_level_info(current_level)
    st.header(f"🎮 Level {current_level} - {level_info['name']}")
    progress_data = LevelSystem.get_level_progress(
        st.session_state.interaction_count, current_level,
    )
    st.progress(progress_data["progress"])
    st.caption(progress_data["message"])
    st.markdown(f"**총 상호작용:** {st.session_state.interaction_count}회")
    st.markdown(f"**KB.md 토큰:** 약 {kb.estimate_tokens():,}개")

    # Tool execution log
    tool_logs = ToolSystem.load_logs()
    if tool_logs:
        recent = tool_logs[-5:][::-1]
        st.divider()
        st.subheader("🛠 도구 실행 로그")
        for log in recent:
            icon = "✅" if log["success"] else "❌"
            ts = log.get("timestamp", "")
            preview = log.get("output_preview", "")[:60]
            st.caption(f"{icon} `{log['command']}` _{ts}_")
            if preview:
                st.code(preview, language="bash")


# --- Cron notification polling ---
@st.fragment(run_every="10s")
def _poll_cron_notifications():
    cron_notifications = CronManager.drain_pending_notifications()
    if cron_notifications:
        for notif in cron_notifications:
            task_name = notif.get("task_name", "크론 잡")
            executed_at = notif.get("executed_at", "?")
            llm_response = notif.get("llm_response", "")
            response_text = llm_response.get("content", str(llm_response)) if isinstance(llm_response, dict) else str(llm_response)
            msg = f"⏰ **[{task_name}]** 실행 완료 ({executed_at})\n\n{response_text}"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            SessionManager.add_message(st.session_state.current_session_id, "assistant", msg)
        st.rerun()


_poll_cron_notifications()

# --- Message history ---
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            ui.render_tool_call_widgets(msg["tool_calls"])
        if msg["role"] == "assistant" and idx > 0:
            col_save, col_fork = st.columns([1, 1])
            with col_save:
                if st.button("📌 저장", key=f"save_{idx}"):
                    saved = ui.load_saved_messages()
                    saved.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    ui.save_saved_messages(saved)
                    st.toast("📌 메시지가 저장되었습니다!")
            with col_fork:
                if st.button("🔀 포크", key=f"fork_{idx}"):
                    forked = SessionManager.fork_session(st.session_state.current_session_id, idx)
                    if forked:
                        st.session_state.current_session_id = forked["id"]
                        st.session_state.messages = forked["messages"]

# --- Chat input ---
user_input = st.chat_input("Kairo에게 메시지를 보내세요...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    SessionManager.add_message(st.session_state.current_session_id, "user", user_input)

    # Auto-title on first message
    current_session = SessionManager.load_session(st.session_state.current_session_id)
    if current_session and current_session.get("title", "").startswith("새 대화"):
        auto_title = user_input[:20].strip() + ("..." if len(user_input) > 20 else "")
        SessionManager.update_title(st.session_state.current_session_id, auto_title)

    with st.chat_message("assistant"):
        chat_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]
        kb_content = kb.read()
        if "## 🔧 Skills" in kb_content:
            kb_content = SkillStore.migrate_from_kb(kb_content)
            kb.write(kb_content)
        skills_section = SkillStore.to_kb_section(SkillStore.load())
        full_context = kb_content + "\n\n" + skills_section if skills_section else kb_content

        # LLM call
        with st.spinner("💭 생각 중..."):
            result = llm.chat(chat_messages, kb_content=full_context, use_tools=True, agent_level=st.session_state.agent_level)
        streamed_text = result.get("content", "")
        tool_calls = result.get("tool_calls", [])
        reasoning = result.get("reasoning", "")

        if reasoning and st.session_state.get("show_reasoning", False):
            with st.expander("🧠 사고 과정", expanded=False):
                st.markdown(reasoning)

        clean_display = re.sub(r"---TOOL---[\s\S]*?(?:---TOOL---|$)", "", streamed_text).strip()
        clean_display = re.sub(r"```kb-(?:update|graph|cron)\n.*?```\n?", "", clean_display, flags=re.DOTALL).strip()
        if clean_display:
            st.markdown(clean_display)
        raw_response = streamed_text

        # Render UI widgets
        if tool_calls:
            ui.render_tool_call_widgets(tool_calls)
        elif clean_display and "|" in clean_display:
            ui.render_markdown_tables(clean_display)

    # Tool execution loop
    tool_commands = ce.extract_tool_commands(raw_response)
    if tool_commands:
        final_response, tool_results = ce.execute_tool_loop(llm, chat_messages, full_context, raw_response)
        if tool_results:
            for tr in tool_results:
                icon = "✅" if tr["success"] else "❌"
                status = tr.get("output", "") or tr.get("error", "")
                status_preview = status[:200] + ("..." if len(status) > 200 else "")
                st.info(f"🛠 `{tr['command']}` {icon}\n```\n{status_preview}\n```")
        with st.chat_message("assistant"):
            st.markdown(final_response)
    else:
        final_response = raw_response

    # Parse structured blocks
    display_response, updates = ce.extract_kb_updates(final_response)
    graph_edges = ce.extract_graph_edges(final_response)
    cron_suggestions = ce.extract_cron_suggestions(final_response)
    if updates or graph_edges or cron_suggestions:
        display_response = re.sub(r"```kb-(?:update|graph|cron)\n.*?```\n?", "", display_response, flags=re.DOTALL).strip()
    display_response = re.sub(r"---TOOL---[\s\S]*?(?:---TOOL---|$)", "", display_response).strip()

    if not display_response.strip():
        if tool_calls:
            display_response = "📊 " + tool_calls[0].get("arguments", {}).get("title", "결과를 생성했습니다")
        else:
            display_response = final_response

    # Persist message
    msg_data = {"role": "assistant", "content": display_response if display_response.strip() else final_response}
    if tool_calls:
        msg_data["tool_calls"] = tool_calls
    st.session_state.messages.append(msg_data)
    SessionManager.add_message(st.session_state.current_session_id, "assistant", msg_data["content"])

    # Handle KB updates
    if updates:
        current_kb = kb.read()
        for update_block in updates:
            lines = update_block.strip().split("\n")
            for line in lines:
                if line.startswith("## "):
                    kb.update_section(line.strip(), update_block.strip())
                    break
            else:
                current_kb += f"\n\n{update_block.strip()}"
                kb.write(current_kb)
        st.toast("📝 KB.md가 업데이트되었습니다!", icon="📝")

    # Handle graph edges
    if graph_edges:
        current_kb = kb.read()
        for edge in graph_edges:
            current_kb = KnowledgeGraph.add_edge(
                current_kb,
                source=edge["source"],
                target=edge["target"],
                edge_type=edge.get("type", "related_to"),
            )
        kb.write(current_kb)
        st.toast(f"🧩 {len(graph_edges)}개 지식 연결이 발견되었습니다!", icon="🧩")

    # Handle cron suggestions
    if cron_suggestions:
        if "pending_crons" not in st.session_state:
            st.session_state.pending_crons = []
        st.session_state.pending_crons.extend(cron_suggestions)
        st.toast(f"⏰ {len(cron_suggestions)}개 크론 잡이 제안되었습니다!", icon="⏰")

    # Level & interaction
    new_count = kb.increment_interaction()
    st.session_state.interaction_count = new_count
    new_level = LevelSystem.get_level(st.session_state.interaction_count)
    if new_level > st.session_state.agent_level:
        st.session_state.agent_level = new_level
        st.balloons()
