# Worktreee 설계 노트

## 프로젝트 네이밍

### 현재 상황
- 프로젝트 이름이 YAML key로 사용됨
- `machine` 필드로 어느 머신인지 이미 구분 가능

### 규칙
- **프로젝트 이름에 머신명(nuc, mac 등) 붙이지 말 것**
- `machine` 필드가 이미 있으므로 중복 정보임

### 예시
```yaml
# Good
my-gateway:
  machine: local
  repo_path: ~/Documents/my-org/my-gateway

# Bad
my-gateway-server:
  machine: server
  repo_path: ~/Documents/my-org/my-gateway
```

### TODO
- [ ] 같은 프로젝트를 여러 머신에 등록할 수 있도록 구조 개선 검토
  - 현재: 프로젝트명이 unique key
  - 개선안: `프로젝트명 + machine` 조합을 key로 사용
