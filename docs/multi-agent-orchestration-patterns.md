---
created: 2025-12-31
tags:
  - patterns
  - project-management
  - orchestration
  - meta-patterns
---

# Multi-Agent Orchestration 패턴

## 개요

이 문서는 inkeep-agents 아키텍처에서 추출한 **범용적인 오케스트레이션 패턴**들을 정리한 것입니다. AI 에이전트뿐 아니라 팀 관리, 프로젝트 관리, 워크플로우 설계 등 다양한 영역에 적용 가능합니다.

---

## 6가지 핵심 메타 패턴

```
┌─────────────────────────────────────────┐
│  1. 분해 (Decomposition)                 │
│     큰 문제 → 역할별 → 태스크별          │
├─────────────────────────────────────────┤
│  2. 위임 (Delegation)                    │
│     Transfer: 완전 이관                  │
│     Delegate: 부분 위임 + 결과 수령       │
├─────────────────────────────────────────┤
│  3. 권한 (Permission)                    │
│     역할별로 사용 가능한 도구/리소스 제한  │
├─────────────────────────────────────────┤
│  4. 제약 (Constraints)                   │
│     종료 조건, 예산, 시간 제한            │
├─────────────────────────────────────────┤
│  5. 컨텍스트 (Context)                   │
│     실행 전 필요 정보 수집 + 캐싱         │
├─────────────────────────────────────────┤
│  6. 추적 (Tracing)                       │
│     모든 상태 변경 이벤트로 기록          │
└─────────────────────────────────────────┘
```

---

## 1. 분해 패턴 (Decomposition Pattern)

### 개념

큰 목표를 계층적으로 분해하여 관리 가능한 단위로 나눔.

### 구조

```
Project (프로젝트 - 최상위 목표)
└── Agent (에이전트 - 역할/도메인)
    └── SubAgent (서브에이전트 - 구체적 태스크)
```

### 3-Tier 계층

| 레벨 | 역할 | 특징 |
|------|------|------|
| **Project** | 전체 목표 정의 | 글로벌 설정, 제약조건, 리소스 |
| **Agent** | 도메인/역할 담당 | 오케스트레이션, 라우팅 |
| **SubAgent** | 구체적 작업 수행 | 전문화, 도구 사용 |

### 적용 예시

**소프트웨어 개발**
```
프로젝트: 쇼핑몰 앱 개발
├── Agent: 백엔드
│   ├── SubAgent: API 설계
│   ├── SubAgent: DB 설계
│   └── SubAgent: 인증 구현
├── Agent: 프론트엔드
│   ├── SubAgent: UI 컴포넌트
│   ├── SubAgent: 상태관리
│   └── SubAgent: API 연동
└── Agent: 인프라
    ├── SubAgent: CI/CD
    └── SubAgent: 모니터링
```

**마케팅 캠페인**
```
프로젝트: 신제품 런칭 캠페인
├── Agent: 콘텐츠팀
│   ├── SubAgent: 블로그 작성
│   ├── SubAgent: SNS 운영
│   └── SubAgent: 영상 제작
├── Agent: 퍼포먼스팀
│   ├── SubAgent: 광고 집행
│   └── SubAgent: 데이터 분석
└── Agent: PR팀
    ├── SubAgent: 보도자료
    └── SubAgent: 인플루언서
```

**고객 지원**
```
프로젝트: 고객 서비스 운영
├── Agent: 1차 상담
│   ├── SubAgent: FAQ 응대
│   └── SubAgent: 문의 분류
├── Agent: 기술 지원
│   ├── SubAgent: 버그 리포트
│   └── SubAgent: 사용법 안내
└── Agent: 결제 지원
    ├── SubAgent: 환불 처리
    └── SubAgent: 결제 문의
```

### 설계 원칙

1. **단일 책임**: 각 SubAgent는 하나의 명확한 역할
2. **적절한 깊이**: 보통 2-3 레벨이 적당
3. **수평 확장**: Agent 내 SubAgent 추가로 기능 확장
4. **느슨한 결합**: Agent 간 직접 의존성 최소화

---

## 2. 위임 패턴 (Delegation Pattern)

### 두 가지 위임 모드

```
┌─────────────────────────────────────────────────────────────┐
│                    TRANSFER (전환)                          │
│                                                             │
│  A ──────────────► B ──────────────► 결과                  │
│      "이건 네 담당"     B가 끝까지 처리                      │
│                                                             │
│  특징: 제어권 완전 이전, A는 손 뗌                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   DELEGATION (위임)                         │
│                                                             │
│  A ───► B ───► 결과                                        │
│  │             │                                           │
│  │◄────────────┘                                           │
│  │                                                          │
│  └──────────────────────► 최종 결과                         │
│       A가 결과 통합                                         │
│                                                             │
│  특징: 부분 작업만 위임, A가 결과 수령 후 계속               │
└─────────────────────────────────────────────────────────────┘
```

### 비교표

| 구분 | Transfer (전환) | Delegation (위임) |
|------|----------------|-------------------|
| **제어권** | 완전 이전 | 유지 |
| **결과 처리** | 위임받은 쪽이 최종 처리 | 위임한 쪽이 최종 처리 |
| **컨텍스트** | 전체 히스토리 전달 | 필요한 정보만 전달 |
| **가시성** | 담당자 변경 인지 가능 | 투명 (모름) |
| **책임** | 위임받은 쪽 | 위임한 쪽 |

### Transfer 사용 시나리오

- 완전히 다른 전문 영역으로 넘길 때
- 에스컬레이션 (상위 담당자로 이관)
- 역할이 명확히 구분될 때

```
예시:
- 일반 상담 → 법무팀 (법적 문제 발생)
- 1차 지원 → 개발팀 (버그 확인됨)
- 영업팀 → 기술팀 (기술 검토 필요)
```

### Delegation 사용 시나리오

- 특정 작업만 전문가에게 맡길 때
- 정보 수집 후 종합 판단이 필요할 때
- 병렬 처리가 필요할 때

```
예시:
- PM이 디자인팀에 시안 요청 → 결과 받아서 기획서에 통합
- 분석가가 각 팀에 데이터 요청 → 취합해서 리포트 작성
- 팀장이 팀원들에게 조사 요청 → 종합해서 의사결정
```

### 구현 시 고려사항

```typescript
// Transfer 설정
{
  canTransferTo: ['legal', 'technical', 'billing']
}

// Delegation 설정
{
  canDelegateTo: ['research', 'calculation', 'verification']
}
```

**자동 생성되는 액션**:
- `transfer_to_legal` - 법무팀으로 전환
- `delegate_to_research` - 리서치 요청 후 결과 대기

---

## 3. 권한 패턴 (Permission Pattern)

### 개념

역할별로 사용 가능한 도구/리소스/액션을 명시적으로 정의.

### 구조

```typescript
SubAgent {
  id: 'junior-dev',
  canUse: [
    'readCode',
    'writeCode',
    'runTests'
  ]
  // deployProduction은 없음 → 사용 불가
}

SubAgent {
  id: 'senior-dev',
  canUse: [
    'readCode',
    'writeCode',
    'runTests',
    'codeReview',
    'deployStaging'
  ]
}

SubAgent {
  id: 'tech-lead',
  canUse: [
    '*'  // 전체 권한
  ]
}
```

### 권한 매트릭스 예시

| 역할 | 문서조회 | 문서작성 | 예산조회 | 예산승인 | 인사정보 |
|------|---------|---------|---------|---------|---------|
| 인턴 | ✓ | - | - | - | - |
| 팀원 | ✓ | ✓ | ✓ | - | - |
| 팀장 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 임원 | ✓ | ✓ | ✓ | ✓ | ✓ |

### 설계 원칙

1. **최소 권한 원칙**: 필요한 것만 부여
2. **명시적 정의**: 암묵적 권한 없음
3. **역할 기반**: 개인이 아닌 역할에 권한 부여
4. **상속 가능**: 상위 역할이 하위 권한 포함 (선택적)

### 도구 선택적 노출

같은 도구라도 역할별로 다른 기능만 노출:

```typescript
// 같은 Slack 도구지만 다른 권한
{
  id: 'reader',
  canUse: [
    slack.with({ selectedTools: ['search_messages', 'read_channel'] })
  ]
}

{
  id: 'writer',
  canUse: [
    slack.with({ selectedTools: ['send_message', 'upload_file'] })
  ]
}

{
  id: 'admin',
  canUse: [
    slack.with({ selectedTools: ['*'] })  // 전체 기능
  ]
}
```

---

## 4. 제약 패턴 (Constraints Pattern)

### 개념

무한 실행, 리소스 낭비, 비용 폭주를 방지하기 위한 명시적 제한.

### 제약 유형

```typescript
interface Constraints {
  // 실행 제한
  maxSteps?: number;           // 최대 스텝 수
  maxTransfers?: number;       // 최대 전환 횟수
  maxDelegations?: number;     // 최대 위임 횟수

  // 시간 제한
  timeoutMs?: number;          // 전체 타임아웃
  stepTimeoutMs?: number;      // 스텝별 타임아웃

  // 리소스 제한
  maxTokens?: number;          // 토큰 한도
  maxCost?: number;            // 비용 한도
  maxRetries?: number;         // 재시도 횟수

  // 깊이 제한
  maxDepth?: number;           // 위임 체인 깊이
}
```

### 적용 예시

```typescript
// 프로젝트 레벨 제약
project({
  constraints: {
    maxSteps: 50,
    maxTransfers: 5,
    timeoutMs: 300000,  // 5분
    maxCost: 10.00      // $10
  }
})

// SubAgent 레벨 제약 (더 엄격)
subAgent({
  id: 'quick-responder',
  constraints: {
    maxSteps: 5,
    timeoutMs: 30000    // 30초
  }
})
```

### Stop Conditions 구현

```typescript
function shouldStop(session: Session, constraints: Constraints): boolean {
  // 스텝 수 체크
  if (constraints.maxSteps && session.stepCount >= constraints.maxSteps) {
    return true;
  }

  // 전환 횟수 체크
  if (constraints.maxTransfers && session.transferCount >= constraints.maxTransfers) {
    return true;
  }

  // 비용 체크
  if (constraints.maxCost && session.totalCost >= constraints.maxCost) {
    return true;
  }

  // 시간 체크
  if (constraints.timeoutMs && session.elapsedMs >= constraints.timeoutMs) {
    return true;
  }

  return false;
}
```

### 제약 초과 시 처리

```typescript
type ConstraintViolationAction =
  | 'stop'           // 즉시 중단
  | 'warn_continue'  // 경고 후 계속
  | 'escalate'       // 상위로 에스컬레이션
  | 'fallback';      // 대체 로직 실행

// 설정 예시
{
  maxSteps: 20,
  onViolation: {
    maxSteps: 'escalate'  // 스텝 초과 시 상위로 이관
  }
}
```

---

## 5. 컨텍스트 패턴 (Context Pattern)

### 개념

실행 전에 필요한 정보를 수집하고, 실행 중에 접근 가능하게 관리.

### 컨텍스트 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    실행 전 (Pre-execution)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 컨텍스트 정의 확인                                       │
│     - 어떤 정보가 필요한가?                                  │
│                                                              │
│  2. 캐시 확인                                                │
│     - 이미 있는 정보인가?                                    │
│     - 유효한가? (TTL 체크)                                   │
│                                                              │
│  3. 정보 수집 (캐시 미스 시)                                 │
│     - 외부 API 호출                                          │
│     - DB 조회                                                │
│     - 파일 읽기                                              │
│                                                              │
│  4. 캐시 저장                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    실행 중 (During execution)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  컨텍스트 주입된 상태로 작업 수행                            │
│                                                              │
│  예: 시스템 프롬프트에 사용자 정보 포함                      │
│      "현재 사용자: VIP 등급, 가입 2년차, 최근 구매 3건"      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 컨텍스트 변수 정의

```typescript
interface ContextConfig {
  variables: {
    [key: string]: ContextFetchDefinition;
  };
  caching?: {
    enabled: boolean;
    ttlMs?: number;
  };
}

interface ContextFetchDefinition {
  source: 'http' | 'database' | 'file' | 'function';

  // HTTP 소스
  url?: string;
  method?: 'GET' | 'POST';
  headers?: Record<string, string>;

  // 변환
  requestTransform?: string;   // 요청 변환
  responseTransform?: string;  // 응답에서 필요한 부분 추출

  // 트리거
  fetchOn?: 'initialization' | 'everyInvocation';
}
```

### 적용 예시

```typescript
const contextConfig: ContextConfig = {
  variables: {
    userProfile: {
      source: 'http',
      url: 'https://api.example.com/users/{{userId}}',
      responseTransform: 'data.profile',
      fetchOn: 'initialization'
    },
    recentOrders: {
      source: 'http',
      url: 'https://api.example.com/orders?userId={{userId}}&limit=5',
      responseTransform: 'data.orders',
      fetchOn: 'everyInvocation'  // 매번 최신 정보
    },
    companyPolicy: {
      source: 'file',
      path: '/policies/refund-policy.md',
      fetchOn: 'initialization'
    }
  },
  caching: {
    enabled: true,
    ttlMs: 300000  // 5분
  }
};
```

### 컨텍스트 → 프롬프트 주입

```xml
<context>
  <user_profile>
    이름: {{userProfile.name}}
    등급: {{userProfile.tier}}
    가입일: {{userProfile.joinedAt}}
  </user_profile>

  <recent_orders>
    {{#each recentOrders}}
    - 주문 #{{this.id}}: {{this.product}} ({{this.status}})
    {{/each}}
  </recent_orders>

  <company_policy>
    {{companyPolicy}}
  </company_policy>
</context>
```

### 캐시 전략

| 전략 | 설명 | 사용 시나리오 |
|------|------|--------------|
| **No Cache** | 항상 새로 조회 | 실시간 데이터 필수 |
| **TTL** | 일정 시간 후 만료 | 대부분의 경우 |
| **Session** | 세션 동안 유지 | 사용자 프로필 |
| **Invalidate on Event** | 이벤트 발생 시 무효화 | 설정 변경 시 |

---

## 6. 추적 패턴 (Tracing Pattern)

### 개념

모든 상태 변경을 이벤트로 기록하여 추적, 디버깅, 분석 가능하게 함.

### Event Sourcing 구조

```typescript
interface Event {
  id: string;
  type: EventType;
  timestamp: Date;
  actor: string;        // 누가
  target?: string;      // 무엇을
  data: any;            // 상세 정보
  metadata?: {
    duration?: number;
    cost?: number;
    tokens?: number;
  };
}

type EventType =
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'transfer'
  | 'delegation_sent'
  | 'delegation_returned'
  | 'tool_called'
  | 'tool_result'
  | 'context_loaded'
  | 'constraint_hit'
  | 'error';
```

### 이벤트 기록 예시

```typescript
// 세션 시작
{ type: 'task_started', actor: 'triage', data: { input: '환불 문의' } }

// 도구 호출
{ type: 'tool_called', actor: 'triage', data: { tool: 'searchKB', params: {...} } }

// 도구 결과
{ type: 'tool_result', actor: 'triage', data: { result: {...} }, metadata: { duration: 230 } }

// 전환
{ type: 'transfer', actor: 'triage', target: 'billing', data: { reason: '환불 처리 필요' } }

// 완료
{ type: 'task_completed', actor: 'billing', data: { output: '환불 완료' } }
```

### Session 클래스

```typescript
class Session {
  private events: Event[] = [];

  // 이벤트 추가
  addEvent(event: Omit<Event, 'id' | 'timestamp'>): void {
    this.events.push({
      id: generateId(),
      timestamp: new Date(),
      ...event
    });
  }

  // 조회
  getEvents(filter?: { type?: EventType; actor?: string }): Event[] {
    return this.events.filter(e => {
      if (filter?.type && e.type !== filter.type) return false;
      if (filter?.actor && e.actor !== filter.actor) return false;
      return true;
    });
  }

  // 통계
  getStats(): SessionStats {
    return {
      totalEvents: this.events.length,
      totalDuration: this.calculateDuration(),
      totalCost: this.calculateCost(),
      transferCount: this.getEvents({ type: 'transfer' }).length,
      toolCallCount: this.getEvents({ type: 'tool_called' }).length,
    };
  }

  // 타임라인 생성
  getTimeline(): TimelineEntry[] {
    return this.events.map(e => ({
      time: e.timestamp,
      actor: e.actor,
      action: e.type,
      summary: this.summarize(e)
    }));
  }
}
```

### 활용 사례

**1. 디버깅**
```
문제: 왜 환불이 거부됐지?

타임라인 확인:
1. triage가 요청 받음
2. searchKB 호출 → 환불 정책 조회
3. billing으로 transfer
4. billing이 checkRefundEligibility 호출
5. 결과: eligible=false, reason="90일 초과"  ← 원인 발견
```

**2. 성능 분석**
```
통계:
- 평균 응답 시간: 4.2초
- 도구 호출 평균: 2.3회
- 가장 느린 도구: searchKB (평균 1.8초)
- 전환 발생률: 35%
```

**3. 비용 추적**
```
세션별 비용:
- 토큰 사용: 2,340 tokens
- API 호출: 3회
- 총 비용: $0.047
```

**4. 감사 로그**
```
언제, 누가, 무엇을, 왜 했는지 전체 기록
→ 컴플라이언스, 보안 감사에 활용
```

---

## 패턴 조합 예시

### 고객 지원 시스템

```typescript
const customerSupportProject = {
  // 1. 분해
  structure: {
    project: 'customer-support',
    agents: {
      triage: {
        subAgents: ['faq', 'classifier']
      },
      technical: {
        subAgents: ['bugReport', 'howTo']
      },
      billing: {
        subAgents: ['refund', 'payment']
      }
    }
  },

  // 2. 위임
  relations: {
    triage: {
      canTransferTo: ['technical', 'billing'],
      canDelegateTo: ['search']
    }
  },

  // 3. 권한
  permissions: {
    faq: ['searchKB', 'readDocs'],
    refund: ['searchKB', 'lookupOrder', 'processRefund'],
    bugReport: ['searchKB', 'createTicket', 'notifyDev']
  },

  // 4. 제약
  constraints: {
    maxSteps: 20,
    maxTransfers: 3,
    timeoutMs: 180000  // 3분
  },

  // 5. 컨텍스트
  context: {
    userProfile: { source: 'crm', fetchOn: 'initialization' },
    orderHistory: { source: 'orders-api', fetchOn: 'initialization' }
  },

  // 6. 추적
  tracing: {
    enabled: true,
    events: ['all'],
    exportTo: 'analytics-db'
  }
};
```

---

## 패턴 선택 가이드

| 상황 | 적용 패턴 |
|------|----------|
| 복잡한 문제 해결 | 분해 패턴 |
| 전문가에게 넘겨야 할 때 | Transfer |
| 정보 수집 후 종합할 때 | Delegation |
| 보안/접근 제어 필요 | 권한 패턴 |
| 비용/시간 제한 필요 | 제약 패턴 |
| 외부 정보 필요 | 컨텍스트 패턴 |
| 디버깅/분석 필요 | 추적 패턴 |

---

## 체크리스트

새 프로젝트 설계 시:

- [ ] 계층 구조 정의 (Project → Agent → SubAgent)
- [ ] 각 SubAgent의 책임 명확화
- [ ] Transfer/Delegation 관계 정의
- [ ] 권한 매트릭스 작성
- [ ] 제약 조건 설정
- [ ] 필요한 컨텍스트 정의
- [ ] 추적할 이벤트 결정

---

## 참고

- 원본 분석: [inkeep-agents-ai-design-concepts.md](./inkeep-agents-ai-design-concepts.md)
- 원본 저장소: https://github.com/inkeep/inkeep-agents
