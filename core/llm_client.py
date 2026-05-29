# [KAIRO] LLM Client - LLM API Client with Function Calling
import json as _json
import time as _time
import requests
from core.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TIMEOUT,
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAY,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    TOOL_WHITELIST,
)
import core.config as _cfg

# [KAIRO] UI tool definitions for function calling
UI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_form",
            "description": "Create an interactive form ONLY when the user explicitly asks to create a form, survey, or quiz. Do NOT use for information queries, fact-checking, or system commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Form title displayed to user"},
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Field label"},
                                "field_type": {"type": "string", "enum": ["text", "number", "textarea", "select"], "description": "Input widget type"},
                                "hint": {"type": "string", "description": "Placeholder or help text. For select type, provide comma-separated options"}
                            },
                            "required": ["name", "field_type"]
                        },
                        "description": "List of form fields"
                    }
                },
                "required": ["title", "fields"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_table",
            "description": "Create a data table to present structured information. Use when comparing items, listing data, or showing quiz results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Table title"},
                    "headers": {"type": "array", "items": {"type": "string"}, "description": "Column headers"},
                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "Row data as arrays of strings"}
                },
                "required": ["title", "headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Create a chart to visualize numerical data. Use when showing trends, comparisons, or distributions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie"], "description": "Type of chart"},
                    "title": {"type": "string", "description": "Chart title"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Data labels (x-axis or slice names)"},
                    "values": {"type": "array", "items": {"type": "number"}, "description": "Data values"}
                },
                "required": ["chart_type", "title", "labels", "values"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_button",
            "description": "Create an interactive button ONLY for explicit UI actions like 'submit', 'run script', 'show answer'. Do NOT use for information queries or system checks — use TOOL commands instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Button text shown to user"},
                    "action": {"type": "string", "description": "Description of what happens when clicked"}
                },
                "required": ["label", "action"]
            }
        }
    },
]


class LLMClient:

    def _refresh_config(self):
        if not self.api_key:
            _cfg.reload_env()
            self.api_key = _cfg.LLM_API_KEY
            self.base_url = _cfg.LLM_BASE_URL
            self.model = _cfg.LLM_MODEL

    def __init__(self):
        self.api_key = ""
        self.base_url = ""
        self.model = ""
        self._refresh_config()

    def chat(
        self,
        messages: list[dict],
        kb_content: str = "",
        temperature: float = None,
        max_tokens: int = None,
        use_tools: bool = False,
        agent_level: int = 0,
    ) -> dict:
        self._refresh_config()
        if not self.api_key:
            return {"content": "⚠️ API 키가 설정되지 않았습니다. .env.toml 파일을 확인해주세요.", "tool_calls": [], "reasoning": ""}

        system_prompt = self._build_system_prompt(kb_content, agent_level)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        tokens = max_tokens or LLM_MAX_TOKENS

        # [KAIRO] retry with exponential backoff for API instability
        max_attempts = LLM_MAX_RETRIES + 3
        for attempt in range(max_attempts):
            try:
                payload = {
                    "model": self.model,
                    "messages": full_messages,
                    "temperature": temperature or LLM_TEMPERATURE,
                    "max_tokens": tokens,
                }
                if use_tools:
                    payload["tools"] = UI_TOOLS

                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=LLM_TIMEOUT,
                )

                # [KAIRO] retry on 500
                if response.status_code == 500:
                    if attempt < max_attempts - 1:
                        wait = LLM_RETRY_DELAY * (2 ** min(attempt, 3))
                        _time.sleep(wait)
                        continue
                    return {"content": "❌ 서버 오류가 지속됩니다. 잠시 후 다시 시도해주세요.", "tool_calls": [], "reasoning": ""}

                response.raise_for_status()
                data = response.json()
                message = data["choices"][0]["message"]
                content = message.get("content", "") or ""
                reasoning = message.get("reasoning_content", "") or ""
                tool_calls = self._parse_tool_calls(message.get("tool_calls", []))

                if content or tool_calls:
                    return {"content": content, "tool_calls": tool_calls, "reasoning": reasoning}
                if attempt < LLM_MAX_RETRIES:
                    tokens = tokens * 2
                    continue
                return {"content": "💭 응답을 생성하는 중 시간이 부족했습니다. 다시 시도해주세요.", "tool_calls": [], "reasoning": ""}

            except requests.exceptions.Timeout:
                if attempt < max_attempts - 1:
                    wait = LLM_RETRY_DELAY * (2 ** min(attempt, 3))
                    _time.sleep(wait)
                    continue
                return {"content": "⏰ 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.", "tool_calls": [], "reasoning": ""}

            except requests.exceptions.ConnectionError:
                if attempt < max_attempts - 1:
                    _time.sleep(LLM_RETRY_DELAY)
                    continue
                return {"content": "🔌 서비스에 연결할 수 없습니다. 네트워크를 확인해주세요.", "tool_calls": [], "reasoning": ""}

            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    return {"content": "🔑 API 키가 유효하지 않습니다. .env 파일을 확인해주세요.", "tool_calls": [], "reasoning": ""}
                if response.status_code == 429:
                    if attempt < max_attempts - 1:
                        _time.sleep(LLM_RETRY_DELAY * 4)
                        continue
                    return {"content": "⏳ 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.", "tool_calls": [], "reasoning": ""}
                return {"content": f"❌ API 오류: {e}", "tool_calls": [], "reasoning": ""}

            except (KeyError, IndexError):
                return {"content": "❌ API 응답 형식 오류가 발생했습니다.", "tool_calls": [], "reasoning": ""}

            except Exception as e:
                return {"content": f"❌ 예상치 못한 오류: {e}", "tool_calls": [], "reasoning": ""}

        return {"content": "❌ 최대 재시도 횟수를 초과했습니다.", "tool_calls": [], "reasoning": ""}

    # [KAIRO] streaming chat (no tool support — tools only in non-streaming)
    def chat_stream(self, messages: list[dict], kb_content: str = "", temperature: float = None, max_tokens: int = None):
        self._refresh_config()
        if not self.api_key:
            yield "⚠️ API 키가 설정되지 않았습니다. .env.toml 파일을 확인해주세요."
            return

        system_prompt = self._build_system_prompt(kb_content)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature or LLM_TEMPERATURE,
            "max_tokens": max_tokens or LLM_MAX_TOKENS,
            "stream": True,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=LLM_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                data = decoded[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    chunk = _json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (_json.JSONDecodeError, KeyError, IndexError):
                    continue
        except requests.exceptions.Timeout:
            yield "⏰ 응답 시간이 초과되었습니다."
        except requests.exceptions.ConnectionError:
            yield "🔌 서비스에 연결할 수 없습니다."
        except Exception as e:
            yield f"❌ 스트리밍 오류: {e}"

    # [KAIRO] parse tool_calls from API response
    def _parse_tool_calls(self, raw_tool_calls: list) -> list[dict]:
        parsed = []
        if not raw_tool_calls:
            return parsed
        for tc in raw_tool_calls:
            try:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                args = _json.loads(args_str) if isinstance(args_str, str) else args_str
                parsed.append({"name": name, "arguments": args})
            except (_json.JSONDecodeError, KeyError):
                continue
        return parsed

    def _build_system_prompt(self, kb_content: str, agent_level: int = 0) -> str:
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
            "\n동적 크론 제안 규칙:\n"
            "- 사용자가 반복적인 작업, 알림, 스케줄을 언급하면 크론 잡을 제안하세요.\n"
            "- 응답 맨 끝에 다음 형식으로 추가하세요:\n"
            "```kb-cron\n"
            "name: 작업이름\ncron: */30 * * * *\naction: 실행할 작업 설명\ndescription: 왜 이 크론이 유용한지\n```\n"
            "- cron 표현식은 5필드(분 시 일 월 요일) 형식을 사용하세요.\n"
            "\n터미널 도구 규칙:\n"
            "- 시스템 정보, 파일 목록, 날짜, 파일 존재 여부 등을 확인할 때 터미널 명령어를 직접 실행하세요.\n"
            "- 응답에 다음 형식으로 명령어를 포함하세요:\n"
            "---TOOL---\n"
            "command: ls pages/\n"
            "---TOOL---\n"
            "- 사용 가능한 명령어: " + ", ".join(TOOL_WHITELIST) + "\n"
            "- 위험한 명령어(rm, sudo 등)는 실행할 수 없습니다.\n"
            "- 한 응답에 여러 명령어를 실행할 수 있습니다.\n"
            "- 중요: 사용자가 시스템 정보, 파일 상태, 명령어 실행을 요청하면 반드시 터미널 도구로 먼저 실행하세요. create_button으로 '확인' 버튼을 만들지 마세요.\n"
            "\nUI 도구 사용 규칙:\n"
            "- 표, 폼, 차트, 버튼을 만들어야 할 때 제공된 도구(create_table, create_form, create_chart, create_button)를 호출하세요.\n"
            "- 텍스트로 표를 그리거나 폼 형식을 설명하는 대신, 반드시 도구를 호출하세요.\n"
            "- 사용자가 '표로 만들어', '폼 만들어', '차트 그려' 등이라고 요청하면 반드시 해당 도구를 호출하세요.\n"
            "- 퀴즈, 설문, 비교 등 구조화된 정보를 제시할 때도 적극적으로 도구를 활용하세요.\n"
            "- 주의: create_button은 사용자가 UI 인터랙션을 요청할 때만 사용하세요. 명령어 실행이나 정보 조회에는 터미널 도구를 사용하세요.\n"
        )

        if agent_level >= 2:
            prompt += (
                "\n\n[현재 자율 레벨 2 — 의도 예측 모드]\n"
                "사용자의 질문 의도를 예측하여 먼저 제안하세요.\n"
                "예: 사용자가 '내일 날씨'를 물으면 날씨 정보와 함께 '일정표도 확인할까요?'라고 제안하세요.\n"
                "사용자가 하려는 행동을 미리 파악하고 관련된 추가 도움을 적극 제안하세요.\n"
            )

        if agent_level >= 3:
            prompt += (
                "\n\n[현재 자율 레벨 3 — 선제적 액션 모드]\n"
                "사용자가 질문하기 전에도 필요한 정보를 먼저 제공하세요.\n"
                "시간대에 맞는 제안을 우선하세요 (아침: 일정/날씨, 저녁: 복습/정리).\n"
                "오랜만에 접속한 사용자에게는 변화된 내용을 요약해서 알려주세요.\n"
            )

        if kb_content:
            prompt += f"\n---\n## KB.md (Knowledge Base)\n{kb_content}\n---\n"

        return prompt
