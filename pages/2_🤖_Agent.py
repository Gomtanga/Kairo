# [KAIRO]
import streamlit as st

from core import KBManager, SkillSystem

st.set_page_config(page_title="에이전트 관리 - Kairo", page_icon="🤖", layout="wide")

st.title("🤖 에이전트 관리")

if "edit_skill_name" not in st.session_state:
    st.session_state.edit_skill_name = None

if "last_edit_skill_name" not in st.session_state:
    st.session_state.last_edit_skill_name = None

if "success_message" not in st.session_state:
    st.session_state.success_message = None

if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

if st.session_state.reset_form:
    for key in ("skill_name", "skill_trigger", "skill_action", "skill_description"):
        st.session_state.pop(key, None)
    st.session_state.reset_form = False
    st.rerun()

kb_manager = KBManager()
kb_content = kb_manager.read()
skills = SkillSystem.parse_skills(kb_content)

if st.session_state.success_message:
    st.success(st.session_state.success_message)
    st.session_state.success_message = None

st.header("📋 스킬 목록")

if not skills:
    st.info("현재 등록된 스킬이 없습니다.")
else:
    for skill in skills:
        with st.expander(skill["name"]):
            st.markdown(f"**트리거:** {skill['trigger']}")
            st.markdown(f"**액션:** {skill['action']}")
            st.markdown(f"**설명:** {skill['description']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ 수정", key=f"edit_{skill['name']}"):
                    st.session_state.edit_skill_name = skill["name"]
                    st.rerun()
            with col2:
                if st.button("🗑️ 삭제", key=f"delete_{skill['name']}"):
                    new_content = SkillSystem.remove_skill(kb_content, skill["name"])
                    kb_manager.write(new_content)
                    st.session_state.success_message = f"'{skill['name']}' 스킬이 삭제되었습니다."
                    st.rerun()

st.divider()

editing_skill_name = st.session_state.edit_skill_name
editing_skill = None
if editing_skill_name:
    editing_skill = next((s for s in skills if s["name"] == editing_skill_name), None)

if editing_skill_name and editing_skill is None:
    st.session_state.edit_skill_name = None
    st.session_state.last_edit_skill_name = None
    st.session_state.reset_form = True
    st.rerun()

if st.session_state.get("last_edit_skill_name") != editing_skill_name:
    st.session_state.last_edit_skill_name = editing_skill_name
    if editing_skill:
        st.session_state.skill_name = editing_skill["name"]
        st.session_state.skill_trigger = editing_skill["trigger"]
        st.session_state.skill_action = editing_skill["action"]
        st.session_state.skill_description = editing_skill["description"]
    else:
        st.session_state.reset_form = True
        st.rerun()

if editing_skill:
    st.header("✏️ 스킬 수정")
else:
    st.header("➕ 새 스킬 추가")

with st.form("add_skill_form"):
    name = st.text_input(
        "스킬 이름",
        value=editing_skill["name"] if editing_skill else "",
        key="skill_name",
    )
    trigger = st.text_input(
        "트리거 키워드",
        value=editing_skill["trigger"] if editing_skill else "",
        placeholder='"검색", "찾아봐", "search"',
        key="skill_trigger",
    )
    action = st.text_input(
        "액션",
        value=editing_skill["action"] if editing_skill else "",
        placeholder="web_search(query)",
        key="skill_action",
    )
    description = st.text_input(
        "설명",
        value=editing_skill["description"] if editing_skill else "",
        key="skill_description",
    )

    submitted = st.form_submit_button("💾 저장")

    if submitted:
        if not name or not trigger or not action:
            st.error("이름, 트리거, 액션은 필수 입력 항목입니다.")
        else:
            if editing_skill:
                new_content = SkillSystem.update_skill(
                    kb_content, editing_skill["name"], name, trigger, action, description
                )
                kb_manager.write(new_content)
                st.session_state.success_message = f"'{name}' 스킬이 수정되었습니다."
                st.session_state.edit_skill_name = None
                st.session_state.last_edit_skill_name = None
                st.session_state.reset_form = True
            else:
                if any(s["name"] == name for s in skills):
                    st.error(f"'{name}' 이름의 스킬이 이미 존재합니다.")
                else:
                    new_content = SkillSystem.add_skill(kb_content, name, trigger, action, description)
                    kb_manager.write(new_content)
                    st.session_state.success_message = f"'{name}' 스킬이 추가되었습니다."
                    st.session_state.reset_form = True
            st.rerun()

if editing_skill:
    if st.button("❌ 수정 취소"):
        st.session_state.edit_skill_name = None
        st.session_state.last_edit_skill_name = None
        st.session_state.reset_form = True
        st.rerun()

st.divider()
st.header("🎯 스킬 매처")

query = st.text_input("테스트 쿼리", placeholder="자연어 쿼리를 입력하세요.", key="test_query")

if query:
    matched = SkillSystem.match_skill(query, skills)
    if matched:
        st.success(f"매칭된 스킬: **{matched['name']}**")
        st.json(matched)
    else:
        st.warning("매칭된 스킬이 없습니다.")
