# [KAIRO] Skill System - fuzzy Korean skill matching with kiwipiepy + rapidfuzz
import re
from typing import Optional
from rapidfuzz import fuzz as _fuzz

_kiwi = None


def _get_kiwi():
    global _kiwi
    if _kiwi is None:
        try:
            from kiwipiepy import Kiwi
            _kiwi = Kiwi()
        except Exception:
            _kiwi = False
    return _kiwi if _kiwi else None


def _extract_stems(text: str) -> set[str]:
    kiwi = _get_kiwi()
    if not kiwi:
        return set()
    stems = set()
    try:
        for token in kiwi.tokenize(text):
            if token.tag in ("VV", "VA", "VX", "NNG", "NNP", "NP"):
                stems.add(token.form)
                if len(token.form) >= 2:
                    stems.add(token.form[0])
    except Exception:
        pass
    return stems


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
        query_stems = _extract_stems(query)
        best = None

        for skill in skills:
            if not skill["trigger"]:
                continue
            triggers = [t.strip().strip('"').lower() for t in skill["trigger"].split(",")]
            for trigger in triggers:
                score = 0
                method = ""

                if trigger in query_lower:
                    score = 100
                    method = "exact"
                else:
                    trigger_stems = _extract_stems(trigger)
                    common = query_stems & trigger_stems
                    if common:
                        score = 85 + min(len(common) * 3, 10)
                        method = "stem"
                    else:
                        fuzzy = _fuzz.partial_ratio(trigger, query_lower)
                        if fuzzy >= 60:
                            score = int(fuzzy * 0.9)
                            method = "fuzzy"

                if score > 0 and (best is None or score > best["score"]):
                    best = {
                        "skill": skill,
                        "matched_keyword": trigger,
                        "score": score,
                        "method": method,
                    }

        return best

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
