import json
import os
import datetime

from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ChainedTokenCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from openai import AsyncAzureOpenAI
from quart import (
    Blueprint,
    Response,
    current_app,
    render_template,
    request,
    stream_with_context,
)

bp = Blueprint("chat", __name__, template_folder="templates", static_folder="static")

# Add a path for logs
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'logs', 'chat_logs.json')

# Ensure the logs directory exists
if not os.path.exists(os.path.dirname(LOG_FILE_PATH)):
    os.makedirs(os.path.dirname(LOG_FILE_PATH))

@bp.before_app_serving
async def configure_openai():
    # Use ManagedIdentityCredential with the client_id for user-assigned managed identities
    user_assigned_managed_identity_credential = ManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))

    # Use AzureDeveloperCliCredential with the current tenant.
    azure_dev_cli_credential = AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID"), process_timeout=60)

    # Create a ChainedTokenCredential with ManagedIdentityCredential and AzureDeveloperCliCredential
    azure_credential = ChainedTokenCredential(user_assigned_managed_identity_credential, azure_dev_cli_credential)
    current_app.logger.info("Using Azure OpenAI with credential")

    # Get the token provider for Azure OpenAI based on the selected Azure credential
    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
    if not os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"):
        raise ValueError("AZURE_OPENAI_CHAT_DEPLOYMENT is required for Azure OpenAI")

    # Create the Asynchronous Azure OpenAI client
    bp.openai_client = AsyncAzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_ad_token_provider=token_provider,
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
        # This sends all messages, so API request may exceed token limits
        all_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ] + request_messages

        # Collect the response from Azure OpenAI
        response_content = []
        chat_coroutine = bp.openai_client.chat.completions.create(
            # Azure Open AI takes the deployment name as the model name
            model=bp.openai_model,
            messages=all_messages,
            stream=True,
        )
        try:
            async for event in await chat_coroutine:
                event_dict = event.model_dump()
                if event_dict["choices"]:
                    response_content.append(event_dict["choices"][0])
                    yield json.dumps(event_dict["choices"][0], ensure_ascii=False) + "\n"

            # Log the chat interaction to file
            log_chat_interaction(request_messages, response_content)

        except Exception as e:
            current_app.logger.error(e)
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"

    return Response(response_stream())


def log_chat_interaction(user_messages, response_content):
    """Log the interaction to a JSON file for analysis."""
    log_entry = {
        "timestamp": str(datetime.datetime.now()),
        "user_messages": user_messages,
        "assistant_responses": response_content
    }

    # Append to the JSON log file
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r+', encoding='utf-8') as f:
            logs = json.load(f)
            logs.append(log_entry)
            f.seek(0)
            json.dump(logs, f, indent=4)
    else:
        with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump([log_entry], f, indent=4)
