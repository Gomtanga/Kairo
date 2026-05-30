# [KAIRO] KB Manager - Read, write, update KB.md
import os
import re
import threading
import shutil
from datetime import datetime
from typing import Optional

from core.config import KB_PATH, KB_BACKUP_PATH, KB_BACKUP_DIR, KB_MAX_TOKEN_RATIO, KB_MAX_INTERACTION_LOGS  # [KAIRO]


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
        if not content or not content.strip():  # [KAIRO]
            raise ValueError("Cannot write empty content to KB.md")
        with KBManager._lock:
            self._backup()
            try:
                with open(self.kb_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

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
            try:
                with open(self.kb_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass
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
            try:
                with open(self.kb_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass
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

        self._trim_growth_log()
        return new_count

    def _trim_growth_log(self) -> None:
        """Remove oldest interaction entries if count exceeds limit."""
        content = self.read()
        lines = content.split("\n")

        # Find the Growth Log section
        section_start = None
        for i, line in enumerate(lines):
            if line.strip() == "## 📊 Growth Log":
                section_start = i
                break
        if section_start is None:
            return

        # Collect line indices where Interaction entries begin
        entry_indices = []
        for i in range(section_start + 1, len(lines)):
            if re.match(r"^### Interaction \d+", lines[i].strip()):
                entry_indices.append(i)

        if len(entry_indices) <= KB_MAX_INTERACTION_LOGS:
            return

        # Remove the oldest entries (first ones in the section)
        remove_count = len(entry_indices) - KB_MAX_INTERACTION_LOGS
        new_lines = lines[:entry_indices[0]] + lines[entry_indices[remove_count]:]
        self.write("\n".join(new_lines))

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

    def compress(self, llm_client=None) -> tuple[bool, str]:
        """
        Compress KB.md when it exceeds the threshold.
        Preserves Tier1-2 sections, summarizes old Growth Log entries via LLM.

        Returns:
            (success: bool, message: str)
        """
        if not self.needs_compression():
            return False, "압축이 필요하지 않습니다."

        content = self.read()
        token_count = self.estimate_tokens(content)

        # Parse sections into tiers
        lines = content.split("\n")
        preserved = []
        growth_log_start = None
        growth_log_end = None
        growth_log_lines = []

        in_growth_log = False
        in_header_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Detect section headers
            if stripped.startswith("## "):
                in_header_section = True
                if stripped == "## 📊 Growth Log":
                    growth_log_start = i
                    in_growth_log = True
                    preserved.append(line)
                    continue
                else:
                    in_growth_log = False

            if in_growth_log:
                growth_log_lines.append(line)
                growth_log_end = i
            else:
                preserved.append(line)

        if not growth_log_lines or growth_log_start is None:
            return False, "Growth Log 섹션이 없어 압축할 대상이 없습니다."

        # Count entries
        entry_count = len([l for l in growth_log_lines if re.match(r"^\s*### Interaction \d+", l)])

        if entry_count <= 3:
            return False, f"Growth Log가 {entry_count}개로 충분히 적어 압축 불필요"

        # Parse entries properly
        all_entries = []
        temp_header = None
        current_entry = []
        for line in growth_log_lines:
            if re.match(r"^\s*### Interaction \d+", line):
                if temp_header and current_entry:
                    all_entries.append("\n".join([temp_header] + current_entry))
                temp_header = line
                current_entry = []
            elif temp_header:
                current_entry.append(line)
        if temp_header and current_entry:
            all_entries.append("\n".join([temp_header] + current_entry))

        if len(all_entries) <= 3:
            return False, f"Growth Log가 {len(all_entries)}개로 충분히 적어 압축 불필요"

        old_entries = all_entries[:-3]  # All but last 3
        recent_entries = all_entries[-3:]  # Last 3

        # Use LLM to summarize if available
        summary_text = ""
        if llm_client:
            old_text = "\n\n".join(old_entries)
            try:
                summary_result = llm_client.chat(
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "다음은 Kairo 에이전트의 오래된 Growth Log 항목들입니다. "
                                "이것들을 3-5줄로 간결하게 요약해주세요. "
                                "날짜 범위, 주요 활동 유형, 주요 변경사항을 포함하세요.\n\n"
                                f"{old_text}"
                            ),
                        }
                    ],
                    kb_content="",
                    temperature=0.3,
                    max_tokens=1024,
                )
                summary_content = summary_result.get("content", "") if isinstance(summary_result, dict) else str(summary_result)
                if summary_content:
                    summary_text = f"### 📋 요약 (압축)\n- summary: {summary_content}\n- 기존 {len(old_entries)}개 항목 → 요약됨\n"
            except Exception as e:
                # Fallback to basic summary
                summary_text = self._basic_summary(old_entries)
        else:
            summary_text = self._basic_summary(old_entries)

        # Rebuild Growth Log section
        compressed_section = "## 📊 Growth Log\n"
        if summary_text:
            compressed_section += f"\n{summary_text}\n"
        compressed_section += "\n" + "\n\n".join(recent_entries)

        # Rebuild full content
        preserved_text = "\n".join(preserved)
        # Find where growth log was and replace
        if growth_log_start is not None:
            before_growth = "\n".join(lines[:growth_log_start])
            after_growth = "\n".join(lines[growth_log_end + 1:]) if growth_log_end < len(lines) - 1 else ""
            new_content = before_growth.rstrip() + "\n" + compressed_section
            if after_growth.strip():
                new_content += "\n" + after_growth
        else:
            new_content = preserved_text + "\n\n" + compressed_section

        # Write compressed content
        self._backup()
        self.write(new_content)

        new_token_count = self.estimate_tokens(new_content)
        saved_tokens = token_count - new_token_count
        msg = (
            f"📦 KB.md 압축 완료! "
            f"({token_count:,} → {new_token_count:,} tokens, "
            f"{saved_tokens:,} tokens 절약, "
            f"{len(old_entries)}개 항목 요약)"
        )
        return True, msg

    def _basic_summary(self, entries: list[str]) -> str:
        """Fallback summary when LLM is not available."""
        dates = []
        types = set()
        for entry in entries:
            for line in entry.split("\n"):
                line = line.strip()
                if re.match(r"^### Interaction \d+", line):
                    continue
                if re.match(r"^- date:", line):
                    dates.append(line.split(":", 1)[1].strip())
                if re.match(r"^- type:", line):
                    types.add(line.split(":", 1)[1].strip())

        date_range = f"{dates[0]} ~ {dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "?")
        types_str = ", ".join(sorted(types)) if types else "다양"
        return (
            f"### 📋 요약 (압축)\n"
            f"- summary: {len(entries)}개 Growth Log 항목 ({date_range}) — 유형: {types_str}\n"
            f"- 기존 {len(entries)}개 항목 → 요약됨\n"
        )

    def _backup(self) -> None:
        if os.path.exists(self.kb_path):
            os.makedirs(KB_BACKUP_DIR, exist_ok=True)  # [KAIRO]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(KB_BACKUP_DIR, f"kb_{timestamp}.md.bak")
            shutil.copy2(self.kb_path, backup_file)  # [KAIRO]

    def _create_template(self) -> None:
        template = f"""# Kairo Knowledge Base

## 👤 User Profile
- name: (사용자 이름을 알려주세요)
- major: (전공)
- preferences: (선호하는 것들을 알려주세요)

## 📚 Projects
<!-- 프로젝트 정보가 여기에 추가됩니다 -->

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
        matches = re.findall(r"### Interaction (\d+)", content)
        if matches:
            return max(int(m) for m in matches)
        return 0
