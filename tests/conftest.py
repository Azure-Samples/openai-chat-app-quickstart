import pytest
import pytest_asyncio

import quartapp

from . import mock_cred


@pytest.fixture
def mock_openai_responses(monkeypatch):
    class MockResponseEvent:
        def __init__(self, event_type: str, delta: str | None = None):
            self.type = event_type
            self.delta = delta

    class AsyncResponsesIterator:
        def __init__(self, answer: str):
            self.event_index = 0
            self.events = []
            for answer_index, answer_delta in enumerate(answer.split(" ")):
                if answer_index > 0:
                    answer_delta = " " + answer_delta
                self.events.append(MockResponseEvent("response.output_text.delta", answer_delta))
            self.events.append(MockResponseEvent("response.completed"))

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.event_index < len(self.events):
                next_event = self.events[self.event_index]
                self.event_index += 1
                return next_event
            raise StopAsyncIteration

    def last_message_from_input(input_messages):
        if not input_messages:
            return ""
        content = input_messages[-1].get("content")
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in {"input_text", "output_text"}
            )
        return content

    async def mock_acreate(*args, **kwargs):
        # Only mock a stream=True response
        last_message = last_message_from_input(kwargs.get("input"))
        if last_message == "What is the capital of France?":
            return AsyncResponsesIterator("The capital of France is Paris.")
        elif last_message == "What is the capital of Germany?":
            return AsyncResponsesIterator("The capital of Germany is Berlin.")
        else:
            raise ValueError(f"Unexpected message: {last_message}")

    monkeypatch.setattr("openai.resources.responses.AsyncResponses.create", mock_acreate)


@pytest.fixture
def mock_defaultazurecredential(monkeypatch):
    monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", mock_cred.MockAzureCredential)
    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)


@pytest_asyncio.fixture
async def client(monkeypatch, mock_openai_responses, mock_defaultazurecredential):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "test-chatgpt")

    quart_app = quartapp.create_app(testing=True)

    async with quart_app.test_app() as test_app:
        quart_app.config.update({"TESTING": True})

        yield test_app.test_client()
