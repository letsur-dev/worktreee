# Worktreee (업무나무우)

Claude Code를 태스크별 전담 개발자로 만드는 워크트리 기반 프로젝트 관리 에이전트.

## Why

여러 레포를 오가며 Claude Code로 작업하면, 태스크마다 같은 셋업을 반복하게 됩니다:

```
Jira 티켓 확인 → 브랜치 생성 → 워크트리 만들기 → fetch →
Claude 열기 → "이 레포는..." 설명 → "Jira 내용은..." 붙여넣기 → 작업 시작
```

5분짜리 셋업 x 하루 10번 = 50분. PR 리뷰가 오면 또 그 환경으로 돌아가야 합니다.

Worktreee는 이 전체를 **한 마디**로 줄입니다:

```
"PROJ-107 초대 기능 태스크 만들어줘"
  → Git worktree 자동 생성
  → Jira 티켓 + Notion 문서 자동 조회
  → Claude 세션 시작 (컨텍스트 주입 완료)
  → `claude --continue`로 바로 작업 시작
```

## Key Idea: 컨텍스트 스위칭 비용 → 0

Worktreee의 핵심은 **"돌아오기"가 공짜**라는 점입니다.

| | 일반적인 방식 | Worktreee |
|---|---|---|
| **태스크 시작** | 수동 셋업 5분 | 한 마디 → 즉시 |
| **태스크 전환** | stash → checkout → 컨텍스트 재주입 | `cd` → `claude --continue` |
| **PR 리뷰 대응** | 환경 복원 → Claude에 다시 설명 | `cd worktree/ && claude --continue` |
| **Claude 활용** | 매번 처음부터 레포 설명 | Jira+Notion 자동 주입, 세션 유지 |
| **동시 작업** | 브랜치 충돌, stash 지옥 | 워크트리별 완전 격리 |

Git worktree로 각 태스크가 **독립된 디렉토리**이기 때문에, 브랜치 전환도, stash도, 컨텍스트 재주입도 필요 없습니다. 그냥 `cd`하고 `claude --continue`.

## Workflow

```
1. Worktreee에게: "PROJ-107 초대 기능 태스크 만들어줘"
   → 워크트리 생성, Claude 세션 시작 (Jira/Notion 컨텍스트 주입)

2. 터미널: claude --continue
   → 바로 작업 시작 — Claude가 이미 티켓 내용을 알고 있음

3. PR 제출 → 다른 태스크 작업 중 → 리뷰 도착

4. 터미널: cd my-project-worktrees/PROJ-107-xxx && claude --continue
   → Claude가 이전 작업 맥락을 기억한 상태로 리뷰 대응
   → stash 없음, 브랜치 전환 없음, 재설명 없음
```

## Features

### Git Worktree Automation
태스크마다 독립된 워크트리를 자동 생성합니다. `git fetch` → 브랜치 생성 → 워크트리 설정을 한 번에 처리하고, 태스크 삭제 시 워크트리도 함께 정리됩니다.

### Claude Code Session Management
워크트리 생성 후 Claude CLI 세션을 자동 시작합니다. Jira 티켓 내용과 Notion 문서를 컨텍스트로 주입하므로, Claude가 처음부터 "무엇을 해야 하는지" 알고 있는 상태로 시작합니다. `~/.claude` 마운트로 호스트와 세션을 공유하여 `claude --continue`로 이어서 작업할 수 있습니다.

### Web Dashboard
프로젝트/태스크 목록, GitHub PR 상태 배지, 태스크 생성 모달 (AI 브랜치 이름 추천), 드래그 앤 드롭 순서 변경, Jira 이슈 그래프 시각화 (D3.js) 등을 제공합니다.

### Jira & Notion Integration
태스크 생성 시 Jira 키를 자동 감지하여 티켓 내용을 Claude 세션에 주입합니다. Notion 링크도 자동 조회. 이슈 트리를 인터랙티브 그래프로 시각화하고, 첨부 이미지를 Vision API로 분석할 수 있습니다.

### Multi-machine Support
SSH를 통해 여러 머신의 프로젝트를 통합 관리합니다. 서버에서 Docker로 실행하면서, 원격 머신의 프로젝트도 워크트리 생성과 git 동기화가 가능합니다.

### OpenAI-compatible API (OpenWebUI 연동)
`/v1/chat/completions` 엔드포인트를 제공하여 OpenWebUI 등에서 모델처럼 연결할 수 있습니다. 자연어로 대화하면 Agent가 20+ tool calling으로 프로젝트/태스크를 관리합니다.

**OpenWebUI 연결 방법:**
1. OpenWebUI 관리자 → Connections → OpenAI API 추가
2. URL: `http://<worktreee-host>:4000/v1`
3. 모델 목록에서 `worktreee` 선택 후 대화 시작

## Prerequisites

Worktreee는 Docker 컨테이너 안에서 호스트의 Git, SSH, Claude CLI를 활용하는 구조입니다. 따라서 호스트에 다음이 필요합니다:

| 요구사항 | 설명 | 확인 방법 |
|----------|------|-----------|
| **Docker & Docker Compose** | 컨테이너 실행 | `docker compose version` |
| **Git** | 워크트리 생성 | `git --version` |
| **GitHub CLI** (`gh`) | PR 조회, repo 인증 | `gh auth status` |
| **Claude Code CLI** | Claude 세션 시작 | `claude --version` |
| **SSH 키** (선택) | 원격 머신 접근 | `ssh -T your-remote` |
| **Jira API 토큰** (선택) | Jira 연동 | Atlassian 설정에서 발급 |

> Docker 컨테이너가 `~/.claude`, `~/.config/gh`, `~/.ssh` 등을 마운트하여 호스트의 인증 정보를 공유합니다.

## Quick Start

```bash
# Clone
git clone https://github.com/your-org/worktreee.git
cd worktreee

# Configure
cp .env.example .env
# Edit .env — OPENAI_API_KEY는 필수, 나머지는 선택

# Run
docker compose up -d
```

Open http://localhost:4000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | LLM API endpoint (OpenAI-compatible) | `https://gateway.letsur.ai/v1` |
| `OPENAI_API_KEY` | API key | (required) |
| `OPENAI_MODEL` | Model to use | `claude-sonnet-4-20250514` |
| `LOCAL_MACHINE` | Alias for the machine running the server | `local` |
| `REMOTE_HOSTS` | Remote SSH hosts (`alias:user@host`, comma-separated) | (optional) |
| `JIRA_URL` | Jira instance URL | (optional) |
| `JIRA_EMAIL` | Jira account email | (optional) |
| `JIRA_API_TOKEN` | Jira API token | (optional) |

## Architecture

```
Browser / OpenWebUI
       │
       ▼ http://localhost:4000
┌──────────────────────────────────────────┐
│            Docker Compose                │
│                                          │
│  web (Next.js)  ──►  api (FastAPI)        │
│    :4000                :8000            │
│                                          │
│  api 주요 기능:                           │
│    - /v1/chat/completions (Agent API)    │
│    - Tool Calling (20+ PM tools)         │
│    - Git worktree 생성/삭제              │
│    - Claude CLI 세션 관리                │
│    - Jira/Notion API 연동               │
│    - State 저장 (YAML)                   │
│                                          │
│  Volume Mounts:                          │
│    ~/Documents  ← 프로젝트 파일 접근      │
│    ~/.ssh       ← SSH 키 (원격 머신)     │
│    ~/.claude    ← Claude 세션 공유       │
│    ~/.config/gh ← GitHub CLI 인증        │
└──────────────────────────────────────────┘
```

### Multi-machine Setup

Worktreee는 SSH로 원격 머신의 프로젝트도 관리할 수 있습니다:

```env
# .env
REMOTE_HOSTS=mac:user@192.168.1.10,server2:user@192.168.1.50
```

프로젝트 추가 시 머신 별칭을 지정하면, 해당 머신에서 워크트리 생성/git 동기화가 실행됩니다.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Monorepo | Turborepo + pnpm |
| Backend | Python 3.11+, FastAPI, uv |
| Frontend | Next.js 15, React 19, Tailwind CSS 4 |
| LLM | OpenAI-compatible API |
| State | YAML file |
| Container | Docker |
| GitHub | GitHub CLI (gh) |

## Development

```bash
# Install dependencies
pnpm install

# Run all (Turborepo)
pnpm dev

# Web only
pnpm dev:web

# API only
cd apps/api && uv run uvicorn main:app --reload --port 8000
```

## License

MIT
