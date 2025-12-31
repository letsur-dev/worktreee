---
created: 2025-12-31
tags:
  - comparison
  - inkeep-agents
  - crewai
  - langchain
  - multi-agent
  - architecture
---

# Multi-Agent 프레임워크 3종 비교

## 개요

세 가지 주요 멀티에이전트/LLM 프레임워크를 비교 분석한 문서입니다.

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **언어** | TypeScript | Python | Python |
| **철학** | API-first SaaS | 로컬-first 라이브러리 | 범용 LLM 프레임워크 |
| **특화** | 멀티에이전트 오케스트레이션 | 멀티에이전트 협업 | LLM 애플리케이션 전반 |
| **오케스트레이션** | 내장 | 내장 (Crew) | 외부 (LangGraph) |

---

## 1. 아키텍처 개요

### inkeep-agents
```
Project → Agent → SubAgent
         (오케스트레이터)  (실행자)
```
- 계층적 3-tier 구조
- Transfer/Delegation으로 에이전트 간 협업
- API 서버로 배포 지향

### crewAI
```
Crew → Agent + Task
 (오케스트레이터)  (역할)  (작업)
```
- 평면적 구조 + Task 기반
- Sequential/Hierarchical/Flow 프로세스
- 라이브러리로 직접 사용

### LangChain
```
Runnable → Chain/Agent → LLM + Tools
  (프로토콜)    (조합)      (실행)
```
- Runnable 프로토콜 기반 조합
- LangGraph로 복잡한 오케스트레이션
- 범용 LLM 프레임워크

---

## 2. 에이전트 정의

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **정의 방식** | Builder 함수 | Pydantic 클래스 | Factory 함수 |
| **역할 표현** | prompt 필드 | role/goal/backstory | 프롬프트 템플릿 |
| **도구 할당** | canUse[] | tools[] | tools 파라미터 |
| **계층** | SubAgent 계층 | 단일 레벨 | 단일 레벨 |

### inkeep-agents

```typescript
subAgent({
  id: 'researcher',
  prompt: '정보를 검색하고 분석합니다',
  canUse: [searchTool, analyzeTool],
  canTransferTo: ['writer'],
  canDelegateTo: ['calculator']
})
```

### crewAI

```python
Agent(
  role="Senior Researcher",
  goal="Find accurate and relevant information",
  backstory="You are an expert researcher with 10+ years experience...",
  tools=[search_tool, analyze_tool],
  llm="gpt-4",
  allow_delegation=True
)
```

### LangChain

```python
# Factory 방식
agent = create_react_agent(
  model=ChatOpenAI(model="gpt-4"),
  tools=[search_tool, analyze_tool],
  prompt=hub.pull("hwchase17/react")
)

# 또는 LangGraph로 직접 구성
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
```

---

## 3. 멀티에이전트 오케스트레이션

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **오케스트레이터** | Agent (내장) | Crew (내장) | LangGraph (외부) |
| **Sequential** | Transfer 체인 | ✅ Process.sequential | StateGraph edges |
| **Hierarchical** | ❌ | ✅ Process.hierarchical | 수동 구성 |
| **Flow/State** | ❌ | ✅ @start/@listen | ✅ StateGraph |
| **Transfer** | ✅ | ❌ | ❌ |
| **Delegation** | ✅ | ✅ | Middleware |
| **Manager** | ❌ | ✅ manager_agent | 수동 구성 |

### inkeep-agents: Transfer/Delegation

```typescript
// 완전 이관 (Transfer)
subAgent({
  id: 'triage',
  canTransferTo: ['billing', 'technical']
})
// → User가 이제 billing과 대화

// 부분 위임 (Delegation)
subAgent({
  id: 'main',
  canDelegateTo: ['search']
})
// → main이 결과 받아서 계속 처리
```

### crewAI: Process Types

```python
# Sequential
Crew(
  process=Process.sequential,
  agents=[researcher, writer, reviewer],
  tasks=[research_task, write_task, review_task]
)
# task1 → task2 → task3

# Hierarchical
Crew(
  process=Process.hierarchical,
  manager_agent=manager,
  agents=[researcher, writer],
  tasks=[...]
)
# Manager가 작업 분배 및 조율

# Flow (데코레이터 기반)
class MyFlow(Flow):
  @start()
  def begin(self): ...

  @listen("begin")
  def next(self, data): ...

  @router(depends_on="next")
  def route(self, data):
    return "path_a" if condition else "path_b"
```

### LangChain: LangGraph

```python
from langgraph.graph import StateGraph

# 상태 정의
class AgentState(TypedDict):
  messages: list[BaseMessage]
  next: str

# 그래프 구성
graph = StateGraph(AgentState)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
graph.add_node("reviewer", reviewer_node)

# 엣지 (흐름) 정의
graph.add_edge("researcher", "writer")
graph.add_conditional_edges(
  "writer",
  should_continue,
  {"continue": "reviewer", "end": END}
)

agent = graph.compile()
```

---

## 4. Tool 시스템

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **정의 방식** | Builder / Class | Class 상속 | @tool / Class |
| **스키마** | JSON Schema | Pydantic | Pydantic (자동) |
| **MCP** | ✅ 네이티브 | ✅ 통합 | ✅ 통합 |
| **캐싱** | ❌ | ✅ | ❌ (외부) |
| **사용 제한** | ❌ | ✅ max_usage_count | Middleware |
| **Toolkit** | ❌ | ❌ | ✅ BaseToolkit |

### inkeep-agents

```typescript
// Function Tool
functionTool({
  name: 'search',
  description: '웹 검색',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string' }
    }
  },
  execute: async ({ query }) => {
    return await searchWeb(query);
  }
})

// MCP Tool
tool({
  name: 'slack',
  serverUrl: 'https://mcp.slack.com',
  activeTools: ['send_message']
})
```

### crewAI

```python
from crewai.tools import BaseTool

class SearchTool(BaseTool):
  name: str = "search"
  description: str = "웹 검색"
  cache_function: Callable = lambda args, result: True
  max_usage_count: int = 10

  def _run(self, query: str) -> str:
    return search_web(query)
```

### LangChain

```python
from langchain_core.tools import tool, BaseTool

# 데코레이터 방식 (가장 간단)
@tool
def search(query: str) -> str:
  """웹에서 정보를 검색합니다"""
  return search_web(query)

# 클래스 방식
class SearchTool(BaseTool):
  name = "search"
  description = "웹 검색"
  args_schema: type[BaseModel] = SearchInput

  def _run(self, query: str) -> str:
    return search_web(query)

# Toolkit (관련 도구 묶음)
class MyToolkit(BaseToolkit):
  def get_tools(self) -> list[BaseTool]:
    return [SearchTool(), AnalyzeTool()]
```

---

## 5. 메모리 시스템

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **Short-term** | Context 캐시 | ✅ ShortTermMemory | 명시적 전달 |
| **Long-term** | ❌ | ✅ LongTermMemory | 외부 구현 |
| **Entity** | ❌ | ✅ EntityMemory | 외부 구현 |
| **벡터 DB** | ❌ | ✅ Chroma, Qdrant | ✅ 다양한 통합 |
| **RAG** | ❌ | ✅ Knowledge | ✅ Retriever |
| **요약** | ❌ | ❌ | ✅ Middleware |

### inkeep-agents

```typescript
// Context Resolver로 동적 데이터 로드
contextConfig: {
  variables: {
    userProfile: {
      source: 'http',
      url: 'https://api/users/{{userId}}',
      fetchOn: 'initialization'
    }
  },
  caching: { enabled: true, ttlMs: 300000 }
}
```

### crewAI

```python
Crew(
  memory=True,
  short_term_memory=ShortTermMemory(
    storage=RAGStorage(embedder=OpenAIEmbeddings())
  ),
  long_term_memory=LongTermMemory(
    storage=LTM_SQLiteStorage(db_path="ltm.db")
  ),
  entity_memory=EntityMemory(...),
  knowledge=Knowledge(
    sources=[PDFKnowledgeSource("docs/*.pdf")]
  )
)
```

### LangChain

```python
# 메시지 히스토리 (명시적 관리)
from langchain_core.chat_history import BaseChatMessageHistory

history = InMemoryChatMessageHistory()
history.add_messages([...])

# 모델에 직접 전달
response = model.invoke(history.messages)

# Summarization Middleware
from langchain.agents.middleware import SummarizationMiddleware

agent = create_react_agent(
  ...,
  middleware=[SummarizationMiddleware(llm=summary_llm)]
)

# RAG via Retriever
retriever = vectorstore.as_retriever()
rag_chain = (
  {"context": retriever, "question": RunnablePassthrough()}
  | prompt
  | model
)
```

---

## 6. LLM 통합

### 지원 프로바이더

| Provider | **inkeep-agents** | **crewAI** | **LangChain** |
|----------|-------------------|------------|---------------|
| OpenAI | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ✅ | ✅ |
| Google | ✅ | ✅ | ✅ |
| Azure | ✅ (gateway) | ✅ | ✅ |
| AWS Bedrock | ❌ | ✅ | ✅ |
| Ollama | ❌ | ✅ | ✅ |
| Groq | ❌ | ✅ | ✅ |
| Custom | ✅ | ✅ | ✅ |

### Model Cascade / 다중 모델

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **태스크별 모델** | ✅ base/structured/summarizer | ✅ function_calling_llm | Runnable 조합 |
| **Fallback** | ❌ | ❌ | ✅ with_fallbacks() |
| **Reasoning** | ❌ | ✅ extended thinking | ❌ |

### inkeep-agents

```typescript
project({
  models: {
    base: 'openai/gpt-4o-mini',
    structuredOutput: 'openai/gpt-4o',
    summarizer: 'openai/gpt-3.5-turbo'
  }
})
```

### crewAI

```python
Agent(
  llm="gpt-4",
  function_calling_llm="gpt-3.5-turbo",
  reasoning=True,  # Extended thinking
  max_reasoning_attempts=3
)

Crew(
  manager_llm="gpt-4",
  planning_llm="gpt-4"
)
```

### LangChain

```python
from langchain_openai import ChatOpenAI

# 기본
model = ChatOpenAI(model="gpt-4")

# Fallback
model_with_fallback = model.with_fallbacks([
  ChatOpenAI(model="gpt-3.5-turbo")
])

# 동적 초기화
from langchain.chat_models import init_chat_model
model = init_chat_model("gpt-4", provider="openai")
```

---

## 7. 제약 조건 / 안전장치

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **스텝 제한** | ✅ stepCountIs | ✅ max_iter | Middleware |
| **전환 제한** | ✅ transferCountIs | ❌ | ❌ |
| **시간 제한** | ❌ | ✅ max_execution_time | ❌ |
| **RPM** | ❌ | ✅ max_rpm | ❌ |
| **Guardrail** | ❌ | ✅ | Middleware |
| **Human-in-loop** | ❌ | ✅ human_input | ✅ Middleware |

### inkeep-agents

```typescript
project({
  stopWhen: {
    transferCountIs: 5,
    stepCountIs: 20
  }
})
```

### crewAI

```python
Agent(
  max_iter=25,
  max_execution_time=300,
  max_rpm=10
)

Task(
  guardrail=lambda output: (output.confidence > 0.8, "Confidence too low"),
  guardrail_max_retries=3,
  human_input=True  # 사람 검토 필요
)
```

### LangChain

```python
from langchain.agents.middleware import (
  ModelCallLimitMiddleware,
  HumanInTheLoopMiddleware,
  ToolCallLimitMiddleware
)

agent = create_react_agent(
  ...,
  middleware=[
    ModelCallLimitMiddleware(max_calls=10),
    ToolCallLimitMiddleware(max_calls=20),
    HumanInTheLoopMiddleware(approval_func=get_approval)
  ]
)
```

---

## 8. 이벤트 / 관찰성

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **방식** | AgentSession | EventBus | Callbacks |
| **이벤트 수** | ~10개 | 50개+ | 20개+ |
| **Tracing** | 세션 내 | 글로벌 | LangSmith |
| **Training** | ❌ | ✅ | ❌ |

### inkeep-agents

```typescript
// 세션 이벤트 조회
session.getEvents({ type: 'tool_call' });
session.getTimeline();
session.getStats();
```

### crewAI

```python
from crewai.events import crewai_event_bus

@crewai_event_bus.on(AgentExecutionCompleted)
def on_complete(event):
  print(f"Agent {event.agent.role} completed")

# Training
crew.train(n_iterations=5, inputs={...}, filename="training.json")
```

### LangChain

```python
from langchain_core.callbacks import BaseCallbackHandler

class MyHandler(BaseCallbackHandler):
  def on_llm_start(self, serialized, prompts, **kwargs):
    print(f"LLM started: {prompts}")

  def on_tool_end(self, output, **kwargs):
    print(f"Tool result: {output}")

# 사용
model.invoke(messages, config={"callbacks": [MyHandler()]})

# LangSmith (SaaS tracing)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=...
```

---

## 9. 출력 처리

### 비교표

| | **inkeep-agents** | **crewAI** | **LangChain** |
|--|-------------------|------------|---------------|
| **Artifact** | ✅ | ❌ | ❌ |
| **JSON** | ✅ | ✅ output_json | ✅ JsonOutputParser |
| **Pydantic** | ✅ | ✅ output_pydantic | ✅ PydanticOutputParser |
| **File** | ❌ | ✅ output_file | ❌ |
| **Streaming** | ✅ | ✅ | ✅ |

### inkeep-agents

```typescript
// Artifact 시스템
artifactComponents: [
  {
    type: 'report',
    schema: ReportSchema
  }
]
```

### crewAI

```python
Task(
  output_json=AnalysisResult,
  output_pydantic=AnalysisResult,
  output_file="report.md",
  markdown=True
)
```

### LangChain

```python
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=AnalysisResult)

chain = prompt | model | parser
result: AnalysisResult = chain.invoke({"query": "..."})

# Structured output (native)
structured_model = model.with_structured_output(AnalysisResult)
```

---

## 10. 핵심 설계 패턴 비교

| 패턴 | **inkeep-agents** | **crewAI** | **LangChain** |
|------|-------------------|------------|---------------|
| **조합** | Builder 함수 | Pydantic 클래스 | Runnable \| 연산자 |
| **실행** | API 서버 | 직접 호출 | invoke/stream |
| **상태** | Event Sourcing | EventBus | StateGraph |
| **확장** | MCP/A2A | Middleware 없음 | Middleware |
| **프롬프트** | XML 템플릿 | role/goal/backstory | PromptTemplate |
| **에러** | A2A retry | guardrail retry | with_fallbacks |

---

## 11. 강점 비교

### inkeep-agents 강점

1. **Transfer 패턴** - 완전 이관 (고유)
2. **API-first** - SaaS 바로 배포
3. **Multi-tenant** - 스코프 기반 격리
4. **XML 템플릿** - 구조화된 프롬프트 관리
5. **TypeScript** - 프론트엔드 친화적

### crewAI 강점

1. **Memory 시스템** - 4종류 메모리
2. **Knowledge/RAG** - 내장 벡터 DB
3. **Flow 패턴** - 데코레이터 상태머신
4. **Guardrails** - 출력 검증 + 재시도
5. **Training** - 학습 데이터 수집
6. **Reasoning Mode** - Extended thinking
7. **Process Types** - Sequential/Hierarchical

### LangChain 강점

1. **Runnable 프로토콜** - 범용 조합
2. **Middleware** - 강력한 확장성
3. **LangGraph** - 유연한 그래프 오케스트레이션
4. **20+ 프로바이더** - 가장 많은 통합
5. **RAG 생태계** - Loader/Splitter/Retriever
6. **LangSmith** - 프로덕션 관찰성
7. **Fallback** - 에러 복구
8. **@tool 데코레이터** - 가장 간단한 도구 정의

---

## 12. 약점 비교

### inkeep-agents 약점

- 메모리 시스템 없음
- RAG 없음
- Guardrail 없음
- Python 생태계 접근 제한

### crewAI 약점

- Transfer 패턴 없음
- Middleware 시스템 없음
- Fallback 없음
- 프로바이더 통합 LangChain보다 적음

### LangChain 약점

- 오케스트레이션 외부 의존 (LangGraph)
- 내장 메모리 없음 (명시적 관리)
- 학습 복잡도 높음
- Transfer/Delegation 패턴 없음

---

## 13. 선택 가이드

### 프로젝트 특성별 추천

| 특성 | 추천 |
|------|------|
| SaaS 서비스 | **inkeep-agents** |
| 엔터프라이즈 Multi-tenant | **inkeep-agents** |
| 복잡한 메모리 필요 | **crewAI** |
| RAG 중심 | **crewAI** or **LangChain** |
| 복잡한 워크플로우 | **crewAI** (Flow) or **LangGraph** |
| 출력 검증 필요 | **crewAI** |
| 프로바이더 다양성 | **LangChain** |
| 유연한 조합 | **LangChain** |
| TypeScript | **inkeep-agents** |
| ML/데이터 사이언스 | **crewAI** or **LangChain** |

### 통합 사용

세 프레임워크는 서로 배타적이지 않음:

```python
# crewAI + LangChain Tool
from langchain_core.tools import tool
from crewai import Agent

@tool
def my_langchain_tool(query: str) -> str:
  """LangChain으로 만든 도구"""
  return result

# crewAI Agent에서 사용
agent = Agent(tools=[my_langchain_tool])
```

---

## 14. 패턴 학습 요약

### 공통 패턴

1. **역할 기반 에이전트** - 모든 프레임워크
2. **도구 시스템** - 스키마 기반 정의
3. **LLM 추상화** - 프로바이더 독립적
4. **이벤트/콜백** - 관찰성 지원

### 고유 패턴

| 패턴 | 프레임워크 |
|------|-----------|
| **Transfer (완전 이관)** | inkeep-agents |
| **Hierarchical Process** | crewAI |
| **Flow 데코레이터** | crewAI |
| **Runnable 프로토콜** | LangChain |
| **Middleware 스택** | LangChain |
| **with_fallbacks()** | LangChain |

### 차용 추천

1. **Transfer/Delegation** (inkeep) - 명확한 책임 분리
2. **Memory 시스템** (crewAI) - 컨텍스트 관리
3. **Flow 패턴** (crewAI) - 상태 기반 워크플로우
4. **Middleware** (LangChain) - 횡단 관심사 처리
5. **Runnable** (LangChain) - 범용 조합 인터페이스

---

## 15. 참고 자료

### 관련 문서

- [inkeep-agents AI 설계 개념](./inkeep-agents-ai-design-concepts.md)
- [Multi-Agent Orchestration 패턴](./multi-agent-orchestration-patterns.md)
- [inkeep-agents vs crewAI 비교](./inkeep-agents-vs-crewai-comparison.md)

### 저장소 위치

- inkeep-agents: `/home/amos/Documents/clone/inkeep-agents`
- crewAI: `/home/amos/Documents/clone/crewAIInc-crewAI`
- LangChain: `/home/amos/Documents/clone/langchain-ai-langchain`
