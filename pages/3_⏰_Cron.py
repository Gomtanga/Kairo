# [KAIRO]
import streamlit as st
from core import CronManager, LevelSystem

st.set_page_config(page_title="크론 관리 - Kairo", page_icon="⏰", layout="wide")
st.title("⏰ 크론 잡 관리")

with st.sidebar:
    LevelSystem.render_sidebar("Cron")

if "cron_manager" not in st.session_state:
    st.session_state.cron_manager = CronManager()
    st.session_state.cron_manager.start()

cron_manager = st.session_state.cron_manager

with st.expander("ℹ️ 크론 표현식 도움말", expanded=False):
    st.subheader("크론 표현식 형식")
    st.markdown(
        """
| 필드 | 의미 | 허용값 |
|------|------|--------|
| 분 | 시의 몇 분째 | 0-59 |
| 시 | 몇 시 | 0-23 |
| 일 | 달의 몇 일째 | 1-31 |
| 월 | 몇 월 | 1-12 |
| 요일 | 요일 (0=일, 1=월) | 0-6 |
"""
    )
    st.markdown("**자주 사용하는 예시**")
    st.markdown("- `0 9 * * *` — 매일 오전 9시")
    st.markdown("- `*/30 * * * *` — 30분마다")
    st.markdown("- `0 9 * * 1` — 매주 월요일 오전 9시")

st.divider()

crons = cron_manager.list_crons()

if not crons:
    st.info("등록된 크론 잡이 없습니다.")

for cron in crons:
    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 6, 3])

        with col1:
            st.markdown(f"**{cron['id']}**")
            badge_label = "정적" if cron["type"] == "static" else "동적"
            badge_color = "blue" if cron["type"] == "static" else "orange"
            st.markdown(
                f":{badge_color}-background[:{badge_color}[{badge_label}]]"
            )

        with col2:
            st.markdown(f"`{cron['cron_expr']}`")
            st.markdown(f"**{cron['task_name']}**")
            if cron.get("task_description"):
                st.caption(cron["task_description"])

        with col3:
            if cron["status"] == "active":
                st.markdown(":green-background[:green[● 활성]]")
            else:
                st.markdown(":orange-background[:orange[⏸ 일시정지]]")
            st.caption(f"등록: {cron['created']}")

        if st.session_state.get("_editing_job_id") != cron["id"]:
            a_col1, a_col2, a_col3 = st.columns([1, 1, 1])
            with a_col1:
                if cron["status"] == "active":
                    if st.button("⏸ 일시정지", key=f"pause_{cron['id']}"):
                        cron_manager.pause_cron(cron["id"])
                        st.success(f"`{cron['id']}` 일시정지되었습니다.")
                        st.rerun()
                else:
                    if st.button("▶ 재개", key=f"resume_{cron['id']}"):
                        cron_manager.resume_cron(cron["id"])
                        st.success(f"`{cron['id']}` 재개되었습니다.")
                        st.rerun()
            with a_col2:
                if st.button("🗑 삭제", key=f"remove_{cron['id']}"):
                    st.session_state["_confirm_delete"] = cron["id"]
                    st.rerun()
            with a_col3:
                pass

        if st.session_state.get("_confirm_delete") == cron["id"]:
            st.warning(f"정말 **{cron['id']}**를 삭제하시겠습니까?")
            confirm_col1, confirm_col2 = st.columns([1, 1])
            with confirm_col1:
                if st.button("예, 삭제합니다", key=f"confirm_{cron['id']}", type="primary"):
                    cron_manager.remove_cron(cron["id"])
                    st.session_state.pop("_confirm_delete", None)
                    st.success(f"`{cron['id']}` 삭제되었습니다.")
                    st.rerun()
            with confirm_col2:
                if st.button("취소", key=f"cancel_{cron['id']}"):
                    st.session_state.pop("_confirm_delete", None)
                    st.rerun()

st.divider()

st.subheader("➕ 새 크론 잡 등록")

with st.form("add_cron_form", clear_on_submit=True):
    job_id = st.text_input("잡 ID", placeholder="daily_morning_report")
    cron_expr = st.text_input(
        "크론 표현식",
        placeholder="0 9 * * *",
        help="형식: 분 시 일 월 요일 (예: 0 9 * * *)",
    )
    task_name = st.text_input("태스크 이름", placeholder="아침 보고서")
    task_description = st.text_area("태스크 설명", placeholder="매일 아침 9시에 아침 보고서를 생성합니다.")

    submitted = st.form_submit_button("등록")

    if submitted:
        if not job_id.strip():
            st.error("잡 ID를 입력해주세요.")
        elif not cron_expr.strip():
            st.error("크론 표현식을 입력해주세요.")
        elif not task_name.strip():
            st.error("태스크 이름을 입력해주세요.")
        else:
            success = cron_manager.add_static_cron(
                job_id.strip(),
                cron_expr.strip(),
                task_name.strip(),
                task_description.strip(),
            )
            if success:
                st.success(f"`{job_id.strip()}` 크론 잡이 등록되었습니다!")
                st.rerun()
            else:
                st.error("크론 잡 등록에 실패했습니다. 표현식을 확인해주세요.")
