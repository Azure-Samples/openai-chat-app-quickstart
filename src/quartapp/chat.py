import base64
import json
import os

import azure.identity.aio
from azure.keyvault.secrets.aio import SecretClient
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


def get_azure_credential():
    if not hasattr(bp, "azure_credential"):
        bp.azure_credential = azure.identity.aio.DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    return bp.azure_credential

@bp.before_app_serving
async def configure_openai():
    client_args = {}
    if os.getenv("LOCAL_OPENAI_ENDPOINT"):
        current_app.logger.info("Using local OpenAI-compatible API with no key")
        client_args["api_key"] = "no-key-required"
        client_args["base_url"] = os.getenv("LOCAL_OPENAI_ENDPOINT")
        bp.openai_client = openai.AsyncOpenAI(
            **client_args,
        )
    elif os.getenv("OPENAICOM_API_KEY_SECRET_NAME") or os.getenv("OPENAICOM_API_KEY"):
        current_app.logger.info("Using OpenAI.com OpenAI with key")
        if os.getenv("OPENAICOM_API_KEY"):
            client_args["api_key"] = os.getenv("OPENAICOM_API_KEY")
        else:
            OPENAICOM_API_KEY_SECRET_NAME = os.getenv("OPENAICOM_API_KEY_SECRET_NAME")
            AZURE_KEY_VAULT_NAME = os.getenv("AZURE_KEY_VAULT_NAME")
            async with SecretClient(
                vault_url=f"https://{AZURE_KEY_VAULT_NAME}.vault.azure.net", credential=get_azure_credential()
            ) as key_vault_client:
                openai_api_key = (await key_vault_client.get_secret(OPENAICOM_API_KEY_SECRET_NAME)).value
            client_args["api_key"] = openai_api_key
        bp.openai_client = openai.AsyncOpenAI(
            **client_args,
        )
        bp.openai_model_arg = os.getenv("OPENAI_MODEL_NAME") or "gpt-3.5-turbo"
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
            # This will *not* work inside a Docker container.
            # This should work on ACA as long as AZURE_CLIENT_ID is set to the user-assigned managed identity
            current_app.logger.info("Using Azure OpenAI with default credential")
            default_credential = get_azure_credential()
            client_args["azure_ad_token_provider"] = azure.identity.aio.get_bearer_token_provider(
                default_credential, "https://cognitiveservices.azure.com/.default"
            )
        bp.openai_client = openai.AsyncAzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            **client_args,
        )
        # Note: Azure OpenAI takes the deployment name as the model name
        bp.openai_model_arg = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")


@bp.after_app_serving
async def shutdown_openai():
    await bp.openai_client.close()


# Extract the username for display from the base64 encoded header
# X-MS-CLIENT-PRINCIPAL from the 'name' claim.
#
# Fallback to `default_username` if the header is not present.
def extract_username(headers, default_username="You"):
    if "X-MS-CLIENT-PRINCIPAL" not in headers:
        return default_username

    token = json.loads(base64.b64decode(headers.get("X-MS-CLIENT-PRINCIPAL")))
    claims = {claim["typ"]: claim["val"] for claim in token["claims"]}
    return claims.get("name", default_username)


@bp.get("/")
async def index():
    username = extract_username(request.headers)
    return await render_template("index.html", username=username)


@bp.post("/chat")
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
            model=bp.openai_model_arg,
            messages=all_messages,
            stream=True,
        )
        try:
            async for event in await chat_coroutine:
                yield json.dumps(event.model_dump(), ensure_ascii=False) + "\n"
        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream())
