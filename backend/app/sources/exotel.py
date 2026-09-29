"""Client for Exotel's call API: connect a Student's phone to the Pankh phone line's flow."""

import httpx

from app.config import Settings
from app.sources.http import SourceUnavailable, raise_for_source


class ExotelClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        assert settings.exotel_url
        self.http = http
        self.base = settings.exotel_url.rstrip("/")
        self.settings = settings

    async def connect(self, to: str, flow_url: str, custom_field: str) -> str:
        """Place a call to `to` that runs the flow at `flow_url`. Returns the call's Sid."""
        try:
            response = await self.http.post(
                f"{self.base}/Calls/connect",
                data={
                    "From": to,
                    "CallerId": self.settings.exotel_caller_id,
                    "Url": flow_url,
                    "CustomField": custom_field,
                },
                headers={"X-API-Key": self.settings.exotel_api_key},
            )
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"Exotel could not be reached: {error}") from error
        raise_for_source(response, "Exotel")
        if response.status_code >= 400:
            raise SourceUnavailable(f"Exotel refused the call ({response.status_code})")
        return response.json()["Call"]["Sid"]
