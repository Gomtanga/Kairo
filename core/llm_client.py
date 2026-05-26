# [KAIRO] LLM Client - DeepSeek V4 Flash via Jiminbox API
import requests
from core.config import (
    JIMINBOX_API_KEY,
    JIMINBOX_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAY,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


class LLMClient:

    def __init__(self):
        self.api_key = JIMINBOX_API_KEY
        self.base_url = JIMINBOX_BASE_URL
        self.model = LLM_MODEL

    def chat(
        self,
        messages: list[dict],
        kb_content: str = "",
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        if not self.api_key:
            return "⚠️ API 키가 설정되지 않았습니다. .env.toml 파일을 확인해주세요."

        system_prompt = self._build_system_prompt(kb_content)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        tokens = max_tokens or LLM_MAX_TOKENS

        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                payload = {
                    "model": self.model,
                    "messages": full_messages,
                    "temperature": temperature or LLM_TEMPERATURE,
                    "max_tokens": tokens,
                }
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=LLM_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                message = data["choices"][0]["message"]
                content = message.get("content", "")
                if content:
                    return content
                if attempt < LLM_MAX_RETRIES:
                    tokens = tokens * 2
                    continue
                return "💭 응답을 생성하는 중 시간이 부족했습니다. 다시 시도해주세요."

            except requests.exceptions.Timeout:
                if attempt < LLM_MAX_RETRIES:
                    import time
                    time.sleep(LLM_RETRY_DELAY)
                    continue
                return "⏰ 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."

            except requests.exceptions.ConnectionError:
                return "🔌 서비스에 연결할 수 없습니다. 네트워크를 확인해주세요."

            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    return "🔑 API 키가 유효하지 않습니다. .env 파일을 확인해주세요."
                if response.status_code == 429:
                    return "⏳ 요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
                return f"❌ API 오류: {e}"

            except (KeyError, IndexError):
                return "❌ API 응답 형식 오류가 발생했습니다."

            except Exception as e:
                return f"❌ 예상치 못한 오류: {e}"

        return "❌ 최대 재시도 횟수를 초과했습니다."

    def _build_system_prompt(self, kb_content: str) -> str:
        prompt = (
            "당신은 Kairo(카이로)입니다 — 사용자와 함께 성장하는 개인 지식 에이전트입니다.\n"
            "아래 KB.md 내용을 바탕으로 사용자를 도와주세요.\n\n"
            "지침:\n"
            "1. KB.md의 사용자 프로필을 기반으로 개인화된 답변을 제공하세요.\n"
            "2. KB.md에 정의된 스킬이 질문과 관련 있으면 활용하세요.\n"
            "3. 새로운 정보를 얻었다면 KB.md에 추가할 내용을 제안하세요.\n"
            "4. 지식 간 연결을 발견하면 알려주세요.\n"
            "5. 한국어로 친근하게 대화하세요.\n\n"
            "KB.md 업데이트 규칙:\n"
            "- 사용자가 이름, 전공, 취향 등 개인정보를 알려주면 User Profile 섹션을 업데이트하세요.\n"
            "- 새로운 프로젝트 정보가 나오면 Projects 섹션에 추가하세요.\n"
            "- 업데이트가 필요할 경우, 응답 맨 끝에 다음 형식으로 블록을 추가하세요:\n"
            "```kb-update\n"
            "## 👤 User Profile\n"
            "- name: 곰탕\n"
            "- major: Computer Science\n"
            "```\n"
            "- 여러 섹션을 업데이트하려면 ```kb-update 블록을 여러 개 사용하세요.\n"
            "- 블록 안에는 해당 섹션의 헤더(`## `)와 전체 내용을 포함하세요.\n"
            "\n지식 그래프 엣지 규칙:\n"
            "- 대화 중 두 개념의 관계를 발견하면 응답 맨 끝에 다음 형식으로 추가하세요:\n"
            "```kb-graph\n"
            "source: 개념A\ntarget: 개념B\ntype: 관계유형\n```\n"
            "- type 예시: related_to, depends_on, part_of, leads_to\n"
        )

        if kb_content:
            prompt += f"\n---\n## KB.md (Knowledge Base)\n{kb_content}\n---\n"

        return prompt
