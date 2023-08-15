import json
import os

import azure.identity
import openai
from flask import Blueprint, Response, current_app, render_template, request, stream_with_context

bp = Blueprint("chat", __name__, template_folder="templates", static_folder="static")

# Configure OpenAI API
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2023-03-15-preview"
if os.getenv("AZURE_OPENAI_KEY"):
    openai.api_type = "azure"
    openai.api_key = os.getenv("AZURE_OPENAI_KEY")
else:
    openai.api_type = "azure_ad"
    if os.getenv("AZURE_OPENAI_CLIENT_ID"):
        default_credential = azure.identity.ManagedIdentityCredential(client_id=os.getenv("AZURE_OPENAI_CLIENT_ID"))
    else:
        default_credential = azure.identity.DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    openai.api_key = token.token


@bp.get("/")
def index():
    return render_template("index.html")


@bp.post("/chat")
def chat_handler():
    request_message = request.json["message"]

    @stream_with_context
    def response_stream():
        response = openai.ChatCompletion.create(
            engine=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "chatgpt"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request_message},
            ],
            stream=True,
        )
        for event in response:
            current_app.logger.info(event)
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return Response(response_stream())
