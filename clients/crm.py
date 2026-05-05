from __future__ import annotations

from typing import Any

import requests

from config.constants import PAGE_SIZE
from config.settings import AppSettings

CrmItem = dict[str, Any]


class CrmClient:
    def __init__(self, settings: AppSettings, session: requests.Session) -> None:
        self._settings = settings
        self._session = session

    def get_token(self) -> str:
        response = self._session.post(
            self._settings.token_url,
            data={
                "grant_type": "password",
                "client_id": self._settings.crm_client_id,
                "client_secret": self._settings.crm_client_secret,
                "username": self._settings.crm_username,
                "password": self._settings.crm_password,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def fetch_page(
        self,
        token: str,
        query: str,
        start: int,
        page_size: int = PAGE_SIZE,
    ) -> list[CrmItem]:
        response = self._session.post(
            self._settings.search_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            data=query,
            params={
                "returnAllFields": False,
                "limit": page_size,
                "start": start,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["result"]

    def fetch_all_pages(
        self,
        token: str,
        query: str,
        page_size: int = PAGE_SIZE,
    ) -> list[CrmItem]:
        items: list[CrmItem] = []
        start = 1

        while True:
            page = self.fetch_page(token, query, start, page_size)
            items.extend(page)
            if len(page) < page_size:
                break
            start += page_size

        return items
