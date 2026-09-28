"""The language model behind JAGO, reached through any OpenAI-compatible chat API.

Kept behind one small interface so the provider can be chosen, and changed, by measurement.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.config import Settings


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class ChatModel(Protocol):
    async def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn: ...


class ModelUnavailable(Exception):
    pass


class OpenAICompatibleModel:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        assert settings.llm_base_url and settings.llm_model
        self.url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        self.model = settings.llm_model
        self.headers = (
            {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
        )
        self.http = http

    async def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn:
        try:
            response = await self.http.post(
                self.url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                },
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ModelUnavailable(str(error)) from error
        message = response.json()["choices"][0]["message"]
        calls = [
            ToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=json.loads(call["function"].get("arguments") or "{}"),
            )
            for call in message.get("tool_calls") or []
        ]
        return ModelTurn(text=message.get("content"), tool_calls=calls)
