# [KAIRO] Autonomy Level System
import streamlit as st
from core.config import LEVEL_THRESHOLDS


class LevelSystem:

    @staticmethod
    def get_level(interactions: int, crons_accepted: int, consecutive_days: int) -> int:
        if "level_override" in st.session_state and st.session_state.level_override is not None:
            return st.session_state.level_override

        level = 0
        for lvl, thresholds in sorted(LEVEL_THRESHOLDS.items()):
            if interactions >= thresholds["interactions"]:
                if lvl <= 1 or (
                    lvl == 2 and crons_accepted >= thresholds["crons_accepted"]
                ) or (
                    lvl == 3 and consecutive_days >= thresholds["consecutive_days"]
                ):
                    level = lvl
        return level

    @staticmethod
    def get_level_info(level: int) -> dict:
        info = {
            0: {
                "name": "초기 상태",
                "abilities": ["기본 에이전트 3종", "수동 크론 등록"],
                "next": "10회 상호작용으로 Lv.1 달성",
            },
            1: {
                "name": "동적 크론 추천",
                "abilities": ["기본 에이전트 3종", "수동 크론 등록", "동적 크론 추천 활성화"],
                "next": "30회 상호작용 + 크론 3회 수락으로 Lv.2 달성",
            },
            2: {
                "name": "의도 예측",
                "abilities": ["기본 에이전트 3종", "수동/동적 크론", "사용자 의도 예측 제안"],
                "next": "50회 상호작용 + 연속 7일 사용으로 Lv.3 달성",
            },
            3: {
                "name": "선제적 액션",
                "abilities": ["기본 에이전트 3종", "수동/동적 크론", "의도 예측", "선제적 액션 제안"],
                "next": "향후 확장 (Lv.4)",
            },
            4: {
                "name": "완전 자율",
                "abilities": ["모든 기능", "완전 자율 행동"],
                "next": None,
            },
        }
        return info.get(level, info[0])

    @staticmethod
    def check_level_up(old_level: int, new_level: int) -> bool:
        return new_level > old_level

    @staticmethod
    def set_override(level: int | None):
        if level is None:
            st.session_state.pop("level_override", None)
        else:
            st.session_state.level_override = level
        st.session_state.agent_level = LevelSystem.get_level(
            st.session_state.get("interaction_count", 0),
            st.session_state.get("crons_accepted", 0),
            st.session_state.get("consecutive_days", 1),
        )

    @staticmethod
    def clear_override():
        LevelSystem.set_override(None)

    @staticmethod
    def get_level_progress(interactions: int, crons_accepted: int, consecutive_days: int, current_level: int) -> dict:
        if current_level >= 3:
            return {"progress": 1.0, "message": "최고 레벨 달성!"}

        next_level = current_level + 1
        thresholds = LEVEL_THRESHOLDS.get(next_level, {})
        if not thresholds:
            return {"progress": 1.0, "message": "최고 레벨 달성!"}

        interaction_progress = min(interactions / max(thresholds["interactions"], 1), 1.0)
        crons_progress = min(crons_accepted / max(thresholds["crons_accepted"], 1), 1.0) if thresholds["crons_accepted"] > 0 else 1.0
        days_progress = min(consecutive_days / max(thresholds["consecutive_days"], 1), 1.0) if thresholds["consecutive_days"] > 0 else 1.0

        overall = min(interaction_progress, crons_progress, days_progress)

        remaining = []
        if interactions < thresholds["interactions"]:
            remaining.append(f"상호작용 {thresholds['interactions'] - interactions}회 더 필요")
        if thresholds["crons_accepted"] > 0 and crons_accepted < thresholds["crons_accepted"]:
            remaining.append(f"크론 수락 {thresholds['crons_accepted'] - crons_accepted}회 더 필요")
        if thresholds["consecutive_days"] > 0 and consecutive_days < thresholds["consecutive_days"]:
            remaining.append(f"연속 사용 {thresholds['consecutive_days'] - consecutive_days}일 더 필요")

        return {
            "progress": overall,
            "message": " | ".join(remaining) if remaining else "레벨업 임박!",
        }

    @staticmethod
    def render_sidebar(active_page: str = ""):
        current_level = st.session_state.get("agent_level", 0)
        info = LevelSystem.get_level_info(current_level)
        st.header(f"🎮 Level {current_level} — {info['name']}")
        progress = LevelSystem.get_level_progress(
            st.session_state.get("interaction_count", 0),
            st.session_state.get("crons_accepted", 0),
            st.session_state.get("consecutive_days", 1),
            current_level,
        )
        st.progress(progress["progress"])
        st.caption(progress["message"])
        st.markdown(f"**상호작용:** {st.session_state.get('interaction_count', 0)}회")

        if active_page:
            st.markdown(f"""
            <style>
            [data-testid="stSidebarNav"] a[href*="/{active_page}"],
            [data-testid="stSidebarNav"] a[href="/"] {{
                background: linear-gradient(90deg, rgba(255,75,75,0.1) 0%, transparent 100%);
                border-left: 3px solid #FF4B4B;
                font-weight: 600;
            }}
            </style>
            """, unsafe_allow_html=True)
