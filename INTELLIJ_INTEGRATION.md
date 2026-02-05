# IntelliJ Integration Guide

이 프로젝트는 웹 UI에서 원격 서버 또는 로컬 IntelliJ를 즉시 실행할 수 있는 기능을 제공합니다.

## 1. 작동 원리

### 원격 서버
- **방식**: `jetbrains-gateway://` URL Scheme을 사용하여 JetBrains Gateway를 호출합니다.
- **연결**: Gateway가 원격 서버에 SSH로 접속하여 지정된 `idePath`의 IntelliJ 백엔드를 실행하고, 로컬의 JetBrains Client와 연결합니다.
- **자동 탐색**: 백엔드 API(`/api/projects/ide-path`)가 서버의 `~/.cache/JetBrains/RemoteDev/dist` 경로에서 최신 IDE 바이너리를 찾아 반환합니다.

### 로컬 머신
- **방식**: `idea://` URL Scheme을 사용하여 로컬 IntelliJ를 직접 호출합니다.
- **연결**: 브라우저가 로컬 시스템의 IntelliJ를 즉시 실행하며 프로젝트 경로를 인자로 전달합니다.
- **URL 포맷**: `idea://open?file={project_path}`
- **중요**: 백엔드 API 호출 시 `project_path` 파라미터를 명시적으로 전달해야 개별 워크트리 경로를 열 수 있습니다.
- **요구사항**: IntelliJ Toolbox를 통해 설치했거나, IntelliJ 내에서 `Create Shell Launcher`가 설정되어 있어야 합니다.

## 2. 설정 방법

### 데이터 설정 (`data/projects.yaml`)
각 프로젝트의 `machine` 필드에 따라 실행 방식이 결정됩니다.
- 원격 머신: JetBrains Gateway (SSH) 방식 사용
- `machine: local` 또는 `LOCAL_MACHINE` 값과 일치: 로컬 `idea://` 방식 사용

### 백엔드 환경 변수
원격 접속을 위해 SSH 호스트 정보가 필요합니다.
```env
REMOTE_HOSTS=server:user@your-server-ip,dev:user@192.168.1.50
```

## 3. 트러블슈팅

### "원격 서버에서 IntelliJ 설치 경로를 찾을 수 없습니다"
- 원격 서버에 IntelliJ Remote Development용 백엔드가 설치되어 있지 않은 경우 발생합니다.
- **해결**: JetBrains Gateway에서 수동으로 한 번 해당 서버에 접속하여 프로젝트를 열면 자동으로 IDE 백엔드가 다운로드 및 설치됩니다.

### Mac에서 IntelliJ가 열리지 않을 때
- 브라우저가 `idea://` 프로토콜을 인식하지 못하는 경우입니다.
- **해결**: IntelliJ 내 설정(`Settings > Keymap` 또는 `Tools`)에서 Shell Launcher를 생성하거나, Toolbox 앱을 확인하세요.
