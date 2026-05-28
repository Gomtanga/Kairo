# [KAIRO] Session Manager - multi-session chat management
import json
import os
import shutil
from datetime import datetime

from core.config import MAX_SESSIONS  # [KAIRO]

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions")


class SessionManager:

    @staticmethod
    def _ensure_dir():
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    @staticmethod
    def create_session(title: str = None) -> dict:
        SessionManager._ensure_dir()
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session = {
            "id": session_id,
            "title": title or f"새 대화 {session_id}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": [],
        }
        SessionManager._save(session)
        SessionManager._cleanup_old_sessions()  # [KAIRO]
        return session

    @staticmethod
    def load_session(session_id: str) -> dict:
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def _save(session: dict):
        SessionManager._ensure_dir()
        session["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join(SESSIONS_DIR, f"{session['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _cleanup_old_sessions():  # [KAIRO]
        SessionManager._ensure_dir()
        sessions = SessionManager.list_sessions()
        if len(sessions) > MAX_SESSIONS:
            to_delete = sessions[MAX_SESSIONS:]
            for s in to_delete:
                SessionManager.delete_session(s["id"])

    @staticmethod
    def list_sessions() -> list[dict]:
        SessionManager._ensure_dir()
        sessions = []
        for fname in sorted(os.listdir(SESSIONS_DIR), reverse=True):
            if fname.endswith(".json"):
                path = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        s = json.load(f)
                    sessions.append({
                        "id": s["id"],
                        "title": s["title"],
                        "created_at": s["created_at"],
                        "updated_at": s["updated_at"],
                        "message_count": len(s.get("messages", [])),
                    })
                except Exception:
                    pass
        return sessions

    @staticmethod
    def delete_session(session_id: str):
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def add_message(session_id: str, role: str, content: str):
        session = SessionManager.load_session(session_id)
        if not session:
            return
        session["messages"].append({"role": role, "content": content})
        SessionManager._save(session)

    @staticmethod
    def update_title(session_id: str, title: str):
        session = SessionManager.load_session(session_id)
        if not session:
            return
        session["title"] = title
        SessionManager._save(session)

    @staticmethod
    def fork_session(session_id: str, fork_from_index: int) -> dict:
        source = SessionManager.load_session(session_id)
        if not source:
            return None
        new_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        forked = {
            "id": new_id,
            "title": f"[FORK] {source['title']}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": source["messages"][:fork_from_index + 1],
        }
        SessionManager._save(forked)
        return forked
