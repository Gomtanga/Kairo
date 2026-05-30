# [KAIRO]
import json
import os
import re
from datetime import datetime
import streamlit as st
from core import KBManager, LLMClient, LevelSystem, SkillSystem, SkillStore, BigSkillExecutor, KnowledgeGraph, ToolSystem, SessionManager, CronManager

def extract_kb_updates(response: str) -> tuple[str, list[str]]:
    display = response
    updates = re.findall(r"```kb-update\n(.*?)```", response, re.DOTALL)
    if updates:
        display = re.sub(r"```kb-update\n.*?```\n?", "", response, flags=re.DOTALL).strip()
    return display, updates


def extract_graph_edges(response: str) -> list[dict]:
    blocks = re.findall(r"```kb-graph\n(.*?)```", response, re.DOTALL)
    edges = []
    for block in blocks:
        edge = {}
        for line in block.strip().split("\n"):
            match = re.match(r"(\w+):\s*(.+)", line.strip())
            if match:
                edge[match.group(1)] = match.group(2).strip()
        if "source" in edge and "target" in edge:
            edges.append(edge)
    return edges


def extract_cron_suggestions(response: str) -> list[dict]:
    blocks = re.findall(r"```kb-cron\n(.*?)```", response, re.DOTALL)
    suggestions = []
    for block in blocks:
        cron = {}
        for line in block.strip().split("\n"):
            match = re.match(r"(\w+):\s*(.+)", line.strip())
            if match:
                cron[match.group(1)] = match.group(2).strip()
        if "name" in cron and "cron" in cron:
            suggestions.append(cron)
    return suggestions


# [KAIRO] extract tool commands from ---TOOL--- markers
def extract_tool_commands(response: str) -> list[str]:
    commands = re.findall(r"---TOOL---\s*\ncommand:\s*(.+?)\s*\n(?:---TOOL---)?", response)
    seen = []
    for cmd in commands:
        cmd = cmd.strip()
        if cmd and cmd not in seen:
            seen.append(cmd)
    return seen


def execute_tool_loop(llm_client, chat_messages, kb_content, raw_response, max_rounds=3):
    all_tool_results = []
    current_response = raw_response
    executed_commands = set()

    for round_num in range(max_rounds):
        commands = extract_tool_commands(current_response)
        new_commands = [c for c in commands if c not in executed_commands]
        if not new_commands:
            break

        tool_outputs = []
        for cmd in new_commands:
            executed_commands.add(cmd)
            result = ToolSystem.run_safe_command(cmd)
            all_tool_results.append({"command": cmd, **result})
            if result["success"]:
                tool_outputs.append(f"$ {cmd}\n{result['output']}")
            else:
                tool_outputs.append(f"$ {cmd}\nERROR: {result['error']}")

        if not tool_outputs:
            break

        tool_context = "\n".join(tool_outputs)
        followup_messages = chat_messages + [
            {"role": "assistant", "content": current_response},
            {"role": "user", "content": f"[TOOL RESULTS]\n{tool_context}\n\n위 도구 실행 결과를 반영하여 답변을 완성해주세요. 더 이상 ---TOOL--- 마커를 사용하지 마세요."},
        ]
        followup_result = llm_client.chat(followup_messages, kb_content=kb_content)
        current_response = followup_result.get("content", "") if isinstance(followup_result, dict) else followup_result

    return current_response, all_tool_results


# [KAIRO] parse markdown tables from text and render as st.dataframe
def render_markdown_tables(text: str):
    import pandas as pd
    table_pattern = re.compile(r'^\|.+\|$\n^\|[-:\s|]+\|$\n((?:^\|.+\|$\n?)+)', re.MULTILINE)
    for match in table_pattern.finditer(text):
        rows = [line.strip() for line in match.group(0).strip().split('\n') if line.strip()]
        if len(rows) < 3:
            continue
        headers = [c.strip() for c in rows[0].split('|') if c.strip()]
        data_rows = []
        for row in rows[2:]:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            data_rows.append(cells)
        if headers and data_rows:
            df = pd.DataFrame(data_rows, columns=headers)
            row_height = 35
            height = min(35 + row_height * (len(data_rows) + 1), 400)
            st.dataframe(df, width="stretch", hide_index=True, height=height)


# [KAIRO] render tool_calls-based UI widgets
def render_tool_call_widgets(tool_calls: list[dict]):
    has_any = False
    for tc in tool_calls:
        name = tc["name"]
        args = tc["arguments"]

        if name == "create_form":
            has_any = True
            with st.expander(f"📝 {args.get('title', 'Form')}", expanded=True):
                field_data = {}
                for field in args.get("fields", []):
                    fname = field.get("name", "")
                    ftype = field.get("field_type", "text")
                    fhint = field.get("hint", "")
                    if ftype == "number":
                        field_data[fname] = st.number_input(fname, help=fhint)
                    elif ftype == "textarea":
                        field_data[fname] = st.text_area(fname, help=fhint)
                    elif ftype == "select":
                        options = [o.strip() for o in fhint.split(",")] if fhint else []
                        field_data[fname] = st.selectbox(fname, options) if options else st.text_input(fname, help=fhint)
                    else:
                        field_data[fname] = st.text_input(fname, help=fhint)
                if st.button(f"제출: {args.get('title', 'Form')}", key=f"form_{args.get('title', 'form')}"):
                    st.toast(f"✅ {args.get('title', 'Form')} 제출됨!")

        elif name == "create_table":
            has_any = True
            headers = args.get("headers", [])
            rows = args.get("rows", [])
            if headers and rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=headers)
                row_height = 35
                height = min(35 + row_height * (len(rows) + 1), 400)
                st.dataframe(df, width="stretch", hide_index=True, height=height)

        elif name == "create_chart":
            has_any = True
            labels = args.get("labels", [])
            values = args.get("values", [])
            chart_type = args.get("chart_type", "bar")
            chart_data = {"항목": labels, "값": values}
            if chart_type == "line":
                st.line_chart(chart_data, x="항목", y="값", width="stretch")
            elif chart_type == "pie":
                import pandas as pd
                st.pyplot(
                    pd.DataFrame(chart_data).plot(
                        kind="pie", y="값", labels=labels, autopct="%1.1f%%", figsize=(6, 4)
                    ).figure
                )
            else:
                st.bar_chart(chart_data, x="항목", y="값", width="stretch")

        elif name == "create_button":
            has_any = True
            label = args.get("label", "버튼")
            action = args.get("action", "")
            if st.button(f"🔘 {label}", key=f"btn_{label}"):
                st.info(f"실행: {action}")

    return has_any


st.set_page_config(page_title="Chat - Kairo", page_icon="🧠", layout="wide")

@st.cache_resource
def get_kb_manager():
    return KBManager()

@st.cache_resource
def get_llm_client():
    return LLMClient()

kb = get_kb_manager()
llm = get_llm_client()

# [KAIRO] session initialization
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

with st.sidebar:
    st.title("Kairo 카이로")

    # [KAIRO] session list in sidebar
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
        selected = st.selectbox(
            "세션 선택",
            options=option_keys,
            index=current_index,
        )
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
    level_name = level_info["name"]
    st.header(f"🎮 Level {current_level} - {level_name}")
    progress_data = LevelSystem.get_level_progress(
        st.session_state.interaction_count,
        current_level,
    )
    st.progress(progress_data["progress"])
    st.caption(progress_data["message"])
    st.markdown(f"**총 상호작용:** {st.session_state.interaction_count}회")
    st.markdown(f"**KB.md 토큰:** 약 {kb.estimate_tokens():,}개")

    # [KAIRO] big skill registry
    st.divider()
    st.subheader("🏗️ 빅스킬")
    _all_skills = SkillStore.load()
    _big_skills = [s for s in _all_skills if BigSkillExecutor.is_big_skill(s)]
    if _big_skills:
        for _bs in _big_skills:
            _sub_list = ", ".join(_bs.get("sub_skills", []))
            _mode = _bs.get("execution_mode", "sequential")
            st.markdown(f"**{_bs['name']}** ({_mode})")
            st.caption(f"→ {_sub_list}")
            if st.button(f"▶ 실행: {_bs['name']}", key=f"run_bs_{_bs['name']}"):
                st.info(f"🏗️ 빅스킬 '{_bs['name']}' 실행 시작... 하위 스킬: {_sub_list}")
    else:
        st.caption("등록된 빅스킬 없음")

    # [KAIRO] tool execution log sidebar
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

SAVED_MESSAGES_PATH = os.path.join(os.path.dirname(__file__), "saved_messages.json")


def load_saved_messages() -> list[dict]:
    if os.path.exists(SAVED_MESSAGES_PATH):
        with open(SAVED_MESSAGES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_saved_messages(messages: list[dict]):
    with open(SAVED_MESSAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


@st.fragment(run_every="10s")
def _poll_cron_notifications():
    cron_notifications = CronManager.drain_pending_notifications()
    if cron_notifications:
        for notif in cron_notifications:
            task_name = notif.get("task_name", "크론 잡")
            executed_at = notif.get("executed_at", "?")
            llm_response = notif.get("llm_response", "")
            response_text = llm_response.get("content", str(llm_response)) if isinstance(llm_response, dict) else str(llm_response)
            notif_msg = f"⏰ **[{task_name}]** 실행 완료 ({executed_at})\n\n{response_text}"
            st.session_state.messages.append({"role": "assistant", "content": notif_msg})
            SessionManager.add_message(st.session_state.current_session_id, "assistant", notif_msg)
        st.rerun()

_poll_cron_notifications()

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # [KAIRO] render stored tool_calls on replay
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            render_tool_call_widgets(msg["tool_calls"])
        if msg["role"] == "assistant" and idx > 0:
            col_save, col_fork = st.columns([1, 1])
            with col_save:
                if st.button("📌 저장", key=f"save_{idx}"):
                    saved = load_saved_messages()
                    saved.append({"role": msg["role"], "content": msg["content"], "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    save_saved_messages(saved)
                    st.toast("📌 메시지가 저장되었습니다!")
            with col_fork:
                if st.button("🔀 포크", key=f"fork_{idx}"):
                    forked = SessionManager.fork_session(st.session_state.current_session_id, idx)
                    if forked:
                        st.session_state.current_session_id = forked["id"]
                        st.session_state.messages = forked["messages"]


user_input = st.chat_input("Kairo에게 메시지를 보내세요...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    SessionManager.add_message(st.session_state.current_session_id, "user", user_input)

    # [KAIRO] auto-title on first message
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

        # [KAIRO] Big Skill detection and orchestration
        big_skill_results = []
        all_skills = SkillStore.load()
        matched_big = None
        for s in all_skills:
            if BigSkillExecutor.is_big_skill(s) and SkillSystem.match_skill(user_input, [s]):
                matched_big = s
                break
        if matched_big:
            big_skill_results = BigSkillExecutor.execute(matched_big, all_skills, user_input, llm)
            steps_desc = "\n".join(
                f"  {r.get('step', '→')} {r['skill']}: {r.get('status', 'error')}"
                for r in big_skill_results
            )
            big_context = (
                f"\n\n[🏗️ 빅스킬 실행: {matched_big['name']}]\n"
                f"실행 계획:\n{steps_desc}\n"
            )
            full_context += big_context

        # [KAIRO] function calling for UI tools + streaming fallback
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

        # [KAIRO] render UI from tool_calls (must be inside chat_message)
        if tool_calls:
            render_tool_call_widgets(tool_calls)
        elif clean_display and '|' in clean_display:
            render_markdown_tables(clean_display)

    # [KAIRO] TOOL execution loop
    tool_commands = extract_tool_commands(raw_response)
    if tool_commands:
        final_response, tool_results = execute_tool_loop(
            llm, chat_messages, full_context, raw_response
        )
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

    display_response, updates = extract_kb_updates(final_response)
    graph_edges = extract_graph_edges(final_response)
    cron_suggestions = extract_cron_suggestions(final_response)
    if updates or graph_edges or cron_suggestions:
        display_response = re.sub(r"```kb-(?:update|graph|cron)\n.*?```\n?", "", display_response, flags=re.DOTALL).strip()
    display_response = re.sub(r"---TOOL---[\s\S]*?(?:---TOOL---|$)", "", display_response).strip()

    if not display_response.strip():
        # [KAIRO] fallback: use tool_calls title as display text when content is empty
        if tool_calls:
            display_response = "📊 " + tool_calls[0].get("arguments", {}).get("title", "결과를 생성했습니다")
        else:
            display_response = final_response

    # [KAIRO] persist tool_calls with message for replay on rerun
    msg_data = {"role": "assistant", "content": display_response if display_response.strip() else final_response}
    if tool_calls:
        msg_data["tool_calls"] = tool_calls
    st.session_state.messages.append(msg_data)
    SessionManager.add_message(st.session_state.current_session_id, "assistant", msg_data["content"])

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

    if cron_suggestions:
        if "pending_crons" not in st.session_state:
            st.session_state.pending_crons = []
        st.session_state.pending_crons.extend(cron_suggestions)
        st.toast(f"⏰ {len(cron_suggestions)}개 크론 잡이 제안되었습니다!", icon="⏰")

    new_count = kb.increment_interaction()
    st.session_state.interaction_count = new_count
    new_level = LevelSystem.get_level(st.session_state.interaction_count)
    if new_level > st.session_state.agent_level:
        st.session_state.agent_level = new_level
        st.balloons()
