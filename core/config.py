# [KAIRO] Core configuration module
import os
import toml

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.toml")

# API Configuration
LLM_API_KEY = ""
LLM_BASE_URL = ""
LLM_MODEL = "deepseek-v4-flash"


def _load_toml() -> dict:
    if os.path.exists(ENV_PATH):
        try:
            data = toml.load(ENV_PATH)
            return data.get("api", {})
        except Exception:
            return {}
    return {}


def reload_env():
    global LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    env = _load_toml()
    LLM_API_KEY = env.get("LLM_API_KEY", "")
    LLM_BASE_URL = env.get("LLM_BASE_URL", "")
    LLM_MODEL = env.get("LLM_MODEL", "deepseek-v4-flash")


def save_env(values: dict):
    try:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            toml.dump({"api": values}, f)
        reload_env()
    except OSError:
        pass


def read_env() -> dict:
    return _load_toml()


reload_env()

# KB Configuration
KB_PATH = os.getenv("KB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb.md"))
KB_BACKUP_PATH = KB_PATH + ".bak"
KB_MAX_TOKEN_RATIO = 0.80  # 80% threshold for compression
MAX_SESSIONS = 50  # [KAIRO]
KB_BACKUP_DIR = KB_PATH + ".backups"  # [KAIRO]
KB_MAX_INTERACTION_LOGS = 30  # Maximum Growth Log entries before trimming

# Skills Configuration
SKILLS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills.json")

# Autonomy Level Thresholds
LEVEL_THRESHOLDS = {
    0: {"interactions": 0, "crons_accepted": 0, "consecutive_days": 0},
    1: {"interactions": 10, "crons_accepted": 0, "consecutive_days": 0},
    2: {"interactions": 30, "crons_accepted": 3, "consecutive_days": 0},
    3: {"interactions": 50, "crons_accepted": 0, "consecutive_days": 7},
    4: {"interactions": 999, "crons_accepted": 0, "consecutive_days": 999},
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

# Session
SESSION_KEY_INTERACTIONS = "interaction_count"
SESSION_KEY_LEVEL = "agent_level"
SESSION_KEY_MESSAGES = "messages"
SESSION_KEY_CRONS_ACCEPTED = "crons_accepted"
SESSION_KEY_CONSECUTIVE_DAYS = "consecutive_days"
