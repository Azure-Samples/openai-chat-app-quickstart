import os
import subprocess
from typing import Any, Dict, Optional, Tuple

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential

TIMEOUT = 60


async def get_auth_headers(credential: AsyncTokenCredential):
    token_result = await credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token_result.token}"}


async def get_application(auth_headers: Dict[str, str], app_id: str) -> Optional[str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(f"https://graph.microsoft.com/v1.0/applications(appId='{app_id}')") as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json["id"]

    return None


async def update_application(auth_headers: Dict[str, str], object_id: str, app_payload: object):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.patch(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}", json=app_payload
        ) as response:
            if not response.ok:
                response_json = await response.json()
                raise Exception(response_json)

    return True

async def create_application(auth_headers: Dict[str, str], app_payload: object) -> Tuple[str, str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post("https://graph.microsoft.com/v1.0/applications", json=app_payload) as response:
            response_json = await response.json()
            object_id = response_json["id"]
            client_id = response_json["appId"]

    return object_id, client_id


async def add_client_secret(auth_headers: Dict[str, str], object_id: str):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}/addPassword",
            json={"passwordCredential": {"displayName": "secret"}},
        ) as response:
            response_json = await response.json()
            if response.status == 200:
                return response_json["secretText"]

            raise Exception(response_json)


async def create_or_update_application_with_secret(
    auth_headers: Dict[str, str], app_id_env_var: str, app_secret_env_var: str, app_payload: Dict[str, Any]
) -> Tuple[str, str, bool]:
    app_id = os.getenv(app_id_env_var, "no-id")
    created_app = False
    object_id = None
    if app_id != "no-id":
        print(f"Checking if application {app_id} exists")
        object_id = await get_application(auth_headers, app_id)

    if object_id:
        print("Application already exists, not creating new one")
        await update_application(auth_headers, object_id, app_payload)
    else:
        print("Creating application registration")
        object_id, app_id = await create_application(auth_headers, app_payload)
        update_azd_env(app_id_env_var, app_id)
        created_app = True

    if object_id and os.getenv(app_secret_env_var, "no-secret") == "no-secret":
        print(f"Adding client secret to {app_id}")
        client_secret = await add_client_secret(auth_headers, object_id)
        update_azd_env(app_secret_env_var, client_secret)

    return (object_id, app_id, created_app)


def update_azd_env(name, val):
    subprocess.run(f"azd env set {name} {val}", shell=True)



def test_authentication_enabled():
    use_authentication = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    require_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    if require_access_control and not use_authentication:
        print("AZURE_ENFORCE_ACCESS_CONTROL is true, but AZURE_USE_AUTHENTICATION is false. Stopping...")
        return False

    if not use_authentication:
        return False

    return True



async def setup_server_know_applications(auth_headers: Dict[str, str], server_object_id: str, client_app_id: str):

    await update_application(
        auth_headers,
        object_id=server_object_id,
        app_payload=create_server_app_known_client_application_payload(client_app_id),
    )

def create_server_app_known_client_application_payload(client_app_id: str):
    return {
        "api": {
            "knownClientApplications": [client_app_id],
        }
    }