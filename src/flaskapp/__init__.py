import os
import json
import time

from flask import Flask, Response, render_template, request
import openai
import azure.identity
import dotenv

dotenv.load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

# Configure OpenAI API
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT") 
openai.api_version = "2023-03-15-preview"
default_credential = azure.identity.DefaultAzureCredential()
token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_type = "azure_ad"
openai.api_key = token.token

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/chat")
def chat_handler():
    request_message = request.args.get('message')
    def eventStream():
        response = openai.ChatCompletion.create(
            engine="chatgpt", # engine = "deployment_name"
            messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": request_message}
                ],
            stream=True
        )
        for event in response:
            print(event)
            if event['choices'][0]['delta'].get('content'):
                response_message =event['choices'][0]['delta']['content']
                json_data = json.dumps({"text": response_message, "sender": "assistant"})
                yield f'event:message\ndata: {json_data}\n\n'
        yield f'event: bye\ndata: bye-bye\n\n'
    return Response(eventStream(), mimetype="text/event-stream")