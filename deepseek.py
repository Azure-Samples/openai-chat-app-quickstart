import http.client as http_client
import os

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv

http_client.HTTPConnection.debuglevel = 1

load_dotenv(override=True)
# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("urllib3").setLevel(logging.DEBUG)
# logging.getLogger("urllib3").propagate = True


# With keys
# client = ChatCompletionsClient(
#    endpoint=os.environ["AZURE_INFERENCE_ENDPOINT"],
#    credential=AzureKeyCredential(os.environ["AZURE_INFERENCE_KEY"]),
# )

# With Entra ID credential
client = ChatCompletionsClient(
    endpoint=os.environ["AZURE_INFERENCE_ENDPOINT"],
    credential=AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"]),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
    model="DeepSeek-R1",
)

result = client.complete(
    messages=[
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="How many languages are in the world?"),
    ],
    max_tokens=2048,
    stream=True,
)

for update in result:
    if update.choices:
        print(update.choices[0].delta.content, end="")
