import asyncio
import os
from typing import Tuple

import aiohttp
from azure.identity.aio import AzureDeveloperCliCredential

from auth_common import (
    TIMEOUT,
    get_auth_headers,
    test_authentication_enabled,
    create_or_update_application_with_secret,
)



def create_client_app_payload():
    return {
        "displayName": "Demo Client App",
        "signInAudience": "AzureADMyOrg",
        "web": {
            "redirectUris": ["http://localhost:50505/.auth/login/aad/callback"],
            "implicitGrantSettings": {"enableIdTokenIssuance": True},
        },
        "spa": {"redirectUris": ["http://localhost:50505/redirect"]},
        "requiredResourceAccess": [
            # Graph User.Read
            {
                "resourceAppId": "00000003-0000-0000-c000-000000000000",
                "resourceAccess": [{"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"}],
            },
        ],
    }

async def main():
    if not test_authentication_enabled():
        print("Not setting up authentication...")
        exit(0)

    print("Setting up authentication...")
    tenantId = os.getenv("TENANT_ID", None)
    credential = AzureDeveloperCliCredential(tenant_id=tenantId)
    auth_headers = await get_auth_headers(credential)

    print("Creating application registration...")
    await create_or_update_application_with_secret(
        auth_headers,
        app_id_env_var="AZURE_CLIENT_APP_ID",
        app_secret_env_var="AZURE_CLIENT_APP_SECRET",
        app_payload=create_client_app_payload(),
    )

if __name__ == "__main__":
    asyncio.run(main())
