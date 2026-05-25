# [KAIRO] Autonomy Level System
from core.config import LEVEL_THRESHOLDS


class LevelSystem:

    @staticmethod
    def get_level(interactions: int, crons_accepted: int, consecutive_days: int) -> int:
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
