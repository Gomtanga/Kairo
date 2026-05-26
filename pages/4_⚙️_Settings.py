# [KAIRO]
import streamlit as st
from core.config import read_env, save_env, reload_env
from core.llm_client import LLMClient
from core import LevelSystem

st.set_page_config(page_title="설정 - Kairo", page_icon="⚙️", layout="wide")
st.title("⚙️ 설정")

with st.sidebar:
    LevelSystem.render_sidebar("Settings")

env = read_env()

current_key = env.get("LLM_API_KEY", "")
current_url = env.get("LLM_BASE_URL", "")
current_model = env.get("LLM_MODEL", "deepseek-v4-flash")

st.subheader("🔑 API 설정")

with st.form("env_form"):
    new_key = st.text_input(
        "API 키 (LLM_API_KEY)",
        value=current_key,
        type="password",
        help="LLM API 키를 입력하세요.",
    )
    new_url = st.text_input(
        "엔드포인트 (LLM_BASE_URL)",
        value=current_url,
        help="커스텀 LLM 엔드포인트 URL을 입력하세요.",
    )
    new_model = st.text_input(
        "모델 (LLM_MODEL)",
        value=current_model,
        help="사용할 LLM 모델명 (예: deepseek-v4-flash)",
    )

    show_key = st.checkbox("API 키 표시")
    if show_key:
        st.code(new_key)

    submitted = st.form_submit_button("💾 저장")
    if submitted:
        save_env({
            "LLM_API_KEY": new_key,
            "LLM_BASE_URL": new_url,
            "LLM_MODEL": new_model,
        })
        st.success("설정이 저장되었습니다.")
        st.rerun()

st.divider()
st.subheader("🔍 연결 테스트")

if st.button("API 연결 테스트", use_container_width=True):
    with st.spinner("테스트 중..."):
        reload_env()
        llm = LLMClient()
        resp = llm.chat([{"role": "user", "content": "안녕"}], kb_content="", max_tokens=100)
    if resp.startswith("⚠️") or resp.startswith("❌") or resp.startswith("🔌") or resp.startswith("⏰") or resp.startswith("🔑") or resp.startswith("⏳"):
        st.error(resp)
    else:
        st.success(f"연결 성공! 응답: {resp[:200]}")
