# [KAIRO] KB Manager - Read, write, update KB.md
import os
import threading
import shutil
from datetime import datetime
from typing import Optional

from core.config import KB_PATH, KB_BACKUP_PATH, KB_MAX_TOKEN_RATIO


class KBManager:

    _lock = threading.Lock()

    def __init__(self, kb_path: str = KB_PATH):
        self.kb_path = kb_path
        self.backup_path = KB_BACKUP_PATH

    def read(self) -> str:
        """Read KB.md. Auto-creates template if missing."""
        if not os.path.exists(self.kb_path):
            self._create_template()
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return f.read()

    def write(self, content: str) -> None:
        with KBManager._lock:
            self._backup()
            with open(self.kb_path, "w", encoding="utf-8") as f:
                f.write(content)

    def update_section(self, section_header: str, new_content: str) -> bool:
        with KBManager._lock:
            content = self.read()
            lines = content.split("\n")
            section_start = None
            section_end = None
            header_level = section_header.count("#")

            for i, line in enumerate(lines):
                if line.strip() == section_header:
                    section_start = i
                elif section_start is not None and line.startswith("#" * (header_level) + " ") and not line.strip().startswith(section_header):
                    section_end = i
                    break

            if section_start is not None:
                if section_end is None:
                    section_end = len(lines)
                old_section = "\n".join(lines[section_start:section_end])
                content = content.replace(old_section, new_content)
            else:
                content += f"\n\n{new_content}"

            self._backup()
            with open(self.kb_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    def append_to_section(self, section_header: str, text: str) -> bool:
        with KBManager._lock:
            content = self.read()
            lines = content.split("\n")
            header_level = section_header.count("#")
            insert_idx = None

            for i, line in enumerate(lines):
                if line.strip() == section_header:
                    insert_idx = i + 1
                    break

            if insert_idx is None:
                content += f"\n\n{section_header}\n{text}"
            else:
                lines.insert(insert_idx, text)
                content = "\n".join(lines)

            self._backup()
            with open(self.kb_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    def add_growth_log(self, message: str) -> bool:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n### {date_str}\n- {message}"
        return self.append_to_section("## 📊 Growth Log", entry)

    def increment_interaction(self) -> int:
        """Increment interaction count. Returns new count."""
        content = self.read()
        count = self._parse_interaction_count(content)
        new_count = count + 1
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        log_entry = f"\n### Interaction {new_count}\n- date: {date_str}\n- type: user_chat"

        if "## 📊 Growth Log" in content:
            self.append_to_section("## 📊 Growth Log", log_entry)
        else:
            content += f"\n\n## 📊 Growth Log{log_entry}\n"
            self.write(content)

        return new_count

    def estimate_tokens(self, content: Optional[str] = None) -> int:
        if content is None:
            content = self.read()
        return int(len(content) / 3.5)

    def needs_compression(self) -> bool:
        tokens = self.estimate_tokens()
        return tokens > (1_000_000 * KB_MAX_TOKEN_RATIO)

    def restore_backup(self) -> bool:
        if os.path.exists(self.backup_path):
            shutil.copy2(self.backup_path, self.kb_path)
            return True
        return False

    def _backup(self) -> None:
        if os.path.exists(self.kb_path):
            shutil.copy2(self.kb_path, self.backup_path)

    def _create_template(self) -> None:
        template = f"""# Kairo Knowledge Base

## 👤 User Profile
- name: (사용자 이름을 알려주세요)
- major: (전공)
- preferences: (선호하는 것들을 알려주세요)

## 📚 Projects
<!-- 프로젝트 정보가 여기에 추가됩니다 -->

## 🔧 Skills
### skill: web-research
- trigger: "검색", "찾아봐", "search"
- action: web_search(query)
- description: 웹 검색 결과 요약

### skill: planner
- trigger: "계획", "일정", "schedule"
- action: generate_plan(tasks)
- description: 작업 계획 수립

### skill: coding-helper
- trigger: "코드", "프로그래밍", "code", "디버그"
- action: help_coding(problem)
- description: 코딩 문제 해결 도움

## 🧩 Knowledge Graph (자동 발견)
<!-- 지식 간 관계가 자동으로 추가됩니다 -->

## 📊 Growth Log
<!-- 상호작용 기록이 자동으로 추가됩니다 -->
"""
        os.makedirs(os.path.dirname(self.kb_path) or ".", exist_ok=True)
        with open(self.kb_path, "w", encoding="utf-8") as f:
            f.write(template)

    @staticmethod
    def _parse_interaction_count(content: str) -> int:
        import re
        matches = re.findall(r"### Interaction (\d+)", content)
        if matches:
            return max(int(m) for m in matches)
        return 0
