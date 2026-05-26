# [KAIRO]
import json
import os
import re
import streamlit as st
from core import KBManager, LLMClient, LevelSystem, SkillSystem, SkillStore

CHAT_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "chat_history.json")


def extract_kb_updates(response: str) -> tuple[str, list[str]]:
    display = response
    updates = re.findall(r"```kb-update\n(.*?)```", response, re.DOTALL)
    if updates:
        display = re.sub(r"```kb-update\n.*?```\n?", "", response, flags=re.DOTALL).strip()
    return display, updates


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
        with st.spinner("💭 생성 중..."):
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
            raw_response = llm.chat(chat_messages, kb_content=full_context)

    display_response, updates = extract_kb_updates(raw_response)

    if not display_response.strip():
        display_response = raw_response

    with st.chat_message("assistant"):
        st.markdown(display_response)
    st.session_state.messages.append({"role": "assistant", "content": display_response})
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
