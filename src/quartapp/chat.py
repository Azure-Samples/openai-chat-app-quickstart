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

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip("/")
    if azure_endpoint.endswith("/openai/v1"):
        base_url = azure_endpoint
    else:
        base_url = f"{azure_endpoint}/openai/v1"

    # Create the Asynchronous OpenAI client for Azure OpenAI
    bp.openai_client = AsyncOpenAI(
        base_url=base_url,
        api_key=token_provider,
    )
    bp.openai_token_provider = token_provider
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
        def to_response_message(message):
            role = message.get("role")
            content = message.get("content")
            content_type = "input_text" if role in {"system", "user"} else "output_text"

            if isinstance(content, list):
                normalized = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        normalized.append({"type": content_type, "text": part.get("text", "")})
                    elif isinstance(part, dict):
                        normalized.append(part)
                    else:
                        normalized.append({"type": content_type, "text": str(part)})
                return {"role": role, "content": normalized}

            if isinstance(content, str):
                return {"role": role, "content": [{"type": content_type, "text": content}]}

            return {"role": role, "content": [{"type": content_type, "text": str(content)}]}

        # This sends all messages, so API request may exceed token limits
        all_messages = [
            {"role": "system", "content": [{"type": "input_text", "text": "You are a helpful assistant."}]},
        ] + [to_response_message(message) for message in request_messages]

        response_stream = await bp.openai_client.responses.create(
            # Azure OpenAI takes the deployment name as the model name
            model=bp.openai_model,
            input=all_messages,
            stream=True,
            store=False,
        )
        try:
            async for event in response_stream:
                if event.type == "response.output_text.delta":
                    yield json.dumps({"type": event.type, "delta": event.delta}, ensure_ascii=False) + "\n"
                elif event.type == "response.completed":
                    yield json.dumps({"type": event.type}, ensure_ascii=False) + "\n"
        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"type": "response.error", "error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream())
