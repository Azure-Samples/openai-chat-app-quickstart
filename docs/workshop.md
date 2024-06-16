# Workshop steps

This guide is specifically for workshop attendees that are using the Azure OpenAI proxy service.

## Opening the project

Open the project in GitHub Codespaces by clicking the button below:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/openai-chat-app-quickstart)

## Local server

1. Copy `.env.sample` to `.env` and fill in the values for `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_CHATGPT_DEPLOYMENT`:

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

