FROM python:3.11-slim

# SSH 클라이언트, Git, Node.js 설치
RUN apt-get update && apt-get install -y openssh-client git curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Claude CLI 설치
RUN npm install -g @anthropic-ai/claude-code

# Git safe.directory 설정 (마운트된 볼륨 신뢰)
RUN git config --global --add safe.directory '*'

WORKDIR /app

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 설치
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# 소스 복사
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
