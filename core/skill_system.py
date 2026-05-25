# [KAIRO] Skill System - manages micro/big skills defined in KB.md
import re
from typing import Optional


class SkillSystem:

    SKILL_PATTERN = re.compile(
        r"### skill:\s*(.+)\n"
        r"(?:- trigger:\s*(.+)\n)?"
        r"(?:- action:\s*(.+)\n)?"
        r"(?:- description:\s*(.+)\n)?",
        re.MULTILINE,
    )

    @staticmethod
    def parse_skills(kb_content: str) -> list[dict]:
        skills = []
        for match in SkillSystem.SKILL_PATTERN.finditer(kb_content):
            skill = {
                "name": match.group(1).strip(),
                "trigger": match.group(2).strip() if match.group(2) else "",
                "action": match.group(3).strip() if match.group(3) else "",
                "description": match.group(4).strip() if match.group(4) else "",
            }
            skills.append(skill)
        return skills

    @staticmethod
    def match_skill(query: str, skills: list[dict]) -> Optional[dict]:
        query_lower = query.lower()
        best_match = None
        best_score = 0

        for skill in skills:
            if not skill["trigger"]:
                continue
            triggers = [t.strip().strip('"').lower() for t in skill["trigger"].split(",")]
            for trigger in triggers:
                if trigger in query_lower:
                    score = len(trigger)
                    if score > best_score:
                        best_score = score
                        best_match = skill

        return best_match

    @staticmethod
    def add_skill(kb_content: str, name: str, trigger: str, action: str, description: str) -> str:
        skill_block = (
            f"\n### skill: {name}\n"
            f"- trigger: {trigger}\n"
            f"- action: {action}\n"
            f"- description: {description}\n"
        )

        skills_header = "## 🔧 Skills"
        if skills_header in kb_content:
            kb_content = kb_content.replace(
                skills_header,
                skills_header + skill_block,
            )
        else:
            kb_content += f"\n\n{skills_header}{skill_block}\n"

        return kb_content

    @staticmethod
    def remove_skill(kb_content: str, skill_name: str) -> str:
        lines = kb_content.split("\n")
        result = []
        skip = False
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()
            if stripped == f"### skill: {skill_name}":
                skip = True
                i += 1
                continue
            if skip:
                if stripped.startswith("### ") or stripped.startswith("## "):
                    skip = False
                    result.append(lines[i])
                i += 1
                continue
            result.append(lines[i])
            i += 1

        return "\n".join(result)

    @staticmethod
    def update_skill(kb_content: str, old_name: str, name: str, trigger: str, action: str, description: str) -> str:
        kb_content = SkillSystem.remove_skill(kb_content, old_name)
        kb_content = SkillSystem.add_skill(kb_content, name, trigger, action, description)
        return kb_content

    @staticmethod
    def get_default_skills() -> list[dict]:
        return [
            {
                "name": "web-research",
                "trigger": '"검색", "찾아봐", "search"',
                "action": "web_search(query)",
                "description": "웹 검색 결과 요약",
            },
            {
                "name": "planner",
                "trigger": '"계획", "일정", "schedule"',
                "action": "generate_plan(tasks)",
                "description": "작업 계획 수립",
            },
            {
                "name": "coding-helper",
                "trigger": '"코드", "프로그래밍", "code", "디버그"',
                "action": "help_coding(problem)",
                "description": "코딩 문제 해결 도움",
            },
        ]
