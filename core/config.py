# [KAIRO] Core configuration module
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
JIMINBOX_API_KEY = os.getenv("JIMINBOX_API_KEY", "")
JIMINBOX_BASE_URL = os.getenv("JIMINBOX_BASE_URL", "https://api.jiminbox.ai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# KB Configuration
KB_PATH = os.getenv("KB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "kb.md"))
KB_BACKUP_PATH = KB_PATH + ".bak"
KB_MAX_TOKEN_RATIO = 0.80  # 80% threshold for compression

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
LLM_TIMEOUT = 30  # seconds
LLM_MAX_RETRIES = 1
LLM_RETRY_DELAY = 5  # seconds
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.7

# Cron Configuration
CRON_MAX_RETRIES = 3

# Session
SESSION_KEY_INTERACTIONS = "interaction_count"
SESSION_KEY_LEVEL = "agent_level"
SESSION_KEY_MESSAGES = "messages"
SESSION_KEY_CRONS_ACCEPTED = "crons_accepted"
SESSION_KEY_CONSECUTIVE_DAYS = "consecutive_days"
