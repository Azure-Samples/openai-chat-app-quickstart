import azure.ai.inference.models
import pytest
import pytest_asyncio

import quartapp

from . import mock_cred


@pytest.fixture
def mock_openai_chatcompletion(monkeypatch):
    class AsyncChatCompletionIterator:
        def __init__(self, answer: str):
            self.chunk_index = 0
            self.chunks = [
                azure.ai.inference.models.StreamingChatCompletionsUpdate(
                    id="test-123",
                    created=1703462735,
                    model="DeepSeek-R1",
                    choices=[
                        azure.ai.inference.models.StreamingChatChoiceUpdate(
                            delta=azure.ai.inference.models.StreamingChatResponseMessageUpdate(
                                content=None, role="assistant"
                            ),
                            index=0,
                            finish_reason=None,
                        )
                    ],
                ),
            ]
            answer_deltas = answer.split(" ")
            for answer_index, answer_delta in enumerate(answer_deltas):
                # Completion chunks include whitespace, so we need to add it back in
                if answer_index > 0:
                    answer_delta = " " + answer_delta
                self.chunks.append(
                    azure.ai.inference.models.StreamingChatCompletionsUpdate(
                        id="test-123",
                        created=1703462735,
                        model="DeepSeek-R1",
                        choices=[
                            azure.ai.inference.models.StreamingChatChoiceUpdate(
                                delta=azure.ai.inference.models.StreamingChatResponseMessageUpdate(
                                    content=answer_delta, role=None
                                ),
                                index=0,
                                finish_reason=None,
                            )
                        ],
                    )
                )
            self.chunks.append(
                azure.ai.inference.models.StreamingChatCompletionsUpdate(
                    id="test-123",
                    created=1703462735,
                    model="DeepSeek-R1",
                    choices=[
                        azure.ai.inference.models.StreamingChatChoiceUpdate(
                            delta=azure.ai.inference.models.StreamingChatResponseMessageUpdate(content=None, role=None),
                            index=0,
                            finish_reason="stop",
                        )
                    ],
                )
            )

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.chunk_index < len(self.chunks):
                next_chunk = self.chunks[self.chunk_index]
                self.chunk_index += 1
                return next_chunk
            else:
                raise StopAsyncIteration

    async def mock_complete(*args, **kwargs):
        # Only mock a stream=True completion
        last_message = kwargs.get("messages")[-1]["content"]
        if last_message == "What is the capital of France?":
            return AsyncChatCompletionIterator("The capital of France is Paris.")
        elif last_message == "What is the capital of Germany?":
            return AsyncChatCompletionIterator("The capital of Germany is Berlin.")
        else:
            raise ValueError(f"Unexpected message: {last_message}")

    monkeypatch.setattr("azure.ai.inference.aio.ChatCompletionsClient.complete", mock_complete)


@pytest.fixture
def mock_defaultazurecredential(monkeypatch):
    monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", mock_cred.MockAzureCredential)
    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)


@pytest_asyncio.fixture
async def client(monkeypatch, mock_openai_chatcompletion, mock_defaultazurecredential):
    monkeypatch.setenv("AZURE_INFERENCE_ENDPOINT", "test-deepseek-service.ai.azure.com")

    quart_app = quartapp.create_app(testing=True)

    async with quart_app.test_app() as test_app:
        quart_app.config.update({"TESTING": True})

        yield test_app.test_client()
