# [KAIRO] Core configuration module
import os
import toml

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.toml")

# API Configuration
LLM_API_KEY = ""
LLM_BASE_URL = ""
LLM_MODEL = "deepseek-v4-flash"

_in_memory_env: dict = {}


def _load_toml() -> dict:
    if os.path.exists(ENV_PATH):
        try:
            data = toml.load(ENV_PATH)
            return data.get("api", {})
        except Exception:
            return {}
    return {}


def _load_secrets() -> dict:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "api" in st.secrets:
            return dict(st.secrets["api"])
    except Exception:
        pass
    return {}


def _load_env_vars() -> dict:
    result = {}
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        val = os.getenv(key)
        if val:
            result[key] = val
    return result


def _get_value(key: str, file_env: dict, secrets_env: dict, os_env: dict, default: str = "") -> str:
    if key in _in_memory_env:
        v = _in_memory_env[key]
        if v:
            return v
    if key in file_env:
        v = file_env[key]
        if v:
            return v
    if key in secrets_env:
        v = str(secrets_env[key])
        if v:
            return v
    if key in os_env:
        v = os_env[key]
        if v:
            return v
    return default


def reload_env():
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    file_env = _load_toml()
    secrets_env = _load_secrets()
    os_env = _load_env_vars()
    LLM_API_KEY = _get_value("LLM_API_KEY", file_env, secrets_env, os_env, "")
    LLM_BASE_URL = _get_value("LLM_BASE_URL", file_env, secrets_env, os_env, "")
    LLM_MODEL = _get_value("LLM_MODEL", file_env, secrets_env, os_env, "deepseek-v4-flash")


def save_env(values: dict):
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    _in_memory_env.update(values)
    try:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            toml.dump({"api": values}, f)
    except OSError:
        pass
    reload_env()


def read_env() -> dict:
    file_env = _load_toml()
    merged = {**file_env, **_in_memory_env}
    if not merged.get("LLM_API_KEY") and LLM_API_KEY:
        merged["LLM_API_KEY"] = LLM_API_KEY
    if not merged.get("LLM_BASE_URL") and LLM_BASE_URL:
        merged["LLM_BASE_URL"] = LLM_BASE_URL
    if not merged.get("LLM_MODEL") and LLM_MODEL:
        merged["LLM_MODEL"] = LLM_MODEL
    return merged


reload_env()

# KB Configuration
KB_PATH = os.getenv("KB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb.md"))
KB_BACKUP_PATH = KB_PATH + ".bak"
KB_MAX_TOKEN_RATIO = 0.80  # 80% threshold for compression
MAX_SESSIONS = 50  # [KAIRO]
KB_BACKUP_DIR = KB_PATH + ".backups"  # [KAIRO]
KB_MAX_INTERACTION_LOGS = 10

# Skills Configuration
SKILLS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills.json")

# Autonomy Level Thresholds
LEVEL_THRESHOLDS = {
    0: {"interactions": 0},
    1: {"interactions": 10},
    2: {"interactions": 30},
    3: {"interactions": 50},
    4: {"interactions": 999},
}

# Context Budget
CONTEXT_BUDGET = {
    "kb_ratio": 0.80,
    "conversation_ratio": 0.15,
    "system_ratio": 0.05,
}

# LLM Parameters
LLM_TIMEOUT = 60
LLM_MAX_RETRIES = 1
LLM_RETRY_DELAY = 5  # seconds
LLM_MAX_TOKENS = 8192
LLM_TEMPERATURE = 0.7

# Cron Configuration
CRON_MAX_RETRIES = 3

# Tool System Configuration
TOOL_WHITELIST = [
    "date",
    "ls",
    "cat",
    "echo",
    "git status",
    "git diff",
    "git log",
    "pwd",
    "wc",
    "head",
    "tail",
    "whoami",
    "uname",
    "df",
]

TOOL_BLACKLIST_PATTERNS = [
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

# Session
SESSION_KEY_INTERACTIONS = "interaction_count"
SESSION_KEY_LEVEL = "agent_level"
SESSION_KEY_MESSAGES = "messages"
