# Local development server with Docker

In addition to the `Dockerfile` that's used in production, this repo includes a `docker-compose.yaml` for
local development which creates a volume for the app code. That allows you to make changes to the code
and see them instantly.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/). If you opened this inside Github Codespaces or a Dev Container in VS Code, installation is not needed. ⚠️ If you're on an Apple M1/M2, you won't be able to run `docker` commands inside a Dev Container; either use Codespaces or do not open the Dev Container.

2. Make sure that the `.env` file exists. The `azd up` deployment step should have created it.

3. Store a key for the OpenAI resource in the `.env` file. You can get the key from the Azure Portal, or from the output of `./infra/getkey.sh`. The key should be stored in the `.env` file as `AZURE_OPENAI_KEY`. This is necessary because Docker containers don't have access to your user Azure credentials.

4. Start the services with this command:

    ```shell
    docker-compose up --build
    ```

5. Click 'http://0.0.0.0:50505' in the terminal, which should open a new tab in the browser. You may need to navigate to 'http://localhost:50505' if that URL doesn't work.
