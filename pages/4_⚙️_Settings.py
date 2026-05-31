# [KAIRO]
import streamlit as st
from core.config import read_env, save_env, reload_env
from core.llm_client import LLMClient
from core import LevelSystem

@st.cache_resource
def get_llm_client():
    return LLMClient()

st.set_page_config(page_title="설정 - Kairo", page_icon="⚙️", layout="wide")
st.title("⚙️ 설정")

with st.sidebar:
    LevelSystem.render_sidebar("Settings")

env = read_env()

current_key = env.get("LLM_API_KEY", "")
current_url = env.get("LLM_BASE_URL", "")
current_model = env.get("LLM_MODEL", "deepseek-v4-flash")

st.subheader("🔑 API 설정")

# 현재 설정값 요약 표시 (form 밖에서 실시간 확인 가능)
with st.expander("🔍 현재 설정값 확인", expanded=False):
    st.text(f"LLM_API_KEY: {current_key[:12]}...{current_key[-4:]}" if len(current_key) > 16 else (f"LLM_API_KEY: {current_key}" if current_key else "LLM_API_KEY: (설정되지 않음)"))
    st.text(f"LLM_BASE_URL: {current_url or '(설정되지 않음)'}")
    st.text(f"LLM_MODEL: {current_model}")

try:
    import streamlit as _st
    if hasattr(_st, "secrets") and "api" in _st.secrets:
        st.info("📡 Streamlit Cloud `st.secrets`에서 API 설정을 감지했습니다. 아래에서 덮어쓸 수 있습니다.")
except Exception:
    pass

with st.form("env_form"):
    # show_key checkbox → form 밖으로 뺄 수 없으니, type을 조건부로 변경
    show_key = st.checkbox("👁️ API 키 표시 (저장 후 확인)", help="체크하고 저장하면 키가 평문으로 표시됩니다.")
    new_key = st.text_input(
        "API 키 (LLM_API_KEY)",
        value=current_key,
        type="default" if show_key else "password",
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

if st.button("API 연결 테스트", width="stretch"):
    with st.spinner("테스트 중..."):
        reload_env()
        llm = get_llm_client()
        resp = llm.chat([{"role": "user", "content": "안녕"}], kb_content="", max_tokens=100)
    resp_text = resp.get("content", "") if isinstance(resp, dict) else str(resp)
    if resp_text.startswith("⚠️") or resp_text.startswith("❌") or resp_text.startswith("🔌") or resp_text.startswith("⏰") or resp_text.startswith("🔑") or resp_text.startswith("⏳"):
        st.error(resp_text)
    else:
        st.success(f"연결 성공! 응답: {resp_text[:200]}")

st.divider()
st.subheader("🧠 사고 과정")

show_reasoning = st.toggle(
    "LLM 사고 과정 표시",
    value=st.session_state.get("show_reasoning", False),
    help="켜면 LLM 응답에 사고 과정(reasoning)을 expander로 표시합니다.",
)
st.session_state.show_reasoning = show_reasoning
if show_reasoning:
    st.caption("🧠 채팅 응답에서 사고 과정을 확인할 수 있습니다.")

st.divider()
st.subheader("🎮 레벨 시스템")

current_level = st.session_state.get("agent_level", 0)
level_info = LevelSystem.get_level_info(current_level)
has_override = "level_override" in st.session_state and st.session_state.level_override is not None

col1, col2, col3 = st.columns(3)
col1.metric("현재 레벨", f"Lv.{current_level}")
col2.metric("레벨명", level_info["name"])
col3.metric("수동 설정", "ON" if has_override else "OFF")

with st.expander("🔧 레벨 수동 조작", expanded=has_override):
    st.caption(
        "자동 레벨업이 정상 동작하지 않을 때 수동으로 레벨을 설정할 수 있습니다. "
        "수동 설정 시 자동 레벨업이 비활성화됩니다."
    )

    override_level = st.selectbox(
        "레벨 선택",
        options=[0, 1, 2, 3, 4],
        format_func=lambda l: f"Lv.{l} — {LevelSystem.get_level_info(l)['name']}",
        index=st.session_state.get("level_override", current_level) if has_override else current_level,
    )

    bc1, bc2 = st.columns(2)
    if bc1.button("적용", use_container_width=True, type="primary"):
        LevelSystem.set_override(override_level)
        st.success(f"Lv.{override_level}으로 수동 설정되었습니다.")
        st.rerun()

    if bc2.button("자동으로 복원", use_container_width=True, disabled=not has_override):
        LevelSystem.clear_override()
        st.success("자동 레벨 시스템으로 복원되었습니다.")
        st.rerun()

st.divider()
st.subheader("📊 상태 카운터")

new_interactions = st.number_input(
    "상호작용 횟수",
    min_value=0,
    max_value=9999,
    value=st.session_state.get("interaction_count", 0),
)

if st.button("카운터 저장", width="stretch"):
    st.session_state.interaction_count = new_interactions
    if not has_override:
        st.session_state.agent_level = LevelSystem.get_level(new_interactions)
    st.success("카운터가 업데이트되었습니다.")
    st.rerun()
