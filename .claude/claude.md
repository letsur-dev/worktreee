# PM Agent

## 개요
멀티 프로젝트 관리를 위한 대화형 PM(Project Manager) Agent.
OpenAI 호환 API를 제공하여 OpenWebUI 등에서 모델처럼 연결 가능.

## 아키텍처

```
OpenWebUI / Client
       │
       ▼ POST /v1/chat/completions
┌─────────────────────────────────────┐
│         PM Agent Server             │
│                                     │
│  ┌───────────────────────────────┐  │
│  │   OpenAI 호환 API Layer       │  │
│  │   - POST /v1/chat/completions │  │
│  │   - GET /v1/models            │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │        Agent Core             │  │
│  │   - System Prompt             │  │
│  │   - Tool Calling Loop         │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │     LLM Client (LiteLLM)      │──────► gateway.letsur.ai
│  └───────────────────────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │         PM Tools              │  │
│  │   - add_project               │  │
│  │   - list_projects             │  │
│  │   - create_task               │  │
│  │   - get_status                │  │
│  │   - update_task_status        │  │
│  │   - add_report                │  │
│  └───────────────┬───────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │       State Manager           │  │
│  │   - data/projects.yaml        │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## 기술 스택

| 구성요소 | 기술 |
|---------|------|
| 언어 | Python 3.11+ |
| 프레임워크 | FastAPI |
| 패키지 관리 | uv |
| LLM 호출 | openai 라이브러리 |
| 상태 저장 | YAML 파일 |
| 컨테이너 | Docker |

## 프로젝트 구조

```
pm-worktree/
├── main.py                 # FastAPI 앱 진입점
├── config.py               # 설정 (환경변수)
├── pyproject.toml          # 의존성 정의
├── Dockerfile
├── docker-compose.yaml
├── .env                    # API 키 (gitignore)
│
├── api/
│   ├── __init__.py
│   └── openai_compat.py    # OpenAI 호환 API
│
├── agent/
│   ├── __init__.py
│   ├── core.py             # Agent 핵심 로직
│   ├── llm.py              # LLM 클라이언트
│   └── tools.py            # PM 도구 정의
│
├── state/
│   ├── __init__.py
│   └── manager.py          # 상태 관리
│
├── pm/                     # (Phase 2: worktree, SSH)
│   └── __init__.py
│
└── data/
    └── projects.yaml       # 프로젝트 상태 저장
```

## API 엔드포인트

### GET /
서버 상태 확인
```json
{"name": "PM Agent", "version": "0.1.0", "status": "running"}
```

### GET /v1/models
사용 가능한 모델 목록
```json
{"object": "list", "data": [{"id": "pm-agent", ...}]}
```

### POST /v1/chat/completions
OpenAI 호환 채팅 API
```json
{
  "model": "pm-agent",
  "messages": [{"role": "user", "content": "프로젝트 목록 보여줘"}],
  "stream": false
}
```

## PM Tools

### add_project
새 프로젝트 등록
- `name`: 프로젝트 이름 (필수)
- `repo_path`: Git 레포 경로 (필수)
- `machine`: 실행 머신 - local/mac/nuc (기본: local)

### list_projects
등록된 프로젝트 목록 조회

### get_status
프로젝트/태스크 현황 조회
- `project`: 특정 프로젝트 (선택, 없으면 전체)

### create_task
프로젝트에 태스크 생성
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `context`: 태스크 컨텍스트 (필수)

### update_task_status
태스크 상태 업데이트
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `status`: pending/in_progress/completed (필수)

### add_report
태스크에 진행 보고 추가
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `content`: 보고 내용 (필수)

## 환경변수

| 변수 | 설명 | 기본값 |
|-----|------|-------|
| LITELLM_ENDPOINT | LLM API 엔드포인트 | https://gateway.letsur.ai/v1 |
| LITELLM_API_KEY | API 키 | - |
| LITELLM_MODEL | 사용할 모델 | claude-opus-4-5-20251101 |
| DATA_PATH | 데이터 저장 경로 | /data |

## 실행

### Docker (권장)
```bash
docker compose up -d
```

### 로컬 개발
```bash
uv run uvicorn main:app --reload
```

## 연결 정보

- **로컬**: http://localhost:9001
- **Tailscale**: http://100.119.182.54:9001
- **OpenWebUI Endpoint**: http://100.119.182.54:9001/v1

## 상태 저장 형식

```yaml
# data/projects.yaml
projects:
  my-project:
    repo_path: /home/user/projects/my-project
    machine: nuc
    created: '2025-12-31T00:00:00'
    tasks:
      feature-auth:
        branch: feature-auth
        worktree: null  # Phase 2
        status: in_progress
        context: |
          인증 기능 구현
        created: '2025-12-31T00:00:00'
        reports:
          - date: '2025-12-31T00:00:00'
            content: "기본 구조 완료"
```

## 로드맵

### Phase 1: MVP ✅
- [x] OpenAI 호환 API
- [x] LLM Tool Calling
- [x] 프로젝트/태스크 CRUD
- [x] 상태 저장 (YAML)
- [x] Docker 배포

### Phase 2: Git Worktree
- [ ] create_task에서 worktree 자동 생성
- [ ] branch 자동 생성
- [ ] 태스크 context 파일 생성

### Phase 3: 원격 머신 (SSH)
- [ ] SSH 연결 설정
- [ ] 원격 명령 실행
- [ ] 멀티 머신 지원

### Phase 4: 고도화
- [ ] 스트리밍 응답
- [ ] Git 동기화
- [ ] 웹훅/알림
