from __future__ import annotations

import requests

from config.settings import load_settings


def get_env_var(key: str) -> str:
    settings = load_settings()
    mapping = {
        "CRM_BASE_URL": settings.crm_base_url,
        "CRM_CLIENT_ID": settings.crm_client_id,
        "CRM_CLIENT_SECRET": settings.crm_client_secret,
        "CRM_USERNAME": settings.crm_username,
        "CRM_PASSWORD": settings.crm_password,
    }
    return mapping[key]


def get_token() -> str:
    settings = load_settings()
    response = requests.post(
        settings.token_url,
        data={
            "grant_type": "password",
            "client_id": settings.crm_client_id,
            "client_secret": settings.crm_client_secret,
            "username": settings.crm_username,
            "password": settings.crm_password,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]
