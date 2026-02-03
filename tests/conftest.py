import pytest
import pytest_asyncio

import quartapp

from . import mock_cred


class MockResponseEvent:
    """Mock event for Responses API streaming."""

    def __init__(self, event_type: str, delta: str | None = None):
        self.type = event_type
        self.delta = delta


class AsyncResponsesIterator:
    """Async iterator for mocking Responses API streaming."""

    def __init__(self, answer: str):
        self.events = []
        answer_words = answer.split(" ")
        for word_index, word in enumerate(answer_words):
            # Add whitespace back for words after the first
            if word_index > 0:
                word = " " + word
            self.events.append(MockResponseEvent("response.output_text.delta", word))
        self.events.append(MockResponseEvent("response.completed"))
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.events):
            event = self.events[self.index]
            self.index += 1
            return event
        raise StopAsyncIteration


@pytest.fixture
def mock_openai_responses(monkeypatch):
    async def mock_acreate(*args, **kwargs):
        # Get the last user message from input
        input_items = kwargs.get("input", [])
        last_message = None
        for item in reversed(input_items):
            if item.get("role") == "user":
                content = item.get("content", [])
                if content and isinstance(content, list):
                    last_message = content[0].get("text", "")
                break

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
