# Project Kairo 🧠

> **Knowledge Base가 하나의 파일로, 에이전트는 그걸 읽고 자란다.**
> Karpathy의 LLM Wiki 철학 + DeepSeek V4 Flash 1M Context의 만남

---

## 개요

Kairo는 하나의 마크다운 파일(`KB.md`)로 모든 지식을 관리하는 개인 AI 에이전트 시스템입니다.
RAG(임베딩/벡터DB/청킹) 없이, DeepSeek V4 Flash의 1M 컨텍스트 윈도우에
KB.md를 통째로 넣어 처리하는 독창적인 접근법을 사용합니다.

### 핵심 철학
- **"RAG를 구축할 시간에, KB.md를 채워라"**
- **"단순함이 곧 완성도"** — 복잡한 인프라 없이 하나의 파일로 모든 지식 관리
- **"함께 성장한다"** — 사용자 상호작용이 쌓일수록 에이전트가 진화

---

## 주요 기능

| 기능 | 설명 | 상태 |
|------|------|:----:|
| 💬 **채팅 인터페이스** | 멀티세션, 포크, 자동 제목 생성 | ✅ |
| 📝 **KB.md 기반 지식 관리** | 단일 파일로 User Profile, Projects, Skills 통합 관리 | ✅ |
| 🧩 **지식 그래프 자동발견 + 시각화** | 기존 KB.md 스캔 + 채팅 중 관계 추출 → `st.graphviz_chart()` 시각화 | ✅ |
| 🗺️ **지식 그래프 시각화 전용 페이지** | 독립된 페이지에서 지식 그래프를 탐색하고 필터링 | ✅ |
| ⏰ **크론 시스템** | 정적/동적 크론, APScheduler 자동 실행, 채팅 알림, created_by 뱃지(👤/🤖) | ✅ |
| 🎮 **자율주행 레벨 시스템** | Lv.0~4, Settings에서 수동 오버라이드 가능 | ✅ |
| 🛠️ **스킬 시스템** | 트리거 키워드 기반 자동 매칭 (web-research, planner 등) | ✅ |
| 🖥️ **터미널 도구** | 화이트리스트 기반 안전한 셸 명령어 실행, Settings에서 설정 가능 | ✅ |
| 🎨 **동적 UI 생성** | DeepSeek Function Calling으로 실시간 표/차트/폼 생성 | ✅ |
| 🧠 **사고 과정 토글** | Settings에서 LLM reasoning 표시/숨김 전환 | ✅ |

---

## 아키텍처

```
사용자 ←→ Streamlit UI (WebSocket)
                ↓
        Kairo Agent (LLM Inference)
        - KB.md (전체 내용)
        - Skills 목록
        - Level 정보
                ↓
    ┌───────┬──────┬──────┬──────┐
    ▼       ▼      ▼      ▼      ▼
  KB.md   Skills  Cron   Tools Sessions
  저장     매칭    스케줄  실행   관리

Core 모듈:
  ├─ core/chat_engine.py — LLM 응답 처리 & Function Calling 오케스트레이션
  └─ core/ui_helpers.py  — Streamlit UI 렌더링 헬퍼 (동적 위젯, 그래프 페이지)

LLM 응답 처리:
  ├─ kb-update → KB.md 자동 업데이트
  ├─ kb-cron   → 크론 추천 / 등록
  ├─ kb-graph  → 지식 관계 저장
  └─ TOOL      → 터미널 명령어 실행
```

---

## 오픈소스 스택

| 오픈소스 | 라이선스 | 활용 |
|----------|---------|------|
| [Streamlit](https://streamlit.io) | Apache 2.0 | 웹 UI (채팅, 시각화, 그래프) |
| [DeepSeek V4 Flash](https://github.com/deepseek-ai/DeepSeek-V4) | MIT | LLM 추론, Function Calling |
| [APScheduler](https://github.com/agronholm/apscheduler) | MIT / Apache 2.0 | 크론 스케줄링 |
| [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) | MIT | 퍼지 문자열 매칭 |
| [Kiwi](https://github.com/bab2min/kiwipiepy) | LGPL | 한국어 형태소 분석 |

### 참고한 프로젝트 (철학/영감)

| 프로젝트 | 설명 | 영향 |
|----------|------|------|
| [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | "LLM이 유지보수하는 영속적인 위키" 패턴 | **KB.md 철학의 근간.** RAG 대신 LLM이 직접 지식을 축적/관리하는 개념을 차용 |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | 자기 수정 프롬프트 + 스킬 시스템 | 레벨 기반 자율주행 아키텍처와 동적 크론 시스템에 영감 |

---

## 시작하기

**요구사항:** Python 3.11+ (`runtime.txt`에 명시)

```bash
# 1. 클론
git clone https://github.com/Gomtanga/Kairo.git
cd Kairo

# 2. 의존성 설치
pip install streamlit apscheduler python-dotenv requests rapidfuzz kiwipiepy

# 3. 환경변수 설정
cat > .env.toml << 'EOF'
[api]
LLM_API_KEY = "your-api-key"
LLM_BASE_URL = "https://your-endpoint.com/v1"
LLM_MODEL = "deepseek-v4-flash"
EOF

# 4. 실행
streamlit run app.py
```

---

## GitHub 협업 현황

| 항목 | 수치 |
|------|:----:|
| 토탈 PRs | **70개 머지** |
| Open Issues | 9개 (2개 Low-priority Open) |
| Unit Tests | 133개+ |
| 브랜치 전략 | feature/fix 브랜치 → Squash Merge → main |
| 이슈 관리 | GitHub Projects 칸반 (Todo → In Progress → Done) |
| 문서화 | GitHub Wiki 10페이지 |
| 저장소 | **Public** (github.com/Gomtanga/Kairo) |
| 개발 기간 | 1주일 (2026.05.22~28) |

### 최근 업데이트 (2026.05.28, 17개 PR)

- #54 fix(tool-execution) — LLM이 create_button 남발하던 문제 수정
- #55 feat(level-aware-prompts) — Lv.2 의도예측 + Lv.3 선제액션 프롬프트
- #56 feat(cron-notifications) — 크론 실행 결과 채팅 전달
- #57 fix(three-hotfixes) — 그래프 특수문자 + 툴 우선순위 + 크론 폴링
- #58 feat(auto-discover-graph) — KB.md 기반 지식 그래프 자동 발견
- #59 fix(remove-noise-edges) — 의미 없는 섹션 간 엣지 제거
- #60 feat(level-override) — Settings 수동 레벨 조작
- #61 refactor(level-interactions-only) — 레벨 단순화
- #62 fix(cron-created-by) — 크론 created_by 뱃지 (👤/🤖)
- #63 refactor(rename-pages) — 사이드바 이름 변경
- #64 feat(reasoning-toggle) — Settings에서 LLM 사고 과정 토글
- #65 refactor(tool-whitelist) — 화이트리스트 config.py 중앙 통합
- #66 fix(kb-compression) — KB.md 자동 압축 (임계값 초과 시 LLM 요약)
- #67 fix(settings-env) — .env.toml 키 변경 (JIMINBOX_* → LLM_*)
- #68 refactor(bigskill-tier) — SkillStore에 big skill 계층 추가
- #69 feat(knowledge-graph-page) — 지식 그래프 시각화 전용 페이지
- #70 refactor(cleanup-bigskill-split-app) — BigSkillExecutor 제거, app.py 분할, Codex 리뷰 반영

---

## 팀

| 역할 | 이름 | 주요 기여 |
|------|------|---------|
| 팀장 / 에이전트 엔진 | **박건영** | 70+ PRs, 아키텍처, 지식그래프, 레벨시스템 |
| 팀원 / 품질 관리 | **오충만** | PR #42 Growth Log 정리, Git 충돌 해결 |

---

## 라이선스

MIT
