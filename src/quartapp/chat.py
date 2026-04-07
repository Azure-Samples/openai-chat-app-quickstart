import json
import os
from typing import Any

from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ChainedTokenCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from openai import AsyncOpenAI
from quart import (
    Blueprint,
    Response,
    current_app,
    render_template,
    request,
    stream_with_context,
)

bp = Blueprint("chat", __name__, template_folder="templates", static_folder="static")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") in {"text", "input_text", "output_text"}
            and isinstance(item.get("text"), str)
        )

    raise ValueError("Message content must be a string or a list of text content items.")


def _message_to_response_input(message: dict[str, Any]) -> dict[str, Any]:
    content_type = "output_text" if message["role"] == "assistant" else "input_text"

    return {
        "type": "message",
        "role": message["role"],
        "content": [{"type": content_type, "text": _content_to_text(message["content"])}],
    }


@bp.before_app_serving
async def configure_openai():
    # Use ManagedIdentityCredential with the client_id for user-assigned managed identities
    user_assigned_managed_identity_credential = ManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))

    # Use AzureDeveloperCliCredential with the current tenant.
    azure_dev_cli_credential = AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID"), process_timeout=60)

    # Create a ChainedTokenCredential with ManagedIdentityCredential and AzureDeveloperCliCredential
    #  - ManagedIdentityCredential is used for deployment on Azure Container Apps

    #  - AzureDeveloperCliCredential is used for local development
    # The order of the credentials is important, as the first valid token is used
    # For more information check out:

    # https://learn.microsoft.com/azure/developer/python/sdk/authentication/credential-chains?tabs=ctc#chainedtokencredential-overview
    azure_credential = ChainedTokenCredential(user_assigned_managed_identity_credential, azure_dev_cli_credential)
    current_app.logger.info("Using Azure OpenAI Responses API with credential")

    # Get the token provider for Azure OpenAI based on the selected Azure credential
    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not openai_endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
    if not os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"):
        raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT is required for Azure OpenAI")

    # Create the asynchronous OpenAI client against Azure's v1 endpoint.
    bp.azure_credential = azure_credential
    bp.openai_client = AsyncOpenAI(
        base_url=f"{openai_endpoint.rstrip('/')}/openai/v1/",
        api_key=token_provider,
    )
    # Set the model name to the Azure OpenAI model deployment name
    bp.openai_model = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")


@bp.after_app_serving
async def shutdown_openai():
    await bp.openai_client.close()
    await bp.azure_credential.close()


@bp.get("/")
async def index():
    return await render_template("index.html")


@bp.post("/chat/stream")
async def chat_handler():
    request_messages = (await request.get_json())["messages"]

    @stream_with_context
    async def response_stream():
        all_messages = [
            {
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": "You are a helpful assistant."}],
            },
            *[_message_to_response_input(message) for message in request_messages],
        ]

        try:
            async with bp.openai_client.responses.stream(
                # Azure OpenAI takes the deployment name as the model name.
                model=bp.openai_model,
                input=all_messages,
                store=False,
            ) as openai_stream:
                async for event in openai_stream:
                    if event.type == "response.output_text.delta":
                        yield json.dumps({"type": event.type, "delta": event.delta}, ensure_ascii=False) + "\n"
        except Exception as e:
            current_app.logger.exception("Responses stream failed")
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream(), mimetype="application/x-ndjson")
