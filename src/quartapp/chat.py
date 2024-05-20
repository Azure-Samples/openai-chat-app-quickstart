import json
import os

import azure.identity.aio
import openai
from quart import (
    Blueprint,
    Response,
    current_app,
    render_template,
    request,
    stream_with_context,
)

bp = Blueprint("chat", __name__, template_folder="templates", static_folder="static")


@bp.before_app_serving
async def configure_openai():
    client_args = {}
    if os.getenv("LOCAL_OPENAI_ENDPOINT"):
        # Use a local endpoint like llamafile server
        current_app.logger.info("Using local OpenAI-compatible API with no key")
        client_args["api_key"] = "no-key-required"
        client_args["base_url"] = os.getenv("LOCAL_OPENAI_ENDPOINT")
        bp.openai_client = openai.AsyncOpenAI(
            **client_args,
        )
    else:
        # Use an Azure OpenAI endpoint instead,
        # either with a key or with keyless authentication
        if os.getenv("AZURE_OPENAI_KEY"):
            # Authenticate using an Azure OpenAI API key
            # This is generally discouraged, but is provided for developers
            # that want to develop locally inside the Docker container.
            current_app.logger.info("Using Azure OpenAI with key")
            client_args["api_key"] = os.getenv("AZURE_OPENAI_KEY")
        else:
            # Authenticate using the default Azure credential chain
            # See https://docs.microsoft.com/azure/developer/python/azure-sdk-authenticate#defaultazurecredential
            # This will *not* work inside a local Docker container.
            # If using managed user-assigned identity, make sure that AZURE_CLIENT_ID is set
            # to the client ID of the user-assigned identity.
            current_app.logger.info("Using Azure OpenAI with default credential")
            default_credential = azure.identity.aio.DefaultAzureCredential(exclude_shared_token_cache_credential=True)
            client_args["azure_ad_token_provider"] = azure.identity.aio.get_bearer_token_provider(
                default_credential, "https://cognitiveservices.azure.com/.default"
            )
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
        if not os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"):
            raise ValueError("AZURE_OPENAI_CHATGPT_DEPLOYMENT is required for Azure OpenAI")
        bp.openai_client = openai.AsyncAzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            **client_args,
        )


@bp.after_app_serving
async def shutdown_openai():
    await bp.openai_client.close()


@bp.get("/")
async def index():
    return await render_template("index.html")


@bp.post("/chat/stream")
async def chat_handler():
    request_messages = (await request.get_json())["messages"]

    @stream_with_context
    async def response_stream():
        # This sends all messages, so API request may exceed token limits
        all_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ] + request_messages

        chat_coroutine = bp.openai_client.chat.completions.create(
            # Azure Open AI takes the deployment name as the model name
            model=os.environ["AZURE_OPENAI_CHATGPT_DEPLOYMENT"],
            messages=all_messages,
            stream=True,
        )
        try:
            async for event in await chat_coroutine:
                event_dict = event.model_dump()
                if event_dict["choices"]:
                    yield json.dumps(event_dict["choices"][1], ensure_ascii=False) + "\n"
        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream())
