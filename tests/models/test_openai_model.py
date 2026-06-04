import asyncio

import pytest
from pydantic import BaseModel

from api_testing.models.llms.openai_model import OpenAIModel, _validate_schema_json


class OutputSchema(BaseModel):
    status: str
    reason: str


class FakeAsyncCompletions:
    def __init__(self, content='```json\n{"status":"ok","reason":"valid"}\n```'):
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        message = type(
            "Message",
            (),
            {"content": self.content},
        )()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class FakeCompletions:
    def __init__(self, content='{"status":"ok","reason":"valid"}'):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def test_validate_schema_json_reports_top_level_validation_error():
    response = '```json\n{"wrong":[100.5,13.77]}\n```'

    with pytest.raises(Exception) as exc_info:
        _validate_schema_json(response, OutputSchema)

    message = str(exc_info.value)
    assert "status" in message
    assert "reason" in message
    assert "Input should be an object" not in message


def test_openai_structured_generate_sends_json_response_format():
    model = object.__new__(OpenAIModel)
    model.model_name = "gpt-test"
    model.temperature = 0.0
    completions = FakeCompletions()
    model.client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": completions})()},
    )()

    parsed, _ = model.generate(
        prompt="Return JSON.",
        system_prompt="System rules.",
        schema=OutputSchema,
    )

    assert completions.kwargs["response_format"] == {"type": "json_object"}
    system_message = completions.kwargs["messages"][0]["content"]
    assert "System rules." in system_message
    assert '"status"' in system_message
    assert '"reason"' in system_message
    assert parsed.status == "ok"


def test_openai_async_structured_generate_parses_fenced_json():
    model = object.__new__(OpenAIModel)
    model.model_name = "gpt-test"
    model.temperature = 0.0
    completions = FakeAsyncCompletions()
    model.async_client = type(
        "AsyncClient",
        (),
        {"chat": type("Chat", (), {"completions": completions})()},
    )()

    parsed, _ = asyncio.run(
        model.a_generate(
            prompt="Return JSON.",
            system_prompt="System rules.",
            schema=OutputSchema,
        )
    )

    assert parsed.status == "ok"
    assert parsed.reason == "valid"
    assert completions.kwargs["response_format"] == {"type": "json_object"}
    system_message = completions.kwargs["messages"][0]["content"]
    assert "System rules." in system_message
    assert '"status"' in system_message
    assert '"reason"' in system_message
