"""Clients for single-lookup registers: e-District, AISHE, UDISE+, APAAR, UGC-NTA and NPCI."""

from typing import Any

import httpx

from app.config import Settings
from app.sources.http import SourceUnavailable, raise_for_source


class RegistersClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http = http
        self.base = settings.registers_url.rstrip("/")
        self.headers = {"X-API-Key": settings.registers_api_key}

    async def edistrict_certificate(self, state_code: str, number: str) -> dict[str, Any] | None:
        return await self._get(f"/edistrict/{state_code}/certificates/{number}", "e-District")

    async def aishe_institution(self, code: str) -> dict[str, Any] | None:
        return await self._get(f"/aishe/institutions/{code}", "AISHE")

    async def udise_school(self, code: str) -> dict[str, Any] | None:
        return await self._get(f"/udise/schools/{code}", "UDISE+")

    async def net_result(self, roll_number: str) -> dict[str, Any] | None:
        return await self._get(f"/nta/net-results/{roll_number}", "UGC-NTA")

    async def udise_student_contact(self, student_ref: str) -> dict[str, Any] | None:
        return await self._get(f"/udise/students/{student_ref}/contact", "UDISE+")

    async def apaar_student(self, apaar_id: str) -> dict[str, Any] | None:
        return await self._get(f"/apaar/students/{apaar_id}", "APAAR")

    async def aadhaar_seeding(self, reference_key: str) -> dict[str, Any] | None:
        return await self._request(
            "POST", "/npci/aadhaar-seeding", "NPCI", json={"reference_key": reference_key}
        )

    async def udise_students(self, **filters: Any) -> dict[str, Any]:
        result = await self._get("/udise/students", "UDISE+", params=filters)
        assert result is not None
        return result

    async def _get(self, path: str, source: str, **kwargs: Any) -> dict[str, Any] | None:
        return await self._request("GET", path, source, **kwargs)

    async def _request(
        self, method: str, path: str, source: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        try:
            response = await self.http.request(
                method, f"{self.base}{path}", headers=self.headers, **kwargs
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"{source} could not be reached: {error}") from error
        raise_for_source(response, source)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise SourceUnavailable(f"{source} refused the request ({response.status_code})")
        return response.json()
