"""The language model behind JAGO: any OpenAI-compatible chat API, or AWS Bedrock.

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


class BedrockModel:
    """A model on AWS Bedrock, through the Converse API, which works the same across models.

    JAGO speaks in OpenAI-style messages; they are translated here, so the agent does not know
    which provider it is talking to.
    """

    def __init__(self, settings: Settings, client: Any = None) -> None:
        assert settings.bedrock_model_id
        self.model_id = settings.bedrock_model_id
        if client is None:
            import boto3

            session = boto3.Session(profile_name=settings.aws_profile)
            client = session.client("bedrock-runtime", region_name=settings.aws_region)
        self.client = client

    async def respond(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn:
        import asyncio

        from botocore.exceptions import BotoCoreError, ClientError

        system, conversation = to_converse(messages)
        request: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": conversation,
            "system": system,
            "inferenceConfig": {"temperature": 0.2, "maxTokens": 800},
        }
        if tools:
            request["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "inputSchema": {"json": t["function"]["parameters"]},
                        }
                    }
                    for t in tools
                ]
            }
        try:
            response = await asyncio.to_thread(self.client.converse, **request)
        except (BotoCoreError, ClientError) as error:
            raise ModelUnavailable(str(error)) from error
        texts: list[str] = []
        calls: list[ToolCall] = []
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                texts.append(block["text"])
            elif "toolUse" in block:
                use = block["toolUse"]
                calls.append(ToolCall(use["toolUseId"], use["name"], use.get("input") or {}))
        return ModelTurn(text="\n".join(texts) or None, tool_calls=calls)


def to_converse(messages: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """OpenAI-style messages as Converse's system prompt and alternating user/assistant turns."""
    system: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    def add(role: str, blocks: list[dict[str, Any]]) -> None:
        if not blocks:
            return
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"] += blocks  # Converse needs roles to alternate
        else:
            turns.append({"role": role, "content": blocks})

    for message in messages:
        role, content = message["role"], message.get("content")
        if role == "system":
            system.append({"text": content})
        elif role == "tool":
            try:
                result: Any = json.loads(content)
            except (TypeError, ValueError):
                result = None
            body = [{"json": result}] if isinstance(result, dict) else [{"text": str(content)}]
            add(
                "user",
                [{"toolResult": {"toolUseId": message["tool_call_id"], "content": body}}],
            )
        elif role == "assistant":
            blocks: list[dict[str, Any]] = [{"text": content}] if content else []
            for call in message.get("tool_calls") or []:
                blocks.append(
                    {
                        "toolUse": {
                            "toolUseId": call["id"],
                            "name": call["function"]["name"],
                            "input": json.loads(call["function"]["arguments"] or "{}"),
                        }
                    }
                )
            add("assistant", blocks)
        else:
            add("user", [{"text": content}] if content else [])
    return system, turns
