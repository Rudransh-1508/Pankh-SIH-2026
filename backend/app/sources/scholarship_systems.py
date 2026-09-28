"""Clients for the systems of record: NSP, SFMP (Canara Bank) and the NOS Portal."""

from typing import Any

import httpx

from app.config import Settings
from app.sources.http import SourceUnavailable, raise_for_source


class ScholarshipSystemsClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http = http
        self.base = settings.registers_url.rstrip("/")
        self.headers = {"X-API-Key": settings.registers_api_key}

    async def nsp_applications(self, reference_key: str) -> list[dict[str, Any]]:
        return (await self._get("/nsp/applications", "NSP", reference_key))["applications"]

    async def sfmp_fellowships(self, reference_key: str) -> list[dict[str, Any]]:
        return (await self._get("/sfmp/fellows", "SFMP", reference_key))["fellows"]

    async def nos_applications(self, reference_key: str) -> list[dict[str, Any]]:
        return (await self._get("/nos/applications", "NOS Portal", reference_key))["applications"]

    async def nsp_registrations(self, offset: int = 0, limit: int = 2000) -> dict[str, Any]:
        """The ministry's export of every NSP registration."""
        try:
            response = await self.http.get(
                f"{self.base}/nsp/registrations",
                params={"offset": offset, "limit": limit},
                headers=self.headers,
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"NSP could not be reached: {error}") from error
        raise_for_source(response, "NSP")
        return response.json()

    async def _get(self, path: str, source: str, reference_key: str) -> dict[str, Any]:
        try:
            response = await self.http.get(
                f"{self.base}{path}", params={"reference_key": reference_key}, headers=self.headers
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"{source} could not be reached: {error}") from error
        raise_for_source(response, source)
        if response.status_code == 404:
            return {"applications": [], "fellows": []}
        if response.status_code >= 400:
            raise SourceUnavailable(f"{source} refused the request ({response.status_code})")
        return response.json()
