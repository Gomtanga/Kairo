# [KAIRO] Tool System - safe command execution with whitelist/blacklist
import json
import os
import re
import subprocess
from datetime import datetime
from typing import Optional

TOOL_LOGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tool_logs.json")

WHITELIST = [
    r"^date\b",
    r"^ls\b",
    r"^cat\b",
    r"^echo\b",
    r"^git status\b",
    r"^git diff\b",
    r"^git log\b",
    r"^pwd\b",
    r"^wc\b",
    r"^head\b",
    r"^tail\b",
    r"^whoami\b",
    r"^uname\b",
    r"^df\b",
]

BLACKLIST_PATTERNS = [
    r"\brm\b",
    r"\bsudo\b",
    r"\bdd\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bmkfs\b",
    r"\bmv\b",
    r"\bcp\b",
    r">",
    r">>",
    r"\|",
    r";",
    r"&&",
    r"\|\|",
    r"`",
    r"\$\(",
    r"\$\( ",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\b",
    r"\bpkill\b",
    r"\bdocker\b",
    r"\bsystemctl\b",
    r"\bapt\b",
    r"\bbrew\b",
    r"\bpip\b",
    r"\bcurl\b",
    r"\bwget\b",
]


class ToolSystem:

    @staticmethod
    def run_safe_command(cmd: str, timeout: int = 10) -> dict:
        cmd = cmd.strip()
        if not cmd:
            return {"success": False, "output": "", "error": "빈 명령어입니다."}

        for pattern in BLACKLIST_PATTERNS:
            if re.search(pattern, cmd):
                ToolSystem._log(cmd, False, "", "차단된 명령어 패턴")
                return {
                    "success": False,
                    "output": "",
                    "error": f"🚫 차단된 명령어입니다 (패턴: {pattern})",
                }

        whitelisted = False
        for pattern in WHITELIST:
            if re.match(pattern, cmd):
                whitelisted = True
                break

        if not whitelisted:
            ToolSystem._log(cmd, False, "", "화이트리스트에 없는 명령어")
            return {
                "success": False,
                "output": "",
                "error": "🚫 허용되지 않은 명령어입니다.",
            }

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
            success = result.returncode == 0
            ToolSystem._log(cmd, success, output, error)
            return {
                "success": success,
                "output": output,
                "error": error,
            }
        except subprocess.TimeoutExpired:
            ToolSystem._log(cmd, False, "", "실행 시간 초과")
            return {
                "success": False,
                "output": "",
                "error": f"⏰ {timeout}초 내에 완료되지 않았습니다.",
            }
        except Exception as e:
            ToolSystem._log(cmd, False, "", str(e))
            return {
                "success": False,
                "output": "",
                "error": f"❌ 실행 오류: {e}",
            }

    @staticmethod
    def _log(cmd: str, success: bool, output: str, error: str):
        logs = ToolSystem.load_logs()
        logs.append({
            "command": cmd,
            "success": success,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output_preview": (output or error)[:100],
        })
        logs = logs[-50:]
        try:
            with open(TOOL_LOGS_PATH, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def load_logs() -> list[dict]:
        if os.path.exists(TOOL_LOGS_PATH):
            try:
                with open(TOOL_LOGS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
