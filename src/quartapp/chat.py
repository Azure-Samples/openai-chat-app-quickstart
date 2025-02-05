import json
import os

from azure.ai.inference.aio import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage
from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ChainedTokenCredential,
    ManagedIdentityCredential,
)
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

    if not os.getenv("AZURE_INFERENCE_ENDPOINT"):
        raise ValueError("AZURE_INFERENCE_ENDPOINT is required for Azure OpenAI")

    # Create the Asynchronous Azure OpenAI client
    bp.ai_client = ChatCompletionsClient(
        endpoint=os.environ["AZURE_INFERENCE_ENDPOINT"],
        credential=azure_credential,
        credential_scopes=["https://cognitiveservices.azure.com/.default"],
        model="DeepSeek-R1",
        headers={"x-policy-id": "nil"},
    )


@bp.after_app_serving
async def shutdown_openai():
    await bp.ai_client.close()


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
            SystemMessage(content="You are a helpful assistant."),
        ] + request_messages

        client: ChatCompletionsClient = bp.ai_client
        result = await client.complete(messages=all_messages, max_tokens=2048, stream=True)

        try:
            is_thinking = False
            async for update in result:
                if update.choices:
                    content = update.choices[0].delta.content
                    if content == "<think>":
                        is_thinking = True
                        update.choices[0].delta.content = None
                        update.choices[0].delta.reasoning_content = ""
                    elif content == "</think>":
                        is_thinking = False
                        update.choices[0].delta.content = None
                        update.choices[0].delta.reasoning_content = ""
                    elif content:
                        if is_thinking:
                            yield json.dumps(
                                {"delta": {"content": None, "reasoning_content": content, "role": "assistant"}},
                                ensure_ascii=False,
                            ) + "\n"
                        else:
                            yield json.dumps(
                                {"delta": {"content": content, "reasoning_content": None, "role": "assistant"}},
                                ensure_ascii=False,
                            ) + "\n"
        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream(), mimetype="application/json")
