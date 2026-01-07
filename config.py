import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI 호환 API 설정
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "claude-opus-4-5-20251101"

    # 데이터 저장 경로
    data_path: str = "/data"

    # Documents 기준 경로
    local_base_path: str = "/home/amos/Documents"  # 호스트와 동일한 경로로 마운트
    remote_base_path: str = "~/Documents"    # SSH 원격 경로

    # 로컬 머신 별칭 (서버가 돌아가는 머신)
    # "local" 외에 이 값과 일치하면 로컬로 처리
    local_machine: str = "nuc"

    # 원격 머신 (SSH) - 별칭:주소 형태, 쉼표로 구분
    # 예: "mac:amos@100.73.228.37,server:user@192.168.1.100"
    remote_hosts: str = ""  # 기본값 없음, .env에서 설정

    # Jira API
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    @property
    def remote_hosts_map(self) -> dict[str, str]:
        """원격 호스트 별칭 맵 반환"""
        if not self.remote_hosts:
            return {}
        hosts = {}
        for entry in self.remote_hosts.split(","):
            entry = entry.strip()
            if ":" in entry:
                alias, address = entry.split(":", 1)
                hosts[alias.lower()] = address
        return hosts

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = ""
        env_file = ".env"


settings = Settings()
