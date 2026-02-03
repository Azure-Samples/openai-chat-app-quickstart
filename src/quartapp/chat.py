import json
import os

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
    current_app.logger.info("Using Azure OpenAI with credential")

    # Get the token provider for Azure OpenAI based on the selected Azure credential
    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
    if not os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"):
        raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT is required for Azure OpenAI")

    # Create the Asynchronous OpenAI client with Azure OpenAI endpoint
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip("/")
    bp.openai_client = AsyncOpenAI(
        base_url=f"{azure_endpoint}/openai/v1",
        api_key=token_provider,
    )
    # Set the model name to the Azure OpenAI model deployment name
    bp.openai_model = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")


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
        # Build input items for Responses API
        input_items = [
            {"role": "system", "content": [{"type": "input_text", "text": "You are a helpful assistant."}]},
        ]
        for msg in request_messages:
            content_type = "output_text" if msg["role"] == "assistant" else "input_text"
            input_items.append(
                {
                    "role": msg["role"],
                    "content": [{"type": content_type, "text": msg["content"]}],
                }
            )

        response_stream = await bp.openai_client.responses.create(
            # Azure OpenAI takes the deployment name as the model name
            model=bp.openai_model,
            input=input_items,
            stream=True,
            store=False,
        )
        try:
            async for event in response_stream:
                if event.type == "response.output_text.delta":
                    yield json.dumps({"delta": {"content": event.delta, "role": None}}, ensure_ascii=False) + "\n"
                elif event.type == "response.completed":
                    finish_event = {"delta": {"content": None, "role": None}, "finish_reason": "stop"}
                    yield json.dumps(finish_event, ensure_ascii=False) + "\n"
        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream())
