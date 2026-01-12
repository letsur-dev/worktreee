# PM Agent

## 개요
멀티 프로젝트 관리를 위한 대화형 PM(Project Manager) Agent.
OpenAI 호환 API를 제공하여 OpenWebUI 등에서 모델처럼 연결 가능.

## 왜 만들었나?

### 문제
- **레포가 너무 많음**: 여러 프로젝트를 동시에 관리해야 함
- **컨텍스트 스위칭 비용**: 프로젝트/태스크 간 전환 시 매번 환경 설정 필요
- **Claude 세션 관리**: 각 작업마다 새로 컨텍스트 주입해야 함
- **PR 리뷰 대응**: 리뷰 받으면 해당 작업 환경으로 다시 돌아가야 함

### 해결
```
"PRDEL-107 태스크 만들어줘"
  → 워크트리 자동 생성
  → Claude 세션 자동 시작
  → `claude --continue`로 바로 작업!
```

- **Git Worktree 자동화**: 태스크마다 독립된 워크트리, 브랜치 충돌 없음
- **Claude 세션 자동 시작**: 레포 분석 + 태스크 컨텍스트 주입 완료 상태로 시작
- **즉시 재개 가능**: PR 리뷰 받으면 `claude --continue`로 해당 세션 이어서 작업
- **멀티 머신 지원**: NUC, Mac 등 여러 머신의 프로젝트 통합 관리
- **Jira 연동**: 티켓 정보 자동 조회로 컨텍스트 확보

### 워크플로우 예시
```
1. PM Agent: "PRDEL-107 초대 기능 태스크 만들어줘"
   → 워크트리 생성, Claude 세션 시작

2. 터미널: `claude --continue`
   → 바로 작업 시작 (컨텍스트 이미 주입됨)

3. PR 제출 → 리뷰 받음

4. 터미널: `cd lamp-web-worktrees/PRDEL-107-xxx && claude --continue`
   → 리뷰 내용 반영 작업 즉시 재개
```

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
│  │     LLM Client (OpenAI)       │──────► gateway.letsur.ai
│  └───────────────────────────────┘  │
│                  │                  │
│  ┌───────────────▼───────────────┐  │
│  │         PM Tools              │  │
│  │   - add_project               │  │
│  │   - list_projects             │  │
│  │   - create_task (+ worktree   │  │
│  │       + claude session)       │  │
│  │   - delete_task               │  │
│  │   - get_status                │  │
│  │   - update_task_status        │  │
│  │   - create_worktree           │  │
│  │   - sync_worktree             │  │
│  │   - start_claude_session      │  │
│  │   - list_directory            │  │
│  │   - scan_projects             │  │
│  │   - get_jira_issue            │  │
│  │   - get_jira_issues_batch     │  │
│  │   - get_jira_graph            │  │
│  │   - analyze_jira_image        │  │
│  │   - sync_task_status          │  │
│  │   - list_branches             │  │
│  │   - get_notion_page           │  │
│  │   - search_notion             │  │
│  │   - get_task_context          │  │
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
- `include_deleted`: 삭제된 프로젝트도 포함 (기본: false)

### delete_project
프로젝트 삭제 (기본: soft delete)
- `name`: 프로젝트 이름 (필수)
- `hard`: 완전 삭제 여부 (기본: false)

### restore_project
삭제된 프로젝트 복구
- `name`: 프로젝트 이름 (필수)

### update_project
프로젝트 정보 수정
- `name`: 프로젝트 이름 (필수)
- `repo_path`: 새 레포 경로 (선택)
- `machine`: 새 머신 (선택)

### get_status
프로젝트/태스크 현황 조회
- `project`: 특정 프로젝트 (선택, 없으면 전체)

### create_task
프로젝트에 태스크 생성 (워크트리 + Claude 세션 자동 시작)
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 - 워크트리 폴더명 (필수, 예: PRDEL-107-invite-feature)
- `branch`: Git 브랜치명 (선택, 예: feature/PRDEL-107/invite-feature, 생략시 task_name 사용)
- `context`: 태스크 컨텍스트 (필수)
- `jira_key`: 연결할 Jira 이슈 키 (선택, 예: PRDEL-107)
- `notion_urls`: 연결할 Notion 문서 URL 목록 (선택)

동작:
1. 태스크 등록 → 2. 워크트리 생성 → 3. Claude 세션 자동 시작
4. 사용자가 `claude --continue`로 바로 작업 가능

### get_task_context
태스크의 전체 컨텍스트 조회 (Jira + Notion 자동 조회)
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)

반환: 태스크 정보 + 연결된 Jira 이슈 + Notion 문서 내용

### update_task_status
태스크 상태 업데이트
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `status`: pending/in_progress/completed (필수)

### list_directory
Documents 하위 디렉토리 조회
- `path`: Documents 기준 상대경로 (선택, 없으면 루트)
- `host`: 원격 호스트 별칭 (선택, 없으면 로컬)

### scan_projects
Documents 하위에서 Git 프로젝트 스캔
- `path`: Documents 기준 상대경로 (선택, 없으면 전체)
- `host`: 원격 호스트 별칭 (선택, 없으면 로컬)

### create_worktree
기존 태스크에 Git worktree 생성 (태스크 생성시 자동 호출됨)
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)

워크트리 구조 (flat + 해시):
```
{repo}-worktrees/
├── PRDEL-107-invite-a1b2c3d/   # task_name 기반 폴더명
├── PRDEL-108-login-d4e5f6g/
└── fix-build-h7i8j9k/
```
- **폴더명**: task_name 기반 (`/`는 `-`로 변환)
- **브랜치명**: branch 파라미터 사용 (feature/PROJ-123/xxx 형태 가능)
- 7자 해시 suffix 추가 (동일 이름 재생성 가능)
- 생성 전 `git fetch origin` 자동 실행

### delete_task
태스크와 연결된 워크트리를 함께 삭제
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `cleanup_worktree`: 워크트리도 삭제 (기본: true)

### sync_worktree
워크트리를 base 브랜치 기준으로 rebase
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)
- `base_branch`: rebase 기준 브랜치 (기본: develop)

> 충돌 발생시 자동으로 `git rebase --abort` 후 알림

### start_claude_session
태스크용 Claude Code 세션 시작
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (필수)

동작:
1. 워크트리에서 `claude -p "..." --print` 실행
2. 레포 분석 및 태스크 컨텍스트 이해
3. 세션 정보 저장 (호스트와 공유)
4. 사용자가 `claude --continue`로 이어서 작업

> **Note**: create_task 호출 시 자동으로 실행됨

### get_jira_issue
Jira 이슈 정보 조회
- `issue_key`: Jira 이슈 키 (필수, 예: PRDEL-107)
- `recursive`: 하위의 하위, 링크된 이슈까지 전체 트리 조회 (기본: false)
- `fetch_notion`: Notion 링크 발견시 자동 조회 (기본: true)

반환: key, summary, description, status, assignee, comments, attachments, children, linked_issues, notion_pages, **formatted** (마크다운 요약)

### get_jira_issues_batch
여러 Jira 이슈를 병렬로 빠르게 조회
- `issue_keys`: Jira 이슈 키 목록 (필수, 예: ["PRDEL-107", "PRDEL-108"])

반환: issues (키별 결과), formatted (전체 마크다운 요약)

### get_jira_graph
Jira 이슈 트리를 Mermaid 다이어그램으로 시각화
- `issue_key`: Jira 이슈 키 (필수)

반환: Mermaid 형식의 그래프 코드 (상태별 이모지, 링크 관계 포함)

### analyze_jira_image
Jira 이슈 첨부 이미지 분석 (Vision API 활용)
- `issue_key`: Jira 이슈 키 (필수)
- `attachment_index`: 이미지 인덱스, 0부터 시작 (기본: 0)
- `prompt`: 분석 요청 프롬프트 (기본: "이 이미지를 분석해주세요.")

### sync_task_status
GitHub PR 상태 기반 태스크 상태 자동 동기화
- `project`: 프로젝트 이름 (필수)
- `task_name`: 태스크 이름 (선택, 없으면 전체 태스크)

PR 상태에 따라: OPEN → in_review, MERGED → completed

### list_branches
프로젝트의 Git 브랜치 목록 조회
- `project`: 프로젝트 이름 (필수)
- `pattern`: 브랜치 필터 패턴 (선택, 예: feature/)
- `remote_only`: 리모트 브랜치만 조회 (기본: false)

### get_notion_page
Notion 페이지 내용 조회 (OAuth 토큰 사용)
- `page_url_or_id`: Notion 페이지 URL 또는 ID (필수)

> ~/.mcp-auth에 저장된 OAuth 토큰을 사용합니다.

### search_notion
Notion 워크스페이스 검색
- `query`: 검색어 (필수)
- `page_url`: 특정 페이지 내 검색 (선택)

## 환경변수

| 변수 | 설명 | 기본값 |
|-----|------|-------|
| OPENAI_BASE_URL | LLM API 엔드포인트 | https://gateway.letsur.ai/v1 |
| OPENAI_API_KEY | API 키 | - |
| OPENAI_MODEL | 사용할 모델 | claude-sonnet-4-20250514 |
| DATA_PATH | 데이터 저장 경로 | /data |
| LOCAL_BASE_PATH | 로컬 Documents 경로 | /home/amos/Documents |
| REMOTE_BASE_PATH | 원격 Documents 경로 | ~/Documents |
| LOCAL_MACHINE | 서버가 돌아가는 머신 별칭 | nuc |
| REMOTE_HOSTS | 원격 호스트 (별칭:주소) | (없음, 선택사항) |
| JIRA_URL | Jira 인스턴스 URL | (없음, 선택사항) |
| JIRA_EMAIL | Jira 계정 이메일 | (없음, 선택사항) |
| JIRA_API_TOKEN | Jira API 토큰 | (없음, 선택사항) |

> **Note**: Docker 마운트 경로와 호스트 경로를 동일하게 설정해야 git worktree가 정상 작동합니다.

## 실행

### Docker (권장)
```bash
docker compose up -d
```

Docker 볼륨 마운트:
- `/home/amos/Documents` → 로컬 프로젝트 접근
- `/home/amos/.ssh` → SSH 키 (원격 접근)
- `/home/amos/.claude` → Claude CLI 세션 공유

> **Note**: `~/.claude` 마운트로 Claude CLI 인증이 자동 공유됩니다.
> 별도의 ANTHROPIC_API_KEY 설정 불필요.

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
      PRDEL-107-invite:
        branch: feature/PRDEL-107/invite-feature
        worktree: /home/user/projects/my-project-worktrees/PRDEL-107-invite-a1b2c3d
        status: in_progress
        context: |
          초대 기능 구현
        jira_key: PRDEL-107
        notion_urls:
          - https://notion.so/Invite-Feature-Spec-abc123
        created: '2025-12-31T00:00:00'
        pr:
          number: 42
          url: https://github.com/org/repo/pull/42
          state: OPEN
```

## 로드맵

### Phase 1: MVP ✅
- [x] OpenAI 호환 API
- [x] LLM Tool Calling
- [x] 프로젝트/태스크 CRUD
- [x] 상태 저장 (YAML)
- [x] Docker 배포

### Phase 2: Git Worktree ✅
- [x] create_task에서 worktree 자동 생성
- [x] branch 자동 생성
- [x] 로컬/원격 모두 지원
- [x] delete_task로 워크트리 정리
- [x] sync_worktree로 rebase 지원
- [x] 생성 전 git fetch origin 자동 실행

### Phase 3: 원격 머신 (SSH) ✅
- [x] SSH 연결 설정
- [x] 원격 디렉토리 조회 (list_directory)
- [x] 원격 프로젝트 스캔 (scan_projects)
- [x] 멀티 호스트 지원 (REMOTE_HOSTS 환경변수)

### Phase 4: Claude Code 연동 ✅
- [x] Claude CLI 설치 (Docker)
- [x] start_claude_session 도구
- [x] ~/.claude 마운트로 세션 공유
- [x] 호스트에서 `claude --continue` 가능
- [x] create_task 시 Claude 세션 자동 시작

### Phase 5: Jira 연동 고도화 ✅
- [x] get_jira_issue 도구
- [x] Jira API 인증 (Basic Auth)
- [x] ADF (Atlassian Document Format) 파싱
- [x] 재귀적 이슈 트리 조회 (recursive)
- [x] Mermaid 그래프 시각화 (get_jira_graph)
- [x] 첨부 이미지 분석 (analyze_jira_image)
- [x] 댓글/첨부파일 조회
- [x] GitHub PR 상태 동기화 (sync_task_status)
- [x] 브랜치 목록 조회 (list_branches)

### Phase 6: Notion 연동 ✅
- [x] Notion MCP OAuth 토큰 연동 (~/.mcp-auth)
- [x] get_notion_page 도구
- [x] search_notion 도구
- [x] Jira 이슈에서 Notion 링크 자동 감지/조회
- [x] Task에 jira_key, notion_urls 연결
- [x] get_task_context로 통합 컨텍스트 조회

### Phase 7: 고도화
- [ ] 스트리밍 응답
- [ ] 웹훅/알림
