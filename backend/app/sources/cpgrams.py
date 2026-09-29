"""Client for CPGRAMS, the Centralised Public Grievance Redress and Monitoring System."""

from typing import Any

import httpx

from app.config import Settings
from app.sources.http import SourceUnavailable, raise_for_source

MINISTRY = "Ministry of Tribal Affairs"


class CpgramsClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http = http
        self.base = settings.cpgrams_url.rstrip("/")
        self.headers = {"X-API-Key": settings.cpgrams_api_key}

    async def lodge(self, **grievance: Any) -> dict[str, Any]:
        return await self._request("POST", "/grievances", json={"ministry": MINISTRY, **grievance})

    async def status(self, registration_number: str) -> dict[str, Any]:
        _, _, year, serial = registration_number.split("/")
        return await self._request("GET", f"/grievances/{year}/{serial}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self.http.request(
                method, f"{self.base}{path}", headers=self.headers, **kwargs
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"CPGRAMS could not be reached: {error}") from error
        raise_for_source(response, "CPGRAMS")
        if response.status_code >= 400:
            raise SourceUnavailable(f"CPGRAMS refused the request ({response.status_code})")
        return response.json()
