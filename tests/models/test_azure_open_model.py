from pydantic import BaseModel

from api_testing.models.llms.azure_open_model import AzureOpenAIModel


class OutputSchema(BaseModel):
    status: str
    reason: str


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("Message", (), {"content": '{"status":"ok","reason":"valid"}'})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


def test_azure_structured_generate_sends_schema_and_json_response_format():
    model = object.__new__(AzureOpenAIModel)
    model.model_name = "deployment"
    model.temperature = 0.0
    completions = FakeCompletions()
    client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": completions})()},
    )()
    model.load_model = lambda: client

    parsed, _ = model.generate(
        prompt="Compare rules.",
        system_prompt="System rules.",
        schema=OutputSchema,
    )

    system_message = completions.kwargs["messages"][0]["content"]
    assert "System rules." in system_message
    assert '"status"' in system_message
    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert parsed.status == "ok"
