---
created: 2025-12-31
tags:
  - comparison
  - inkeep-agents
  - crewai
  - multi-agent
  - architecture
---

# inkeep-agents vs crewAI 비교 분석

## 개요

두 멀티에이전트 프레임워크의 아키텍처, 패턴, 기능을 비교 분석한 문서입니다.

### 기본 정보

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **언어** | TypeScript | Python |
| **구조** | 모노레포 (pnpm + Turborepo) | 모노레포 (Python workspace) |
| **철학** | API-first, SaaS 지향 | 로컬-first, 라이브러리 지향 |
| **라이선스** | - | MIT |
| **GitHub** | inkeep/inkeep-agents | crewAIInc/crewAI |

---

## 1. 에이전트 계층 구조

### 구조 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **구조** | Project → Agent → SubAgent | Crew → Agent → Task |
| **최상위** | Project (설정, 모델, 제약) | Crew (오케스트레이션) |
| **중간층** | Agent (오케스트레이터) | Agent (역할, 목표, 백스토리) |
| **실행단위** | SubAgent (전문화된 역할) | Task (구체적 작업) |

### inkeep-agents 구조

```
Project
├── models (base, structuredOutput, summarizer)
├── stopWhen (실행 제한)
└── Agent
    ├── defaultSubAgent
    └── subAgents[]
        ├── prompt
        ├── canUse[]
        ├── canTransferTo[]
        └── canDelegateTo[]
```

### crewAI 구조

```
Crew
├── process (sequential | hierarchical)
├── memory (short/long/entity/external)
├── manager_agent (hierarchical용)
├── agents[]
│   ├── role
│   ├── goal
│   ├── backstory
│   └── tools[]
└── tasks[]
    ├── description
    ├── expected_output
    ├── agent (담당 에이전트)
    └── context[] (의존 태스크)
```

### 핵심 차이점

| 관점 | inkeep-agents | crewAI |
|------|---------------|--------|
| **역할 담당** | SubAgent | Agent |
| **작업 단위** | SubAgent 내 처리 | Task |
| **구조** | 계층적 (3-tier) | 평면적 (2-tier + Task) |
| **오케스트레이션** | Agent가 SubAgent 조율 | Crew가 전체 조율 |

---

## 2. 위임 패턴 (Delegation)

### 기능 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Transfer** | ✅ 완전 이관 | ❌ 없음 |
| **Delegation** | ✅ 부분 위임 | ✅ allow_delegation |
| **A2A (원격)** | ✅ JSON-RPC 2.0 | ✅ HTTP 기반 |
| **Manager** | ❌ 없음 | ✅ Hierarchical Process |

### inkeep-agents: Transfer vs Delegation

```typescript
subAgent({
  id: 'triage',
  // Transfer: 완전히 제어권 이전, 나는 손 뗌
  canTransferTo: ['billing', 'technical'],

  // Delegation: 작업만 맡기고 결과 받아서 내가 계속
  canDelegateTo: ['research', 'calculator']
})
```

**Transfer 흐름:**
```
User → Triage → [Transfer] → Billing → User
         ↑                      ↓
         └── 더 이상 관여 안함 ──┘
```

**Delegation 흐름:**
```
User → Triage → [Delegate] → Research
         ↑                      ↓
         └──── 결과 받아서 ─────┘
         ↓
       User에게 응답
```

### crewAI: Delegation + Manager

```python
# Agent 레벨 위임
Agent(
    role="Lead Researcher",
    allow_delegation=True,  # 다른 에이전트에게 위임 가능
    tools=[delegate_work, ask_question]
)

# Crew 레벨 Manager (Hierarchical)
Crew(
    process=Process.hierarchical,
    manager_agent=Agent(role="Project Manager"),
    agents=[researcher, writer, reviewer]
)
```

**Hierarchical 흐름:**
```
Task → Manager Agent
           ↓
    작업 분배 및 조율
    ↓         ↓         ↓
 Agent1   Agent2    Agent3
    ↓         ↓         ↓
    └─────────┴─────────┘
              ↓
         Manager가 종합
              ↓
          최종 결과
```

### A2A (Agent-to-Agent) 원격 통신

**inkeep-agents:**
```typescript
// JSON-RPC 2.0 프로토콜
{
  method: 'agent.invoke',
  params: {
    input: { parts: [{ kind: 'text', text: '...' }] },
    context: { conversationId, userId }
  }
}

// 에이전트 발견
GET /.well-known/{subAgentId}/agent.json
```

**crewAI:**
```python
# HTTP 기반 A2A
Agent(
    a2a=A2AConfig(
        base_url="https://remote-agent.example.com",
        authentication=BearerAuth(token="..."),
        timeout=30
    )
)
```

---

## 3. 실행 방식 (Process)

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Sequential** | 암묵적 (Transfer 체인) | ✅ Process.sequential |
| **Hierarchical** | ❌ | ✅ Process.hierarchical |
| **Flow/State** | ❌ | ✅ 데코레이터 기반 |
| **비동기** | ✅ 스트리밍 | ✅ async_execution |
| **병렬** | Delegation 병렬 가능 | ✅ Task 병렬 |

### crewAI Process 타입

**Sequential:**
```python
Crew(
    process=Process.sequential,
    tasks=[task1, task2, task3]
)
# task1 → task2 → task3 순차 실행
# 이전 태스크 출력이 다음 태스크 컨텍스트로
```

**Hierarchical:**
```python
Crew(
    process=Process.hierarchical,
    manager_llm="gpt-4",
    tasks=[task1, task2, task3]
)
# Manager가 태스크 분배 및 결과 조율
```

### crewAI Flow 패턴

데코레이터 기반 상태 머신:

```python
from crewai.flow import Flow, start, listen, router

class CustomerServiceFlow(Flow):

    @start()
    def receive_inquiry(self):
        # 문의 접수
        return {"type": "billing", "content": "..."}

    @router(depends_on="receive_inquiry")
    def route_inquiry(self, data):
        # 조건부 라우팅
        if data["type"] == "billing":
            return "handle_billing"
        elif data["type"] == "technical":
            return "handle_technical"
        return "handle_general"

    @listen("handle_billing")
    def handle_billing(self, data):
        # 결제 문의 처리
        return billing_agent.execute(data)

    @listen("handle_technical")
    def handle_technical(self, data):
        # 기술 문의 처리
        return technical_agent.execute(data)

    @listen("handle_general")
    def handle_general(self, data):
        # 일반 문의 처리
        return general_agent.execute(data)
```

**Flow 데코레이터:**
- `@start()` - 시작점
- `@listen("method")` - 특정 메서드 완료 후 실행
- `@router(depends_on="method")` - 조건부 라우팅
- `@and_("m1", "m2")` - 여러 메서드 모두 완료 후
- `@or_("m1", "m2")` - 하나라도 완료되면

---

## 4. Tool 시스템

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **정의 방식** | SDK builder 함수 | Pydantic BaseModel 상속 |
| **MCP 지원** | ✅ 네이티브 | ✅ 통합 |
| **Function Tool** | ✅ 직렬화 가능 | ✅ _run 메서드 |
| **자동 생성** | Transfer/Delegate 도구 | Delegation 도구 |
| **캐싱** | ❌ | ✅ cache_function |
| **사용 제한** | ❌ | ✅ max_usage_count |
| **결과→응답** | ❌ | ✅ result_as_answer |

### inkeep-agents Tool 정의

```typescript
// MCP Tool
const slackTool = tool({
  name: 'slack',
  description: 'Slack 연동',
  serverUrl: 'https://mcp.slack.com',
  activeTools: ['send_message', 'search_messages']
});

// Function Tool
const calculateTool = functionTool({
  name: 'calculate',
  description: '수학 계산',
  inputSchema: {
    type: 'object',
    properties: {
      expression: { type: 'string' }
    },
    required: ['expression']
  },
  execute: async ({ expression }) => {
    return eval(expression).toString();
  },
  dependencies: {}  // npm 패키지 의존성
});

// SubAgent에 할당
subAgent({
  canUse: [slackTool, calculateTool]
})
```

### crewAI Tool 정의

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class CalculatorInput(BaseModel):
    expression: str = Field(description="수학 표현식")

class CalculatorTool(BaseTool):
    name: str = "Calculator"
    description: str = "수학 계산을 수행합니다"
    args_schema: type[BaseModel] = CalculatorInput

    # 캐싱 조건
    cache_function: Callable = lambda args, result: True

    # 사용 제한
    max_usage_count: int = 10

    # 결과를 바로 최종 답변으로
    result_as_answer: bool = False

    def _run(self, expression: str) -> str:
        return str(eval(expression))

    async def _arun(self, expression: str) -> str:
        return self._run(expression)

# Agent에 할당
Agent(
    tools=[CalculatorTool()]
)

# Task에 추가 도구 할당
Task(
    tools=[extra_tool]  # 태스크별 추가 도구
)
```

### MCP 통합

**inkeep-agents:**
```typescript
tool({
  name: 'github',
  serverUrl: 'https://mcp.github.com',
  transport: 'streamable_http',  // or 'sse'
  credential: { type: 'bearer', token: '...' },
  activeTools: ['search_repos', 'get_issues']
})
```

**crewAI:**
```python
Agent(
    mcps=[
        MCPServerConfig(
            url="https://mcp.github.com",
            transport="http",  # or "sse", "stdio"
            headers={"Authorization": "Bearer ..."}
        )
    ]
)
```

---

## 5. 메모리 시스템

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Short-term** | Context 캐시 | ✅ ShortTermMemory |
| **Long-term** | ❌ | ✅ LongTermMemory |
| **Entity** | ❌ | ✅ EntityMemory |
| **External** | Context Fetch | ✅ ExternalMemory |
| **벡터 DB** | ❌ | ✅ Chroma, Qdrant |
| **RAG/Knowledge** | ❌ | ✅ Knowledge 시스템 |
| **Embeddings** | ❌ | ✅ 다양한 프로바이더 |

### inkeep-agents 컨텍스트

```typescript
// 동적 컨텍스트 페칭
const contextConfig = {
  variables: {
    userProfile: {
      source: 'http',
      url: 'https://api.example.com/users/{{userId}}',
      responseTransform: 'data.profile',
      fetchOn: 'initialization'
    },
    recentOrders: {
      source: 'http',
      url: 'https://api.example.com/orders?userId={{userId}}',
      fetchOn: 'everyInvocation'
    }
  },
  caching: {
    enabled: true,
    ttlMs: 300000  // 5분
  }
};
```

### crewAI 메모리 시스템

```python
from crewai.memory import (
    ShortTermMemory,
    LongTermMemory,
    EntityMemory,
    ExternalMemory
)

# Crew에 메모리 설정
Crew(
    memory=True,  # 메모리 활성화

    # Short-term: 현재 대화/태스크 컨텍스트
    short_term_memory=ShortTermMemory(
        storage=RAGStorage(
            embedder=OpenAIEmbeddings(),
            type="chroma"
        )
    ),

    # Long-term: 과거 인사이트, 패턴
    long_term_memory=LongTermMemory(
        storage=LTM_SQLiteStorage(
            db_path="long_term.db"
        )
    ),

    # Entity: 엔티티 및 관계 추적
    entity_memory=EntityMemory(
        storage=RAGStorage(...)
    ),

    # External: 외부 시스템 연동
    external_memory=ExternalMemory(
        storage=CustomStorage(...)
    )
)
```

### crewAI Knowledge (RAG)

```python
from crewai.knowledge import Knowledge
from crewai.knowledge.source import (
    TextFileKnowledgeSource,
    PDFKnowledgeSource,
    WebKnowledgeSource
)

# Knowledge 설정
knowledge = Knowledge(
    sources=[
        TextFileKnowledgeSource(file_path="docs/*.txt"),
        PDFKnowledgeSource(file_path="manuals/*.pdf"),
        WebKnowledgeSource(urls=["https://docs.example.com"])
    ],
    embedder=EmbedderConfig(
        provider="openai",
        model="text-embedding-3-small"
    )
)

# Crew에 적용
Crew(
    knowledge=knowledge
)

# 또는 Agent에 직접
Agent(
    knowledge_sources=[
        TextFileKnowledgeSource(...)
    ]
)
```

---

## 6. 프롬프트 관리

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **방식** | XML 템플릿 + 변수 주입 | role/goal/backstory 필드 |
| **동적 컨텍스트** | ✅ Context Resolver | ✅ Task context |
| **Phase 구분** | ✅ Phase1/Phase2 | ❌ |
| **템플릿 버전 관리** | ✅ | ❌ |

### inkeep-agents 템플릿

```xml
<!-- templates/v1/phase1/system-prompt.xml -->
<system_message>
  <agent_identity>
    {{AGENT_NAME}}
    {{AGENT_DESCRIPTION}}
  </agent_identity>

  <core_instructions>
    {{CORE_INSTRUCTIONS}}
  </core_instructions>

  {{AGENT_CONTEXT_SECTION}}
  {{ARTIFACTS_SECTION}}
  {{TOOLS_SECTION}}

  <behavioral_constraints>
    <security>{{SECURITY_RULES}}</security>
    <interaction_guidelines>
      {{INTERACTION_GUIDELINES}}
    </interaction_guidelines>
  </behavioral_constraints>
</system_message>
```

### crewAI Agent 정의

```python
Agent(
    role="Senior Data Analyst",
    goal="Analyze data and provide actionable insights",
    backstory="""
    You are a seasoned data analyst with 10+ years of experience.
    You excel at finding patterns in complex datasets and
    communicating insights clearly to stakeholders.
    """,

    # 추가 프롬프트 옵션
    system_template=None,  # 커스텀 시스템 템플릿
    prompt_template=None,  # 커스텀 프롬프트 템플릿
    response_template=None  # 커스텀 응답 템플릿
)
```

---

## 7. 제약 조건 (Constraints)

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **스텝 제한** | ✅ stepCountIs | ✅ max_iter (기본 25) |
| **전환 제한** | ✅ transferCountIs | ❌ |
| **시간 제한** | ❌ | ✅ max_execution_time |
| **RPM 제한** | ❌ | ✅ max_rpm |
| **토큰 제한** | ❌ | ✅ context window 관리 |
| **재시도** | A2A retry | ✅ guardrail_max_retries |

### inkeep-agents 제약

```typescript
project({
  stopWhen: {
    transferCountIs: 5,   // 최대 5번 전환
    stepCountIs: 20       // 최대 20 스텝
  }
})
```

### crewAI 제약

```python
# Agent 레벨
Agent(
    max_iter=25,              # 최대 반복
    max_execution_time=300,   # 최대 5분
    max_rpm=10,               # 분당 최대 요청
    max_retry_limit=2         # 에러 시 재시도
)

# Task 레벨
Task(
    guardrail=validate_output,     # 출력 검증 함수
    guardrail_max_retries=3        # 검증 실패 시 재시도
)

# Crew 레벨
Crew(
    max_rpm=60  # Crew 전체 RPM 제한
)
```

---

## 8. 이벤트/추적 시스템

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **방식** | AgentSession 이벤트 | Singleton EventBus |
| **이벤트 타입** | ~10개 | 50개 이상 |
| **구독 방식** | 세션 내 조회 | 글로벌 핸들러 등록 |
| **Training** | ❌ | ✅ train() 메서드 |
| **Testing** | ❌ | ✅ test() 메서드 |

### inkeep-agents 이벤트

```typescript
type AgentSessionEventType =
  | 'agent_generate'
  | 'agent_reasoning'
  | 'transfer'
  | 'delegation_sent'
  | 'delegation_returned'
  | 'artifact_saved'
  | 'tool_call'
  | 'tool_result'
  | 'compression'
  | 'error';

// 세션에서 이벤트 조회
const events = session.getEvents({ type: 'tool_call' });
const timeline = session.getTimeline();
const stats = session.getStats();
```

### crewAI EventBus

```python
from crewai.events import crewai_event_bus
from crewai.events.types import (
    AgentExecutionStarted,
    AgentExecutionCompleted,
    TaskExecutionStarted,
    TaskExecutionCompleted,
    ToolUsageStarted,
    ToolUsageCompleted,
    # ... 50개 이상의 이벤트 타입
)

# 이벤트 발행
crewai_event_bus.emit(
    source=self,
    event=AgentExecutionStarted(
        agent=agent,
        task=task
    )
)

# 이벤트 구독
@crewai_event_bus.on(AgentExecutionCompleted)
def on_agent_completed(event):
    print(f"Agent {event.agent.role} completed")
```

### crewAI Training

```python
# 실행 데이터 수집하여 학습
crew = Crew(agents=[...], tasks=[...])

# 학습 데이터 생성
crew.train(
    n_iterations=5,
    inputs={"topic": "AI trends"},
    filename="training_data.json"
)

# 테스트 실행
crew.test(
    n_iterations=3,
    inputs={"topic": "AI trends"}
)
```

---

## 9. LLM 지원

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Anthropic** | ✅ | ✅ |
| **OpenAI** | ✅ | ✅ |
| **Google** | ✅ | ✅ |
| **Azure** | ✅ (gateway) | ✅ |
| **Bedrock** | ❌ | ✅ |
| **OpenRouter** | ✅ | ✅ (via litellm) |
| **Custom** | ✅ | ✅ |
| **Model Cascade** | ✅ | ✅ |
| **Reasoning Mode** | ❌ | ✅ |

### inkeep-agents 모델 설정

```typescript
project({
  models: {
    base: 'openai/gpt-4o-mini',        // 기본 생성
    structuredOutput: 'openai/gpt-4o', // 구조화 출력
    summarizer: 'openai/gpt-3.5-turbo' // 요약
  }
})

// 지원 프로바이더
// anthropic/claude-sonnet-4-20250514
// openai/gpt-4o
// google/gemini-2.0-flash
// openrouter/meta-llama/llama-3-70b
// gateway/...
// custom/...
```

### crewAI 모델 설정

```python
from crewai import LLM

# 기본 LLM
llm = LLM(
    model="gpt-4",
    temperature=0.7,
    timeout=30
)

# Agent별 다른 LLM
Agent(
    llm="gpt-4",
    function_calling_llm="gpt-3.5-turbo",  # 도구 호출용
    reasoning=True,  # 확장된 사고 모드
    max_reasoning_attempts=3
)

# Crew별 LLM 오버라이드
Crew(
    function_calling_llm="gpt-3.5-turbo",  # 전체 에이전트 적용
    planning_llm="gpt-4",  # 계획 수립용
    manager_llm="gpt-4"    # Manager용 (hierarchical)
)
```

---

## 10. 출력 및 검증

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Artifact** | ✅ 아티팩트 시스템 | ❌ |
| **JSON 출력** | ✅ | ✅ output_json |
| **Pydantic 출력** | ✅ | ✅ output_pydantic |
| **파일 출력** | ❌ | ✅ output_file |
| **Guardrail** | ❌ | ✅ |
| **Markdown** | ❌ | ✅ markdown=True |

### crewAI 출력 옵션

```python
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    summary: str
    confidence: float
    recommendations: list[str]

Task(
    description="Analyze the data",
    expected_output="A structured analysis report",

    # 출력 형식
    output_json=AnalysisResult,      # JSON 스키마
    output_pydantic=AnalysisResult,  # Pydantic 모델
    output_file="report.md",         # 파일 저장
    markdown=True,                   # Markdown 포맷

    # 검증
    guardrail=lambda output: (
        output.confidence > 0.8,
        "Confidence too low"
    ),
    guardrail_max_retries=3
)
```

---

## 11. 배포/운영

### 비교

| | **inkeep-agents** | **crewAI** |
|--|-------------------|------------|
| **Self-host** | ✅ Docker Compose | 라이브러리 직접 구성 |
| **SaaS** | ✅ 설계됨 | CrewAI Platform |
| **CLI** | ✅ agents-cli | ✅ crewai CLI |
| **UI** | ✅ manage-ui | Platform UI |
| **Multi-tenant** | ✅ 스코프 기반 | ❌ |

### inkeep-agents 배포

```yaml
# docker-compose.yml
services:
  manage-ui:
    image: inkeep/agents-manage-ui
    ports: ["3000:3000"]

  manage-api:
    image: inkeep/agents-manage-api
    ports: ["3002:3002"]

  run-api:
    image: inkeep/agents-run-api
    ports: ["3003:3003"]

  postgres:
    image: postgres:18
```

### crewAI 배포

```python
# 라이브러리로 직접 서버 구성
from fastapi import FastAPI
from crewai import Crew

app = FastAPI()

@app.post("/execute")
async def execute_crew(inputs: dict):
    crew = Crew(agents=[...], tasks=[...])
    result = await crew.kickoff_async(inputs)
    return result
```

---

## 12. 패턴 비교 요약

| 패턴 | inkeep-agents | crewAI |
|------|---------------|--------|
| **분해** | 3-tier (Project/Agent/SubAgent) | 2-tier (Crew/Agent) + Task |
| **위임** | Transfer + Delegation | Delegation + Manager |
| **실행** | Transfer 체인 | Sequential / Hierarchical / Flow |
| **권한** | canUse[] | tools per agent/task |
| **제약** | stopWhen | max_iter, max_execution_time, RPM |
| **컨텍스트** | Context Resolver + 캐시 | Memory 시스템 (4종류) + Knowledge |
| **추적** | AgentSession events | EventBus + training |
| **출력** | Artifact | JSON/Pydantic/File + Guardrail |

---

## 13. 각 프레임워크의 강점

### inkeep-agents 강점

1. **Transfer 패턴**
   - 완전 이관 개념으로 명확한 책임 분리
   - crewAI에는 없는 고유 기능

2. **템플릿 기반 프롬프트**
   - XML 구조화로 유지보수 용이
   - 버전 관리 가능

3. **API-first 설계**
   - SaaS로 바로 배포 가능
   - Docker Compose로 self-host

4. **Multi-tenant**
   - 스코프 기반 데이터 격리
   - 엔터프라이즈 환경에 적합

5. **TypeScript**
   - 프론트엔드 친화적
   - 타입 안전성

### crewAI 강점

1. **Memory 시스템**
   - 4가지 메모리 타입 (Short/Long/Entity/External)
   - 벡터 DB 통합 (Chroma, Qdrant)
   - 시맨틱 검색

2. **Knowledge/RAG**
   - 다양한 소스 지원 (파일, PDF, 웹)
   - 임베딩 프로바이더 선택

3. **Flow 패턴**
   - 데코레이터 기반 상태 머신
   - 복잡한 워크플로우 표현

4. **Guardrails**
   - 출력 검증 및 재시도
   - 품질 보장

5. **Training/Testing**
   - 학습 데이터 수집
   - 반복 테스트

6. **Reasoning Mode**
   - 확장된 사고 (Claude extended thinking)
   - 복잡한 추론 태스크

7. **풍부한 도구 생태계**
   - 50개 이상의 내장 도구
   - 캐싱, 사용 제한

8. **Python 생태계**
   - 데이터 사이언스/ML 친화적
   - 풍부한 라이브러리

---

## 14. 선택 가이드

### inkeep-agents 선택 시

- TypeScript/Node.js 기반 프로젝트
- SaaS 형태로 서비스하려는 경우
- Multi-tenant가 필요한 경우
- 명확한 역할 이관(Transfer)이 필요한 경우
- 프론트엔드와 통합이 중요한 경우

### crewAI 선택 시

- Python 기반 프로젝트
- RAG/Knowledge가 중요한 경우
- 복잡한 메모리 관리가 필요한 경우
- Flow 기반 복잡한 워크플로우
- 출력 검증(Guardrail)이 중요한 경우
- ML/데이터 사이언스 연동
- 학습/개선이 필요한 경우

---

## 15. 참고 자료

### 관련 문서

- [inkeep-agents AI 설계 개념](./inkeep-agents-ai-design-concepts.md)
- [Multi-Agent Orchestration 패턴](./multi-agent-orchestration-patterns.md)

### 저장소

- inkeep-agents: `/home/amos/Documents/clone/inkeep-agents`
- crewAI: `/home/amos/Documents/clone/crewAIInc-crewAI`
