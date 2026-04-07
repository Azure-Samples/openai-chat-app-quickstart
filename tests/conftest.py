from dataclasses import dataclass

import pytest
import pytest_asyncio

import quartapp

from . import mock_cred


@pytest.fixture
def mock_openai_responses_stream(monkeypatch):
    @dataclass
    class MockResponseEvent:
        type: str
        delta: str | None = None

    class AsyncResponseStream:
        def __init__(self, answer: str):
            self._chunk_index = 0
            self._chunks = []
            for answer_index, answer_delta in enumerate(answer.split(" ")):
                if answer_index > 0:
                    answer_delta = " " + answer_delta
                self._chunks.append(MockResponseEvent(type="response.output_text.delta", delta=answer_delta))

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._chunk_index < len(self._chunks):
                next_chunk = self._chunks[self._chunk_index]
                self._chunk_index += 1
                return next_chunk
            raise StopAsyncIteration

    class AsyncResponseStreamManager:
        def __init__(self, answer: str):
            self._stream = AsyncResponseStream(answer)

        async def __aenter__(self):
            return self._stream

        async def __aexit__(self, exc_type, exc, exc_tb):
            return None

    def mock_stream(*args, **kwargs):
        response_input = kwargs.get("input")
        last_message = response_input[-1]["content"][0]["text"]

        if len(response_input) > 2:
            assistant_message = response_input[-2]
            assert assistant_message["role"] == "assistant"
            assert assistant_message["content"][0]["type"] == "output_text"

        assert kwargs.get("store") is False
        if last_message == "What is the capital of France?":
            return AsyncResponseStreamManager("The capital of France is Paris.")
        if last_message == "What is the capital of Germany?":
            return AsyncResponseStreamManager("The capital of Germany is Berlin.")
        raise ValueError(f"Unexpected message: {last_message}")

    monkeypatch.setattr("openai.resources.responses.responses.AsyncResponses.stream", mock_stream)


@pytest.fixture
def mock_azure_credentials(monkeypatch):
    monkeypatch.setattr("azure.identity.aio.AzureDeveloperCliCredential", mock_cred.MockAzureCredential)
    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)


@pytest_asyncio.fixture
async def client(monkeypatch, mock_openai_responses_stream, mock_azure_credentials):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "test-chatgpt")

    quart_app = quartapp.create_app(testing=True)

    async with quart_app.test_app() as test_app:
        quart_app.config.update({"TESTING": True})

        yield test_app.test_client()
