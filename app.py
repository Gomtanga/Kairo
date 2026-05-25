# [KAIRO]
import streamlit as st
from core import KBManager, LLMClient, LevelSystem, SkillSystem

st.set_page_config(page_title="Kairo", page_icon="🧠", layout="wide")

kb = KBManager()
llm = LLMClient()

if "messages" not in st.session_state:
    st.session_state.messages = []
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

    chat_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]
    kb_content = kb.read()
    response = llm.chat(chat_messages, kb_content=kb_content)

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

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
