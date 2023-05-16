import os

import openai
import dotenv

dotenv.load_dotenv()

openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT") 
openai.api_version = "2023-03-15-preview"

if os.getenv("AZURE_OPENAI_KEY"):
    openai.api_type = "azure"
    openai.api_key = os.getenv("AZURE_OPENAI_KEY")
else:
    from azure.identity import DefaultAzureCredential
    default_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True,
                                                exclude_environment_credential=True)
    token = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    openai.api_type = "azure_ad"
    openai.api_key = token.token

response = openai.ChatCompletion.create(
    engine=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "chatgpt"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."},
        {"role": "user", "content": "Do other Azure Cognitive Services support this too?"}
    ],
    stream=True
)

for event in response:
    if event['choices'][0]['delta'].get('content'):
        response_message =event['choices'][0]['delta']['content']
        print(response_message, end='')