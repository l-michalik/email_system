import requests
from dotenv import load_dotenv
from os import getenv

load_dotenv()


def get_env_var(key: str) -> str:
    """Fetch environment variable or raise error if missing."""
    value = getenv(key)
    if not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def get_token() -> str:
    """Authenticate and return access token from CRM API."""
    response = requests.post(
        f"{get_env_var('CRM_BASE_URL')}/oauth/token",
        data={
            "grant_type": "password",
            "client_id": get_env_var("CRM_CLIENT_ID"),
            "client_secret": get_env_var("CRM_CLIENT_SECRET"),
            "username": get_env_var("CRM_USERNAME"),
            "password": get_env_var("CRM_PASSWORD"),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]
