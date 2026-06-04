import asyncio
from pydantic import BaseModel

from api_testing.models.llms.gemini_model import GeminiModel


class Verdict(BaseModel):
    answer: str


class FakeUsage:
    prompt_token_count = 1
    candidates_token_count = 2


class FakeResponse:
    text = '{"answer": "ok"}'
    usage_metadata = FakeUsage()


class FakeAsyncModels:
    def __init__(self):
        self.config = None

    async def generate_content(self, **kwargs):
        self.config = kwargs["config"]
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.aio = type("FakeAio", (), {"models": FakeAsyncModels()})()


def test_gemini_async_generate_accepts_system_prompt_with_schema():
    model = object.__new__(GeminiModel)
    model.client = FakeClient()
    model.model_name = "gemini-test"
    model.temperature = 0.7
    model.model_safety_settings = []

    response, _ = asyncio.run(
        model.a_generate(
            prompt="Return JSON",
            system_prompt="Use strict JSON",
            schema=Verdict,
        )
    )

    assert response.answer == "ok"
    assert model.client.aio.models.config.system_instruction == "Use strict JSON"
