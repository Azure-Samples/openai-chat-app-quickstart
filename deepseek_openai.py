import logging
import os

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

load_dotenv(override=True)
logging.basicConfig(level=logging.DEBUG)

credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
# ml.azure.com for serverless, cognitiveservices for AIServices
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

client_selection = "AzureOpenAI"
if client_selection == "OpenAI":
    client = OpenAI(
        base_url=f'{os.environ["AZURE_INFERENCE_ENDPOINT"]}',
        # Unfortunately, we can't refresh the token, so we must construct this client before *every* request to be safe
        api_key=token_provider(),
        # This seems to be required, as the chunks won't stream without it
        default_query={"api-version": os.environ["AZURE_INFERENCE_API_VERSION"]},
    )
elif client_selection == "AzureOpenAI":
    client = AzureOpenAI(
        api_version=os.environ["AZURE_INFERENCE_API_VERSION"],
        base_url=os.environ["AZURE_INFERENCE_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )

result = client.chat.completions.create(
    # This *must* be None, even though it technically is meant to be a str,
    # because thats the only way to get the AzureOpenAI class to skip the addition of 'deployments/model' to the URL:
    model=None,
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "What is the capital of the United States?",
        },
    ],
    max_tokens=2048,
    stream=True,
)

for update in result:
    if update.choices:
        print(update.choices[0].delta.content, end="")
