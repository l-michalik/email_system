from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    crm_base_url: str
    crm_client_id: str
    crm_client_secret: str
    crm_username: str
    crm_password: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str

    @property
    def search_url(self) -> str:
        return f"{self.crm_base_url}/rest/external/site/1/search"

    @property
    def token_url(self) -> str:
        return f"{self.crm_base_url}/oauth/token"


def _get_env_var(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def load_settings() -> AppSettings:
    return AppSettings(
        crm_base_url=_get_env_var("CRM_BASE_URL"),
        crm_client_id=_get_env_var("CRM_CLIENT_ID"),
        crm_client_secret=_get_env_var("CRM_CLIENT_SECRET"),
        crm_username=_get_env_var("CRM_USERNAME"),
        crm_password=_get_env_var("CRM_PASSWORD"),
        smtp_host=_get_env_var("SMTP_HOST"),
        smtp_port=int(_get_env_var("SMTP_PORT")),
        smtp_username=_get_env_var("SMTP_USERNAME"),
        smtp_password=_get_env_var("SMTP_PASSWORD"),
        smtp_from=getenv("SMTP_FROM"),
    )
