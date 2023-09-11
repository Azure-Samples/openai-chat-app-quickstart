import openai
import pytest
import pytest_asyncio

from . import mock_cred
from src import quartapp


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    class AsyncChatCompletionIterator:
        def __init__(self, answer: str):
            self.answer_index = 0
            self.answer_deltas = answer.split(" ")

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.answer_index < len(self.answer_deltas):
                answer_chunk = self.answer_deltas[self.answer_index]
                self.answer_index += 1
                return openai.util.convert_to_openai_object({"choices": [{"delta": {"content": answer_chunk}}]})
            else:
                raise StopAsyncIteration

    async def mock_acreate(*args, **kwargs):
        return AsyncChatCompletionIterator("The capital of France is Paris.")

    monkeypatch.setattr(openai.ChatCompletion, "acreate", mock_acreate)


@pytest.fixture
def mock_defaultazurecredential(monkeypatch):
    monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", mock_cred.MockAzureCredential)


@pytest_asyncio.fixture
async def client(monkeypatch, mock_openai_chatcompletion, mock_defaultazurecredential):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "test-chatgpt")

    quart_app = quartapp.create_app()

    async with quart_app.test_app() as test_app:
        quart_app.config.update({"TESTING": True})

        yield test_app.test_client()
