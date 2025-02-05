import pytest
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential

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
            "messages": [
                {"role": "user", "content": "What is the capital of France?"},
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
            "messages": [
                {"role": "user", "content": "What is the capital of France?"},
                {"role": "assistant", "content": "Paris"},
                {"role": "user", "content": "What is the capital of Germany?"},
            ]
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.jsonlines")


@pytest.mark.asyncio
async def test_openai_managedidentity(monkeypatch):
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_INFERENCE_ENDPOINT", "test-deepseek-service.ai.azure.com")

    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)

    quart_app = quartapp.create_app(testing=True)

    async with quart_app.test_app():
        assert not isinstance(quart_app.blueprints["chat"].ai_client._config.credential, AzureKeyCredential)
        assert isinstance(quart_app.blueprints["chat"].ai_client._config.credential, AsyncTokenCredential)
