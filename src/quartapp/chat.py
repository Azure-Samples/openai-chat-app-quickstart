import json
import os

import azure.identity.aio
import openai
from quart import Blueprint, Response, current_app, render_template, request, stream_with_context

bp = Blueprint("chat", __name__, template_folder="templates", static_folder="static")


@bp.before_app_serving
async def configure_openai():
    openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai.api_version = "2023-03-15-preview"
    if os.getenv("AZURE_OPENAI_KEY"):
        openai.api_type = "azure"
        openai.api_key = os.getenv("AZURE_OPENAI_KEY")
    else:
        openai.api_type = "azure_ad"
        if client_id := os.getenv("AZURE_OPENAI_CLIENT_ID"):
            default_credential = azure.identity.aio.ManagedIdentityCredential(client_id=client_id)
        else:
            default_credential = azure.identity.aio.DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        token = await default_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = token.token


@bp.get("/")
async def index():
    return await render_template("index.html")


@bp.post("/chat")
async def chat_handler():
    request_message = (await request.get_json())["message"]

    @stream_with_context
    async def response_stream():
        chat_coroutine = openai.ChatCompletion.acreate(
            engine=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "chatgpt"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request_message},
            ],
            stream=True,
        )
        async for event in await chat_coroutine:
            current_app.logger.info(event)
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return Response(response_stream())
