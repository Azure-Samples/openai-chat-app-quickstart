import asyncio
import os

from auth_common import get_application
from azure.identity.aio import AzureDeveloperCliCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.public_client_application import PublicClientApplication
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication


async def main():
    tenantId = os.getenv("AZURE_AUTH_TENANT_ID", None)
    credential = AzureDeveloperCliCredential(tenant_id=tenantId)

    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    uri = os.getenv("SERVICE_ACA_URI", "no-uri")
    if uri == "no-uri":
        print("No URI set, not updating authentication...")
        exit(0)
    client_app_id = os.getenv("AZURE_CLIENT_APP_ID", None)
    if client_app_id:
        client_object_id = await get_application(graph_client, client_app_id)
        if client_object_id:
            print("Updating client application redirect URIs...")
            # Redirect URIs need to be relative to the deployed application
            app = Application(
                public_client=PublicClientApplication(redirect_uris=[]),
                spa=SpaApplication(
                    redirect_uris=[
                        "http://localhost:50505/redirect",
                        f"{uri}/redirect",
                    ]
                ),
                web=WebApplication(
                    redirect_uris=[
                        "http://localhost:50505/.auth/login/aad/callback",
                        f"{uri}/.auth/login/aad/callback",
                    ]
                ),
            )
            await graph_client.applications.by_application_id(client_object_id).patch(app)
            print(f"Application update for client app id {client_app_id} complete.")


if __name__ == "__main__":
    asyncio.run(main())
