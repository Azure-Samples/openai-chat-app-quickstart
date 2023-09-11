import openai
import pytest

from . import mock_cred
from src import quartapp


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_stream_text(client):
    response = await client.post(
        "/chat",
        json={"message": "What is the capital of France?"},
    )
    assert response.status_code == 200
    result = await response.get_data()
    assert (
        result
        == b'{"choices": [{"delta": {"content": "The"}}]}\n{"choices": [{"delta": {"content": "capital"}}]}\n{"choices": [{"delta": {"content": "of"}}]}\n{"choices": [{"delta": {"content": "France"}}]}\n{"choices": [{"delta": {"content": "is"}}]}\n{"choices": [{"delta": {"content": "Paris."}}]}\n'  # noqa
    )


@pytest.mark.asyncio
async def test_openai_key(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "test-chatgpt")

    quart_app = quartapp.create_app()

    async with quart_app.test_app():
        assert openai.api_type == "azure"


@pytest.mark.asyncio
async def test_openai_managedidentity(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "test-openai-service.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "test-chatgpt")

    monkeypatch.setattr("azure.identity.aio.ManagedIdentityCredential", mock_cred.MockAzureCredential)

    quart_app = quartapp.create_app()

    async with quart_app.test_app():
        assert openai.api_type == "azure_ad"
