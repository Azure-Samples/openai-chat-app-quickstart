# Workshop steps

This guide is specifically for workshop attendees that are using the Azure OpenAI proxy service.

## Opening the project

Open the project in GitHub Codespaces by clicking the button below:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/openai-chat-app-quickstart)

## Local server

1. Copy `.env.sample` to `.env` and fill in the values for `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_CHATGPT_DEPLOYMENT` to use the Azure OpenAI proxy service:

    ```bash
    AZURE_OPENAI_ENDPOINT=https://YOUR-ENDPOINT-HERE/api/v1
    AZURE_OPENAI_KEY=YOUR-KEY-HERE
    AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-35-turbo
    ```

2. Run the server:

    ```bash
    python -m quart --app src.quartapp run --port 50505 --reload
    ```

    This will start the app on port 50505, and you can access it at `http://localhost:50505`.

## Deploying to Azure

1. Create a new azd environment:

    ```shell
    azd env new
    ```

    This will create a folder in `.azure` to store the configuration for the deployment.

2. Set the following azd environment variables to use the Azure OpenAI proxy service. Replace `YOUR-ENDPOINT-HERE` and `YOUR-KEY-HERE`:

    ```shell
    azd env set CREATE_AZURE_OPENAI false
    azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT gpt-35-turbo
    azd env set AZURE_OPENAI_ENDPOINT https://YOUR-ENDPOINT-HERE/api/v1
    azd env set AZURE_OPENAI_KEY YOUR-KEY-HERE
    ```

3. Deploy the app:

    ```shell
    azd up
    ```

    This will create a new resource group with an Azure Container App,
    and deploy the app code to the Azure Container App.
    Once the deployment is complete, you can access the app at the URL provided.
