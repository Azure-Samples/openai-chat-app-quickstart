import pytest
from openai import AsyncOpenAI

import quartapp

from . import mock_cred


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_stream_text(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "You are a helpful assistant."}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "What is the capital of France?"}],
                },
            ]
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_chat_stream_text_history(client, snapshot):
    response = await client.post(
        "/chat/stream",
        json={
            "input": [
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "You are a helpful assistant."}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "What is the capital of France?"}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Paris"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "What is the capital of Germany?"}],
                },
            ]
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_openai_managedidentity(monkeypatch):
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "test-chatgpt")

    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)
    monkeypatch.setattr("azure.identity.aio.AzureDeveloperCliCredential", mock_cred.MockAzureCredential)

    quart_app = quartapp.create_app(testing=True)

    async with quart_app.test_app():
        openai_client = quart_app.blueprints["chat"].openai_client
        assert isinstance(openai_client, AsyncOpenAI)
        assert str(openai_client.base_url).endswith("/openai/v1/")
