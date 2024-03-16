import pytest

import quartapp

from . import mock_cred


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_stream_text(client, snapshot):
    response = await client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "What is the capital of France?"},
            ]
        },
    )
    assert response.status_code == 200
    result = await response.get_data()
    snapshot.assert_match(result, "result.json")


@pytest.mark.asyncio
async def test_chat_stream_text_history(client, snapshot):
    response = await client.post(
        "/chat",
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
    snapshot.assert_match(result, "result.json")


@pytest.mark.asyncio
async def test_openai_key(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "test-chatgpt")
    monkeypatch.setenv("AZURE_OPENAI_VERSION", "2023-10-01-preview")

    quart_app = quartapp.create_app()

    async with quart_app.test_app():
        assert quart_app.blueprints["chat"].openai_client.api_key == "test-key"
        assert quart_app.blueprints["chat"].openai_client._azure_ad_token_provider is None


@pytest.mark.asyncio
async def test_openai_managedidentity(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "test-chatgpt")
    monkeypatch.setenv("AZURE_OPENAI_VERSION", "2023-10-01-preview")

    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)

    quart_app = quartapp.create_app()

    async with quart_app.test_app():
        assert quart_app.blueprints["chat"].openai_client._azure_ad_token_provider is not None


@pytest.mark.asyncio
async def test_openai_local(monkeypatch):
    monkeypatch.setenv("LOCAL_OPENAI_ENDPOINT", "http://localhost:8080")

    quart_app = quartapp.create_app()

    async with quart_app.test_app():
        assert quart_app.blueprints["chat"].openai_client.api_key == "no-key-required"
        assert quart_app.blueprints["chat"].openai_client.base_url == "http://localhost:8080"
