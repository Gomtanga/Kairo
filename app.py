# [KAIRO]
import json
import os
import re
import streamlit as st
from core import KBManager, LLMClient, LevelSystem, SkillSystem, SkillStore, KnowledgeGraph, ToolSystem

CHAT_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "chat_history.json")


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
        current_response = llm_client.chat(followup_messages, kb_content=kb_content)

    return current_response, all_tool_results


# [KAIRO] extract and render dynamic forms
def extract_forms(response: str) -> list[dict]:
    blocks = re.findall(r"---FORM---\s*\n(.*?)\n---FORM_END---", response, re.DOTALL)
    forms = []
    for block in blocks:
        form = {"title": "Form", "fields": []}
        for line in block.strip().split("\n"):
            line = line.strip()
            if line.startswith("title:"):
                form["title"] = line[6:].strip()
            elif line.startswith("field:"):
                parts = line[6:].strip().split("|")
                if len(parts) >= 2:
                    field = {
                        "name": parts[0].strip(),
                        "type": parts[1].strip(),
                        "hint": parts[2].strip() if len(parts) > 2 else "",
                    }
                    form["fields"].append(field)
        if form["fields"]:
            forms.append(form)
    return forms


def render_forms(forms: list[dict]) -> dict:
    results = {}
    for form in forms:
        with st.expander(f"📝 {form['title']}", expanded=True):
            field_data = {}
            for field in form["fields"]:
                ftype = field["type"]
                fname = field["name"]
                fhint = field["hint"]
                if ftype == "number":
                    field_data[fname] = st.number_input(fname, help=fhint)
                elif ftype == "textarea":
                    field_data[fname] = st.text_area(fname, help=fhint)
                elif ftype == "select":
                    options = [o.strip() for o in fhint.split(",")]
                    field_data[fname] = st.selectbox(fname, options)
                else:
                    field_data[fname] = st.text_input(fname, help=fhint)
            if st.button(f"제출: {form['title']}", key=f"form_{form['title']}"):
                results.update(field_data)
                st.toast(f"✅ {form['title']} 제출됨!")
    return results


def load_chat_history() -> list[dict]:
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_chat_history(messages: list[dict]):
    with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

st.set_page_config(page_title="Kairo", page_icon="🧠", layout="wide")

kb = KBManager()
llm = LLMClient()

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()
if "interaction_count" not in st.session_state:
    count = kb._parse_interaction_count(kb.read())
    st.session_state.interaction_count = count
if "agent_level" not in st.session_state:
    interactions = st.session_state.interaction_count
    crons = st.session_state.get("crons_accepted", 0)
    consecutive = st.session_state.get("consecutive_days", 1)
    st.session_state.agent_level = LevelSystem.get_level(interactions, crons, consecutive)
if "crons_accepted" not in st.session_state:
    st.session_state.crons_accepted = 0
if "consecutive_days" not in st.session_state:
    st.session_state.consecutive_days = 1

with st.sidebar:
    st.title("Kairo 카이로")
    current_level = st.session_state.agent_level
    level_info = LevelSystem.get_level_info(current_level)
    level_name = level_info["name"]
    st.header(f"🎮 Level {current_level} - {level_name}")
    progress_data = LevelSystem.get_level_progress(
        st.session_state.interaction_count,
        st.session_state.crons_accepted,
        st.session_state.consecutive_days,
        current_level,
    )
    st.progress(progress_data["progress"])
    st.caption(progress_data["message"])
    st.markdown(f"**총 상호작용:** {st.session_state.interaction_count}회")
    st.markdown(f"**KB.md 토큰:** 약 {kb.estimate_tokens():,}개")

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Kairo에게 메시지를 보내세요...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_chat_history(st.session_state.messages)

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

        # [KAIRO] try streaming, fallback to sync
        streamed_text = ""
        try:
            stream_gen = llm.chat_stream(chat_messages, kb_content=full_context)
            streamed_text = st.write_stream(stream_gen)
        except Exception:
            with st.spinner("💭 생성 중..."):
                streamed_text = llm.chat(chat_messages, kb_content=full_context)
            st.markdown(streamed_text)
        raw_response = streamed_text

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
    dynamic_forms = extract_forms(final_response)
    if updates or graph_edges or cron_suggestions:
        display_response = re.sub(r"```kb-(?:update|graph|cron)\n.*?```\n?", "", display_response, flags=re.DOTALL).strip()
    display_response = re.sub(r"---TOOL---\s*\ncommand:.*?\n(?:---TOOL---\s*\n?)?", "", display_response, flags=re.DOTALL).strip()
    display_response = re.sub(r"---FORM---\s*\n.*?\n---FORM_END---", "", display_response, flags=re.DOTALL).strip()

    if not display_response.strip():
        display_response = final_response

    if dynamic_forms:
        render_forms(dynamic_forms)

    st.session_state.messages.append({"role": "assistant", "content": display_response if display_response.strip() else final_response})
    save_chat_history(st.session_state.messages)

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
    new_level = LevelSystem.get_level(
        st.session_state.interaction_count,
        st.session_state.crons_accepted,
        st.session_state.consecutive_days,
    )
    if new_level > st.session_state.agent_level:
        st.session_state.agent_level = new_level
        st.balloons()
