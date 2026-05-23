# Project Kairo 🧠

> **Knowledge Base가 하나의 파일로, 에이전트는 그걸 읽고 자란다.**
> Karpathy의 LLM Wiki 철학 + DeepSeek V4 Flash 1M Context의 만남

---

## 개요

Kairo는 하나의 마크다운 파일(`KB.md`)로 모든 지식을 관리하는 개인 에이전트 시스템입니다.
RAG(임베딩/벡터DB/청킹) 없이, DeepSeek V4 Flash의 1M 컨텍스트 윈도우에
KB.md를 통째로 넣어 처리하는 독창적인 접근법을 사용합니다.

### 핵심 철학
- **"RAG를 구축할 시간에, KB.md를 채워라"**
- **"단순함이 곧 완성도"** — 복잡한 인프라 없이 하나의 파일로 모든 지식 관리
- **"함께 성장한다"** — 사용자 상호작용이 쌓일수록 에이전트가 진화

---

## 아키텍처

```
사용자 ←→ Streamlit UI
                ↓
        Kairo Agent (LLM)
        DeepSeek V4 Flash
         1M context window
         Jiminbox API
                ↓
        KB.md (Knowledge Base)
        - User Profile
        - Project Knowledge
        - Skills 정의
        - Knowledge Graph
        - Growth Log
```

### 왜 RAG를 안 쓰는가?
| 항목 | RAG 방식 | Kairo 방식 |
|------|:--------:|:----------:|
| 구축 시간 | 2~3일 | 몇 시간 |
| 임베딩/벡터DB | 필요 | ❌ **불필요** |
| 유지보수 | 복잡 | ✅ **KB.md 하나만 관리** |
| LLM 활용 | 검색 + 생성 | ✅ **전체 지식 + 추론** |

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **📝 KB.md 기반 지식 관리** | 하나의 마크다운 파일에 모든 지식 저장 |
| **🧠 DeepSeek V4 Flash 연동** | 1M context, 초저비용 API 호출 |
| **🎮 자율주행 레벨 시스템** | 상호작용 쌓이면 레벨업 |
| **🔧 스킬 시스템** | 마이크로스킬 + 빅스킬 계층 구조 |
| **⏰ 동적 크론 잡** (MVP 이후) | 사용자 패턴 기반 자동 작업 생성 |
| **🔗 지식 자율 결합** | LLM이 지식 간 관계 발견 |

---

## 기술 스택

- **Frontend**: Streamlit
- **LLM**: DeepSeek V4 Flash (Jiminbox API)
- **지식 저장**: KB.md (단일 마크다운 파일)
- **스케줄링**: APScheduler
- **배포**: Streamlit Community Cloud

---

## 사용 오픈소스

| 오픈소스 | 라이선스 | 활용 |
|----------|---------|------|
| Streamlit | Apache 2.0 | 웹 UI |
| APScheduler | MIT | 동적 크론 |
| python-dotenv | BSD | 환경변수 |
| Karpathy's LLM Wiki | (참고) | 지식파일 철학 |
| Hermes Agent | (참고) | 자율주행 개념 |

---

## 시작하기

> 🚧 **현재 MVP 개발 중입니다.** 아래는 계획된 실행 구조입니다.

```bash
git clone https://github.com/Gomtanga/Kairo.git
cd Kairo

# 의존성 설치 (MVP 완성 시)
pip install streamlit apscheduler python-dotenv requests

# 환경변수 설정
echo "JIMINBOX_API_KEY=your_key" > .env

# 실행 (MVP 완성 시)
streamlit run app.py
```

---

## 팀

| 역할 | 이름 |
|------|------|
| 팀장 / 에이전트 엔진 | 곰탕 |
| 프론트엔드 / 문서화 | (팀원) |
| 데이터 / 발표 | (팀원) |

---

## 라이선스

MIT
