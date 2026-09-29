import json

from app.config import get_settings
from app.jago.llm import BedrockModel, to_converse
from app.jago.tools import tool_schemas


class FakeBedrock:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def converse(self, **request):
        self.requests.append(request)
        return {"output": {"message": {"role": "assistant", "content": self.replies.pop(0)}}}


def test_messages_become_alternating_converse_turns_with_tool_results():
    system, turns = to_converse(
        [
            {"role": "system", "content": "You are JAGO."},
            {"role": "user", "content": "Where is my money?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "t1", "function": {"name": "my_applications", "arguments": "{}"}},
                    {"id": "t2", "function": {"name": "my_documents", "arguments": "{}"}},
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "content": json.dumps({"linked": True})},
            {"role": "tool", "tool_call_id": "t2", "content": json.dumps({"issues": []})},
        ]
    )
    assert system == [{"text": "You are JAGO."}]
    assert [t["role"] for t in turns] == ["user", "assistant", "user"]
    assert [b["toolUse"]["name"] for b in turns[1]["content"]] == [
        "my_applications",
        "my_documents",
    ]
    results = turns[2]["content"]
    assert [r["toolResult"]["toolUseId"] for r in results] == ["t1", "t2"]
    assert results[0]["toolResult"]["content"] == [{"json": {"linked": True}}]


async def test_a_bedrock_turn_returns_text_and_tool_calls():
    settings = get_settings().model_copy(update={"bedrock_model_id": "apac.amazon.nova-lite-v1:0"})
    fake = FakeBedrock(
        [
            [
                {"text": "Let me check."},
                {"toolUse": {"toolUseId": "t1", "name": "my_eligibility", "input": {}}},
            ]
        ]
    )
    model = BedrockModel(settings, client=fake)
    turn = await model.respond([{"role": "user", "content": "hi"}], tool_schemas())
    assert turn.text == "Let me check."
    assert [(c.id, c.name, c.arguments) for c in turn.tool_calls] == [("t1", "my_eligibility", {})]
    request = fake.requests[0]
    assert request["modelId"] == "apac.amazon.nova-lite-v1:0"
    names = [t["toolSpec"]["name"] for t in request["toolConfig"]["tools"]]
    assert "my_applications" in names and "scheme_path" in names
    path = next(t for t in request["toolConfig"]["tools"] if t["toolSpec"]["name"] == "scheme_path")
    assert path["toolSpec"]["inputSchema"]["json"]["required"] == []
