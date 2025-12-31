---
repo: inkeep-agents
created: 2025-12-31
tags:
  - ai-design
  - agent-patterns
  - architecture
---

# Inkeep Agents - AI 설계 개념 및 패턴

## 개요

이 문서는 [inkeep-agents](https://github.com/inkeep/inkeep-agents) 코드베이스에서 추출한 AI 에이전트 설계 개념, 패턴, 플로우를 정리한 것입니다. 다른 프로젝트에서 차용하기 좋은 개념들 위주로 구성했습니다.

---

## 1. 에이전트 계층 구조 (Agent Hierarchy)

### 3-Tier 구조: Project → Agent → SubAgent

```
Project (프로젝트 - 최상위 조직 단위)
├── Models
│   ├── base (기본 생성 모델)
│   ├── structuredOutput (구조화 출력용)
│   └── summarizer (요약용)
├── stopWhen (실행 제한 조건)
└── Agent (오케스트레이터)
    ├── defaultSubAgent (진입점 에이전트)
    └── subAgents[] (전문화된 서브 에이전트들)
        ├── prompt (시스템 지시사항)
        ├── canUse[] (사용 가능한 도구 목록)
        ├── canTransferTo[] (전환 가능한 대상)
        └── canDelegateTo[] (위임 가능한 대상)
```

### 핵심 개념

- **Project**: 전체 에이전트 시스템의 컨테이너. 모델 설정, 실행 제한 등 글로벌 설정 관리
- **Agent**: 오케스트레이터 역할. 여러 SubAgent를 조율
- **SubAgent**: 실제 작업을 수행하는 단위. 각각 특정 역할에 특화

### 구현 예시

```typescript
// SDK 빌더 패턴
const myProject = project({
  name: 'customer-support',
  models: {
    base: 'openai/gpt-4o-mini',
    structuredOutput: 'openai/gpt-4o',
    summarizer: 'openai/gpt-3.5-turbo'
  },
  stopWhen: {
    transferCountIs: 5,
    stepCountIs: 20
  }
})
.agents([
  agent({
    name: 'support-agent',
    defaultSubAgent: 'triage',
    subAgents: [
      subAgent({
        id: 'triage',
        prompt: '고객 문의를 분류하고 적절한 팀으로 연결합니다.',
        canTransferTo: ['billing', 'technical'],
        canUse: ['searchKnowledgeBase']
      }),
      subAgent({
        id: 'billing',
        prompt: '결제 및 환불 관련 문의를 처리합니다.',
        canUse: ['lookupOrder', 'processRefund']
      }),
      subAgent({
        id: 'technical',
        prompt: '기술 지원 문의를 처리합니다.',
        canDelegateTo: ['searchAgent']
      })
    ]
  })
])
```

### 관련 파일

- `/packages/agents-sdk/src/project.ts`
- `/packages/agents-sdk/src/agent.ts`
- `/packages/agents-sdk/src/subAgent.ts`

---

## 2. Transfer vs Delegation 패턴

에이전트 간 협업의 두 가지 핵심 패턴입니다.

### 비교표

| 구분 | Transfer (전환) | Delegation (위임) |
|------|----------------|-------------------|
| **개념** | 완전히 다른 에이전트로 제어권 이전 | 작업만 맡기고 결과 받아옴 |
| **대화 흐름** | 새 에이전트가 대화 계속 | 원래 에이전트가 계속 진행 |
| **컨텍스트** | 대화 히스토리 전체 전달 | 필요한 정보만 전달 |
| **사용자 인식** | 새 에이전트와 대화 중 | 동일 에이전트와 대화 중 (투명) |

### Transfer (전환)

```
사용자 ─────► Triage Agent ─────► Billing Agent ─────► 사용자
                    │                    │
                    └── "환불 문의군요,   └── "환불 처리해
                        결제팀 연결합니다"     드리겠습니다"
```

- 에이전트 A가 에이전트 B로 **완전히 제어권을 넘김**
- 사용자는 이제 에이전트 B와 대화
- 대화 히스토리 전체가 전달됨

### Delegation (위임)

```
사용자 ─────► Main Agent ─────────────────────────► 사용자
                  │                                    ▲
                  │ 위임                               │ 결과 종합
                  ▼                                    │
             Search Agent ─── 검색 결과 ───────────────┘
```

- 에이전트 A가 에이전트 B에게 **특정 작업만 위임**
- 에이전트 B가 결과 반환
- 에이전트 A가 결과를 종합하여 응답 생성
- 사용자는 위임이 발생했는지 모름

### 자동 생성되는 도구들

```typescript
// 설정
subAgent({
  id: 'main',
  canTransferTo: ['billing', 'technical'],
  canDelegateTo: ['search', 'calculator']
})

// 자동 생성되는 도구
// - transfer_to_billing
// - transfer_to_technical
// - delegate_to_search
// - delegate_to_calculator
```

### 구현 상세

```typescript
// Transfer 도구 반환값
interface TransferResult {
  type: 'transfer';
  targetSubAgentId: string;
}

// Delegation 도구 - A2A 클라이언트로 비동기 호출
// 결과는 artifact로 래핑되어 반환
```

### 사용 시나리오

**Transfer 사용**:
- 고객지원 → 환불팀 (완전한 역할 전환)
- 일반상담 → 전문상담사 (에스컬레이션)

**Delegation 사용**:
- 메인 에이전트가 검색 에이전트에게 정보 검색 요청
- 분석 에이전트가 계산 에이전트에게 복잡한 연산 위임

---

## 3. A2A (Agent-to-Agent) 통신 프로토콜

### 프로토콜 기반

**JSON-RPC 2.0** 기반의 표준화된 에이전트 간 통신 프로토콜

### 지원 메서드

```typescript
type A2AMethod =
  // 에이전트 호출
  | 'agent.invoke'
  | 'agent.getCapabilities'
  | 'agent.getStatus'
  // 메시지 처리
  | 'message/send'
  | 'message/stream'
  // 태스크 관리
  | 'tasks/get'
  | 'tasks/cancel'
  | 'tasks/resubscribe';
```

### 메시지 구조

```typescript
// 요청
interface A2ATask {
  id: string;
  input: {
    parts: Array<{
      kind: 'text' | 'data';
      text?: string;
      data?: any;
    }>;
  };
  context?: {
    conversationId?: string;
    userId?: string;
    metadata?: Record<string, any>;
  };
}

// 응답
interface A2ATaskResult {
  status: {
    state: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    message?: string;
    type?: A2ATaskErrorType;
  };
  artifacts?: Artifact[];
}
```

### 에이전트 발견 (Discovery)

외부 에이전트는 `.well-known` 엔드포인트를 통해 능력을 노출:

```
GET /.well-known/{subAgentId}/agent.json

Response:
{
  "name": "search-agent",
  "description": "웹 검색 및 정보 수집",
  "capabilities": ["web_search", "document_analysis"],
  "tools": [...]
}
```

### Retry 전략 (Exponential Backoff)

```typescript
const DEFAULT_BACKOFF = {
  initialInterval: 500,      // 첫 재시도: 0.5초
  maxInterval: 60000,        // 최대 대기: 60초
  exponent: 1.5,             // 지수 증가
  maxElapsedTime: 30000,     // 총 재시도 시간: 30초
};

// 재시도 대상 HTTP 상태 코드
const RETRY_STATUS_CODES = [429, 500, 502, 503, 504];
```

### 관련 파일

- `/agents-run-api/src/a2a/types.ts`
- `/agents-run-api/src/a2a/client.ts`
- `/agents-run-api/src/a2a/handlers.ts`

---

## 4. Tool 시스템 설계

### Tool 타입 분류

```
┌─────────────────────────────────────────────────┐
│                  Tool System                     │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  MCP Tools  │  │  Function   │  │Relation │ │
│  │             │  │   Tools     │  │  Tools  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                  │
│  외부 MCP 서버    네이티브 TS     자동 생성      │
│  연동 도구        함수 도구       (Transfer/     │
│                                   Delegation)   │
└─────────────────────────────────────────────────┘
```

### 1. MCP Tools (Model Context Protocol)

외부 MCP 서버의 도구를 통합:

```typescript
interface MCPServerConfig {
  name: string;
  description: string;
  serverUrl: string;
  id?: string;
  credential?: CredentialReference;
  transport?: 'streamable_http' | 'sse';
  activeTools?: string[];  // 선택적으로 특정 도구만 활성화
  headers?: Record<string, string>;
}

// 사용 예시
const slackMCP = tool({
  name: 'slack',
  description: 'Slack 연동',
  serverUrl: 'https://mcp.slack.com',
  activeTools: ['send_message', 'search_messages']
});
```

### 2. Function Tools (네이티브 함수)

TypeScript 함수를 도구로 정의:

```typescript
interface FunctionToolConfig {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;  // JSON Schema
  execute: (params: any) => Promise<any> | string;
  dependencies?: Record<string, string>;  // npm 패키지 의존성
}

// 사용 예시
const searchTool = functionTool({
  name: 'searchWeb',
  description: '웹에서 정보를 검색합니다',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: '검색 쿼리' },
      maxResults: { type: 'number', default: 10 }
    },
    required: ['query']
  },
  execute: async ({ query, maxResults }) => {
    // 검색 로직
    return results;
  },
  dependencies: {
    'axios': '^1.6.0'
  }
});
```

### 3. Relation Tools (자동 생성)

`canTransferTo`, `canDelegateTo` 설정에 따라 자동 생성:

```typescript
// 설정
subAgent({
  canTransferTo: ['billing'],
  canDelegateTo: ['search']
})

// 자동 생성되는 도구
// transfer_to_billing: 결제팀으로 전환
// delegate_to_search: 검색 에이전트에 위임
```

### Tool 실행 플로우

```
1. LLM이 tool_call 생성
      ↓
2. ToolSessionManager가 도구 호출 수신
      ↓
3. 도구 타입에 따라 실행기 선택
   ├─ MCP Tool → MCP Client로 외부 호출
   ├─ Function Tool → Sandbox에서 실행
   └─ Relation Tool → Transfer/Delegation 처리
      ↓
4. 실행 결과 반환
      ↓
5. 결과를 LLM에 다시 전달
      ↓
6. LLM이 결과 기반으로 응답 생성 또는 추가 도구 호출
```

### Sandbox 실행 전략

Function Tool은 안전한 실행을 위해 샌드박스에서 실행:

```typescript
// 실행기 선택 패턴 (Strategy Pattern)
interface SandboxExecutor {
  execute(tool: SerializedTool, params: any): Promise<any>;
}

class NativeSandboxExecutor implements SandboxExecutor { }
class VercelSandboxExecutor implements SandboxExecutor { }

// 팩토리가 적절한 실행기 선택
SandboxExecutorFactory.create(config): SandboxExecutor
```

### 에이전트별 도구 선택

같은 MCP 서버라도 에이전트마다 다른 도구 활성화 가능:

```typescript
subAgent({
  id: 'reader',
  canUse: [
    slackMCP.with({ selectedTools: ['search_messages'] })
  ]
})

subAgent({
  id: 'writer',
  canUse: [
    slackMCP.with({ selectedTools: ['send_message', 'upload_file'] })
  ]
})
```

### 관련 파일

- `/packages/agents-sdk/src/tool.ts`
- `/packages/agents-sdk/src/function-tool.ts`
- `/agents-run-api/src/tools/`
- `/agents-run-api/src/agents/ToolSessionManager.ts`

---

## 5. 시스템 프롬프트 템플릿 아키텍처

### 템플릿 구조

```xml
<system_message>
  <!-- 에이전트 정체성 -->
  <agent_identity>
    {{AGENT_NAME}}
    {{AGENT_DESCRIPTION}}
  </agent_identity>

  <!-- 핵심 지시사항 -->
  <core_instructions>
    {{CORE_INSTRUCTIONS}}
  </core_instructions>

  <!-- 동적 컨텍스트 (런타임에 주입) -->
  {{AGENT_CONTEXT_SECTION}}

  <!-- 아티팩트 정의 -->
  {{ARTIFACTS_SECTION}}

  <!-- 사용 가능한 도구 -->
  {{TOOLS_SECTION}}

  <!-- 행동 제약 -->
  <behavioral_constraints>
    <security>
      <!-- 프롬프트 인젝션 방지 -->
      <!-- 민감 정보 보호 -->
    </security>

    <interaction_guidelines>
      <!-- 통합된 어시스턴트로 보이게 -->
      <!-- Delegation 발생 시 사용자에게 투명하게 -->
      <!-- 도구 호출 시 설명 없이 바로 실행 -->
    </interaction_guidelines>
  </behavioral_constraints>
</system_message>
```

### 템플릿 엔진 패턴

```typescript
class SystemPromptBuilder<TConfig> {
  private templates = new Map<string, string>();

  // 템플릿 로드 (버전별 관리)
  loadTemplates(version: string): void {
    // v1/phase1/system-prompt.xml
    // v1/phase2/system-prompt.xml
  }

  // 프롬프트 조립
  buildSystemPrompt(config: TConfig): AssembleResult {
    // 1. 템플릿 변수 검증
    // 2. 변수 치환
    // 3. 토큰 수 계산
    return {
      prompt: assembledPrompt,
      tokenCount: tokenCount,
      sections: sectionBreakdown
    };
  }
}

interface AssembleResult {
  prompt: string;
  tokenCount: number;
  sections: {
    identity: number;
    instructions: number;
    context: number;
    tools: number;
    constraints: number;
  };
}
```

### 핵심 행동 제약 (Behavioral Constraints)

```xml
<interaction_guidelines>
  <!-- 1. 통합 어시스턴트 표현 -->
  <unified_presentation>
    여러 에이전트가 있더라도 사용자에게는 하나의 어시스턴트로 보여야 합니다.
    "다른 팀에 연결해드리겠습니다" 대신 "확인해보겠습니다"로 표현합니다.
  </unified_presentation>

  <!-- 2. Delegation 투명성 -->
  <delegation_transparency>
    다른 에이전트에게 작업을 위임할 때 사용자에게 알리지 않습니다.
    결과만 자연스럽게 통합하여 응답합니다.
  </delegation_transparency>

  <!-- 3. 도구 호출 규칙 -->
  <tool_usage>
    도구를 호출할 때 "검색해보겠습니다"라고 말하지 않고 바로 실행합니다.
    결과를 자연스러운 대화로 전달합니다.
  </tool_usage>
</interaction_guidelines>
```

### Phase 기반 프롬프트

```
Phase 1: 초기 생성
├── 사용자 요청 이해
├── 필요한 도구 판단
└── 초기 응답 또는 도구 호출

Phase 2: 정제 (Refinement)
├── 도구 결과 통합
├── 응답 품질 개선
└── 추가 액션 판단
```

### 관련 파일

- `/agents-run-api/templates/v1/phase1/system-prompt.xml`
- `/agents-run-api/templates/v1/phase2/system-prompt.xml`
- `/agents-run-api/src/agents/SystemPromptBuilder.ts`

---

## 6. 모델 선택 전략 (Model Cascade)

### 개념

태스크 유형에 따라 다른 모델을 사용하여 비용과 성능 최적화:

```typescript
interface ModelConfig {
  base: string;              // 기본 생성
  structuredOutput?: string; // 구조화된 출력 (JSON 등)
  summarizer?: string;       // 요약 작업
}

// 예시 설정
const models: ModelConfig = {
  base: 'openai/gpt-4o-mini',        // 빠르고 저렴
  structuredOutput: 'openai/gpt-4o', // 정확한 JSON 출력
  summarizer: 'openai/gpt-3.5-turbo' // 비용 효율적
};
```

### Fallback 전략

```typescript
class ModelFactory {
  getPrimaryModel(): LanguageModel {
    return this.createModel(config.base);
  }

  getStructuredOutputModel(): LanguageModel {
    // structuredOutput 설정 없으면 base로 폴백
    return this.createModel(config.structuredOutput ?? config.base);
  }

  getSummarizerModel(): LanguageModel {
    // summarizer 설정 없으면 base로 폴백
    return this.createModel(config.summarizer ?? config.base);
  }
}
```

### 지원 프로바이더

```typescript
// 모델 문자열 파싱: "provider/model-name"
const SUPPORTED_PROVIDERS = [
  'anthropic',    // Claude 시리즈
  'openai',       // GPT 시리즈
  'google',       // Gemini 시리즈
  'openrouter',   // OpenRouter 통합
  'gateway',      // AI Gateway
  'nim',          // NVIDIA NIM
  'custom'        // 커스텀 엔드포인트
];

// 사용 예시
'anthropic/claude-sonnet-4-20250514'
'openai/gpt-4o'
'google/gemini-2.0-flash'
'openrouter/meta-llama/llama-3-70b'
```

### 관련 파일

- `/agents-run-api/src/agents/ModelFactory.ts`

---

## 7. Context 관리 패턴

### 동적 컨텍스트 페칭

에이전트 실행 전에 외부 소스에서 컨텍스트 정보를 가져옴:

```typescript
interface ContextFetchDefinition {
  method: 'http' | 'webhook';
  url?: string;
  requestTransform?: string;   // 요청 변환 표현식
  responseTransform?: string;  // 응답 변환 표현식
}

// 설정 예시
const contextConfig = {
  contextVariables: {
    userProfile: {
      method: 'http',
      url: 'https://api.example.com/users/{{userId}}',
      responseTransform: 'data.profile'
    },
    recentOrders: {
      method: 'http',
      url: 'https://api.example.com/orders?userId={{userId}}&limit=5',
      responseTransform: 'data.orders'
    }
  }
};
```

### 컨텍스트 캐시 전략

```typescript
// 캐시 키 구조
interface ContextCacheKey {
  conversationId: string;
  contextConfigId: string;
  contextVariableKey: string;
}

// 캐시 테이블 구조
contextCache: {
  conversationId: string;
  contextConfigId: string;
  contextVariableKey: string;
  value: JSONB;
  fetchedAt: timestamp;
  fetchDurationMs: number;
}

// 캐시 무효화 조건
// - 컨텍스트 설정 변경 시
// - 명시적 무효화 요청 시
// - TTL 만료 시
```

### 컨텍스트 해결 트리거

```typescript
type ContextTrigger = 'initialization' | 'invocation';

// initialization: 대화 시작 시 한 번만 페칭
// invocation: 매 요청마다 새로 페칭

async function determineContextTrigger(
  config: ContextConfig,
  conversation: Conversation
): Promise<ContextTrigger> {
  if (conversation.isNew) return 'initialization';
  if (config.refreshOnInvocation) return 'invocation';
  return 'initialization';
}
```

### 시스템 프롬프트에 컨텍스트 주입

```xml
{{AGENT_CONTEXT_SECTION}}

<!-- 렌더링 결과 -->
<context>
  <user_profile>
    이름: 홍길동
    등급: VIP
    가입일: 2023-01-15
  </user_profile>

  <recent_orders>
    - 주문 #12345: 노트북 (배송 완료)
    - 주문 #12346: 마우스 (배송 중)
  </recent_orders>
</context>
```

### 관련 파일

- `/packages/agents-core/src/context/context.ts`
- `/packages/agents-core/src/context/contextCache.ts`
- `/agents-run-api/src/context/ContextResolver.ts`

---

## 8. 실행 종료 조건 (Stop Conditions)

### 설정

```typescript
interface StopWhen {
  transferCountIs?: number;  // N번 전환되면 종료
  stepCountIs?: number;      // N스텝이면 종료
}

// 예시
const project = project({
  stopWhen: {
    transferCountIs: 5,   // 최대 5번 에이전트 전환
    stepCountIs: 20       // 최대 20 스텝 (도구 호출 포함)
  }
});
```

### 구현 로직

```typescript
function shouldStop(session: AgentSession, config: StopWhen): boolean {
  if (config.transferCountIs !== undefined) {
    const transfers = session.getEvents('transfer');
    if (transfers.length >= config.transferCountIs) return true;
  }

  if (config.stepCountIs !== undefined) {
    const steps = session.getEvents(['tool_call', 'agent_generate']);
    if (steps.length >= config.stepCountIs) return true;
  }

  return false;
}
```

### 용도

- 무한 루프 방지
- 비용 제어
- 응답 시간 제한

---

## 9. Event Sourcing (세션 이벤트 추적)

### 이벤트 타입

```typescript
type AgentSessionEventType =
  | 'agent_generate'       // LLM 생성 호출
  | 'agent_reasoning'      // 추론 과정
  | 'transfer'             // 에이전트 전환
  | 'delegation_sent'      // 위임 요청 전송
  | 'delegation_returned'  // 위임 결과 수신
  | 'artifact_saved'       // 아티팩트 저장
  | 'tool_call'            // 도구 호출
  | 'tool_result'          // 도구 결과
  | 'compression'          // 컨텍스트 압축
  | 'error';               // 에러 발생
```

### 이벤트 구조

```typescript
interface AgentSessionEvent {
  id: string;
  type: AgentSessionEventType;
  timestamp: Date;
  subAgentId: string;
  data: Record<string, any>;
  metadata?: {
    duration?: number;
    tokenCount?: number;
    cost?: number;
  };
}
```

### AgentSession 클래스

```typescript
class AgentSession {
  private events: AgentSessionEvent[] = [];

  // 이벤트 추가
  addEvent(event: Omit<AgentSessionEvent, 'id' | 'timestamp'>): void {
    this.events.push({
      id: generateId(),
      timestamp: new Date(),
      ...event
    });
  }

  // 이벤트 조회
  getEvents(type?: AgentSessionEventType | AgentSessionEventType[]): AgentSessionEvent[] {
    if (!type) return this.events;
    const types = Array.isArray(type) ? type : [type];
    return this.events.filter(e => types.includes(e.type));
  }

  // 특정 서브에이전트 이벤트만 조회
  getEventsBySubAgent(subAgentId: string): AgentSessionEvent[] {
    return this.events.filter(e => e.subAgentId === subAgentId);
  }
}
```

### 활용 사례

1. **디버깅**: 에이전트 실행 과정 추적
2. **감사 로그**: 모든 액션 기록
3. **리플레이**: 동일 입력으로 재실행
4. **분석**: 성능/비용 측정

---

## 10. 에이전트 실행 플로우 (End-to-End)

### 전체 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        요청 수신                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Middleware Stack                                             │
│     ├─ OpenTelemetry (추적)                                      │
│     ├─ Request ID 생성                                           │
│     └─ ExecutionContext 주입                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 대화 생성/재개                                               │
│     ├─ 새 대화: Conversation 생성                                │
│     └─ 기존 대화: conversationId로 조회                          │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 컨텍스트 해결 (ContextResolver)                              │
│     ├─ 캐시 확인                                                 │
│     ├─ 필요시 외부 API 호출                                      │
│     └─ 컨텍스트 변수 준비                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 에이전트 정의 로드                                           │
│     ├─ DB에서 Agent/SubAgent 설정 조회                           │
│     ├─ 도구 목록 로드 (MCP, Function, Relation)                  │
│     ├─ 데이터/아티팩트 컴포넌트 로드                             │
│     └─ 모델 설정 로드                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 시스템 프롬프트 빌드                                         │
│     ├─ 템플릿 로드                                               │
│     ├─ 변수 치환                                                 │
│     └─ 토큰 수 계산                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 대화 히스토리 로드                                           │
│     ├─ 이전 메시지 조회                                          │
│     ├─ 필요시 요약/압축                                          │
│     └─ 토큰 제한 적용                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. LLM 호출 (AI SDK)                                            │
│     ├─ generateText() 또는 streamText()                          │
│     ├─ 도구 정의 전달                                            │
│     └─ 응답 대기                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. 도구 호출 루프                                               │
│     ┌─────────────────────────────────────────────────────────┐ │
│     │  LLM 응답에 tool_call 있음?                              │ │
│     │     │                                                    │ │
│     │     ├─ Yes ──► ToolSessionManager                       │ │
│     │     │              ├─ 도구 실행                          │ │
│     │     │              └─ 결과 반환                          │ │
│     │     │                    │                               │ │
│     │     │              LLM에 결과 전달                       │ │
│     │     │                    │                               │ │
│     │     │              다시 LLM 호출 ────────────────┐       │ │
│     │     │                                           │       │ │
│     │     └─ No ───► 루프 종료                        │       │ │
│     │                                                 │       │ │
│     └─────────────────────────────────────────────────┘       │ │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. 종료 조건 확인                                               │
│     ├─ stopWhen 조건 체크                                        │
│     ├─ Transfer 발생 시 대상 에이전트로 전환                     │
│     └─ 최종 응답 확정                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  10. 결과 저장                                                   │
│      ├─ 메시지 저장 (user, assistant)                            │
│      ├─ 아티팩트 저장                                            │
│      └─ 세션 이벤트 저장                                         │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  11. 응답 반환                                                   │
│      ├─ 일반: JSON 응답                                          │
│      └─ 스트리밍: SSE 스트림                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 핸들러 코드 구조

```typescript
// generateTaskHandler.ts (간략화)
async function handleGenerateTask(request: GenerateRequest) {
  // 병렬 데이터 로드
  const [
    internalRelations,
    externalRelations,
    teamRelations,
    toolsForAgent,
    dataComponents,
    artifactComponents,
  ] = await Promise.all([
    loadInternalRelations(),
    loadExternalRelations(),
    loadTeamRelations(),
    loadToolsForAgent(),
    loadDataComponents(),
    loadArtifactComponents(),
  ]);

  // 에이전트 인스턴스 생성
  const agent = new Agent({
    id, tenantId, projectId, agentId,
    name, description, prompt,
    models: resolvedModels,
    tools: mcpTools,
    dataComponents,
    artifactComponents,
    conversationHistoryConfig,
    contextConfigId,
  });

  // 실행
  const result = await agent.generate({
    messages: conversationHistory,
    context: resolvedContext,
  });

  return result;
}
```

---

## 11. 핵심 설계 패턴 요약

### 패턴 목록

| 패턴 | 적용 위치 | 설명 |
|------|----------|------|
| **Builder** | SDK | `project().agents([...]).tools([...])` 플루언트 API |
| **Factory** | ModelFactory | `'openai/gpt-4o'` → LanguageModel 인스턴스 생성 |
| **Strategy** | SandboxExecutor | 실행 환경에 따른 실행기 선택 |
| **Middleware** | Hono | 요청마다 ExecutionContext 주입 |
| **Event Sourcing** | AgentSession | 모든 상태 변경을 이벤트로 기록 |
| **Repository** | Data Access | DB 접근 추상화 |
| **Template Method** | SystemPromptBuilder | 프롬프트 조립 알고리즘 템플릿화 |
| **Retry** | A2A Client | Exponential backoff 재시도 |
| **Registry** | CredentialStore | 인증 정보 중앙 관리 |

### 스코프 기반 데이터 격리

```typescript
// 복합 기본키로 멀티테넌시 구현
const tenantScoped = { tenantId, id };
const projectScoped = { ...tenantScoped, projectId };
const agentScoped = { ...projectScoped, agentId };
const subAgentScoped = { ...agentScoped, subAgentId };

// 모든 쿼리에 스코프 적용
db.query.agents.findMany({
  where: { tenantId, projectId }
});
```

### Credential Abstraction

```typescript
// 인증 정보를 비즈니스 로직과 분리
interface CredentialStoreRegistry {
  get(credentialId: string): Promise<Credential>;
}

// CredentialStuffer가 요청에 인증 정보 주입
class CredentialStuffer {
  async stuffRequest(request: Request, credentialId: string): Promise<Request> {
    const credential = await this.registry.get(credentialId);
    return request.withHeaders(credential.toHeaders());
  }
}
```

---

## 12. 차용 가능한 핵심 개념 Top 10

### 1. Transfer/Delegation 패턴
에이전트 간 협업의 두 가지 모드. Transfer는 완전한 제어권 이전, Delegation은 작업만 위임하고 결과 수신.

### 2. 계층적 에이전트 구조
Project → Agent → SubAgent 3-tier 구조로 복잡한 에이전트 시스템 조직화.

### 3. 템플릿 기반 시스템 프롬프트
XML 템플릿 + 변수 치환으로 동적이고 유지보수 가능한 프롬프트 관리.

### 4. Model Cascade
태스크 유형별로 다른 모델 사용 (비용/성능 최적화).

### 5. Event Sourcing
모든 실행 이벤트를 기록하여 디버깅, 감사, 리플레이 지원.

### 6. 동적 컨텍스트 페칭
실행 시점에 외부 API에서 컨텍스트 정보 가져오기 + 캐싱.

### 7. Tool 타입 분류
MCP Tools, Function Tools, Relation Tools로 도구 체계화.

### 8. Stop Conditions
전환 횟수, 스텝 수 제한으로 무한 루프 방지 및 비용 제어.

### 9. A2A 프로토콜
JSON-RPC 2.0 기반의 표준화된 에이전트 간 통신.

### 10. 스코프 기반 격리
복합 기본키로 테넌트/프로젝트/에이전트 레벨 데이터 격리.

---

## 참고: 주요 파일 위치

```
/packages/agents-sdk/src/
├── project.ts          # Project 클래스
├── agent.ts            # Agent 클래스
├── subAgent.ts         # SubAgent 클래스
├── tool.ts             # Tool 정의
├── function-tool.ts    # Function Tool
└── builders.ts         # 빌더 함수들

/packages/agents-core/src/
├── db/schema.ts        # DB 스키마
├── context/            # 컨텍스트 관리
└── data-access/        # 데이터 접근 계층

/agents-run-api/src/
├── agents/
│   ├── Agent.ts        # 에이전트 실행 엔진
│   ├── ModelFactory.ts # 모델 팩토리
│   ├── ToolSessionManager.ts
│   └── SystemPromptBuilder.ts
├── a2a/                # A2A 프로토콜
├── tools/              # 도구 실행
├── handlers/           # 요청 핸들러
└── templates/v1/       # 프롬프트 템플릿
```

---

## 라이선스

이 문서는 inkeep-agents 코드베이스 분석을 기반으로 작성되었습니다.
원본 저장소: https://github.com/inkeep/inkeep-agents
