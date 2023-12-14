import os
import subprocess
import time
from typing import Any

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential

TIMEOUT = 60


async def get_auth_headers(credential: AsyncTokenCredential):
    token_result = await credential.get_token("https://graph.microsoft.com/.default")
    return {"Authorization": f"Bearer {token_result.token}"}


async def get_azure_auth_headers(credential: AsyncTokenCredential) -> dict[str, str]:
    token_result = await credential.get_token("https://management.core.windows.net/.default")
    return {"Authorization": f"Bearer {token_result.token}"}


async def get_tenant_details(credential: AsyncTokenCredential, tenant_id: str) -> tuple[str, str]:
    if tenant_id is None:
        return (None, None)
    auth_headers = await get_azure_auth_headers(credential)
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get("https://management.azure.com/tenants?api-version=2022-12-01") as response:
            response_json = await response.json()
            if response.status == 200:
                for tenant in response_json["value"]:
                    if tenant["tenantId"] == tenant_id:
                        if "tenantType" not in tenant:
                            raise Exception(f"tenantType not found in tenant details: {tenant}")
                        return tenant["tenantType"], tenant["defaultDomain"]
            raise Exception(response_json)


async def get_current_user(auth_headers: dict[str, str]) -> (str | None):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get("https://graph.microsoft.com/v1.0/me") as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json["id"]

    return None


async def get_microsoft_graph_service_principal(auth_headers: dict[str, str]) -> str:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(
            "https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '00000003-0000-0000-c000-000000000000'"
        ) as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json["value"]:
                    return response_json["value"][0]["id"]
            raise Exception(response_json)


async def get_application(auth_headers: dict[str, str], app_id: str) -> (str | None):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(f"https://graph.microsoft.com/v1.0/applications(appId='{app_id}')") as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json["id"]

    return None


async def update_application(auth_headers: dict[str, str], object_id: str, app_payload: object):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.patch(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}", json=app_payload
        ) as response:
            if not response.ok:
                response_json = await response.json()
                raise Exception(response_json)

    return True


async def create_application(auth_headers: dict[str, str], app_payload: object) -> tuple[str, str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post("https://graph.microsoft.com/v1.0/applications", json=app_payload) as response:
            response_json = await response.json()
            if response.status == 201:
                object_id = response_json["id"]
                client_id = response_json["appId"]
                return object_id, client_id
            raise Exception(response_json)


async def get_application_owners(auth_headers: dict[str, str], app_obj_id: str) -> list[str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(f"https://graph.microsoft.com/v1.0/applications/{app_obj_id}/owners") as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json["value"]:
                    ids = [item["id"] for item in response_json["value"]]
                    return ids

                return []


async def add_application_owner(auth_headers: dict[str, str], app_obj_id: str, owner_id: str) -> bool:
    object_ids = await get_application_owners(auth_headers, app_obj_id)
    if owner_id in object_ids:
        print("Application owner already exists, not creating new one")
        return False
    else:
        print("Adding application owner")
        await _add_application_owner(auth_headers, app_obj_id, owner_id)


async def _add_application_owner(auth_headers: dict[str, str], app_obj_id: str, owner_id: str) -> bool:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            f"https://graph.microsoft.com/v1.0/applications/{app_obj_id}/owners/$ref",
            json={"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{owner_id}"},
        ) as response:
            if response.status == 204:
                return True
            response_json = await response.json()
            raise Exception(response_json)


async def get_service_principal(auth_headers: dict[str, str], app_id: str) -> (str | None):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(
            f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{app_id}'"
        ) as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json["value"]:
                    return response_json["value"][0]["id"]

    return None


async def add_service_principal(auth_headers: dict[str, str], app_id: str):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            "https://graph.microsoft.com/v1.0/servicePrincipals",
            json={"appId": app_id, "tags": ["WindowsAzureActiveDirectoryIntegratedApp"]},
        ) as response:
            response_json = await response.json()
            if response.status == 201:
                return response_json["id"]

            raise Exception(response_json)


async def add_client_secret(auth_headers: dict[str, str], object_id: str):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            f"https://graph.microsoft.com/v1.0/applications/{object_id}/addPassword",
            json={"passwordCredential": {"displayName": "secret"}},
        ) as response:
            response_json = await response.json()
            if response.status == 200:
                return response_json["secretText"]

            raise Exception(response_json)


async def get_permission_grant(auth_headers: dict[str, str], obj_id: str, resource_id: str, scope: str) -> (str | None):
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(
            f"https://graph.microsoft.com/v1.0/oauth2PermissionGrants?$filter=clientId eq '{obj_id}' \
                and resourceId eq '{resource_id}'"
        ) as response:
            response_json = await response.json()
            if response.status == 200:
                for permission in response_json["value"]:
                    if permission["scope"] == scope:
                        return permission["id"]
    return None


async def create_permission_grant(auth_headers: dict[str, str], obj_id: str, resource_id: str, scope: str) -> str:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            "https://graph.microsoft.com/v1.0/oauth2PermissionGrants",
            json={"clientId": obj_id, "resourceId": resource_id, "scope": scope, "consentType": "AllPrincipals"},
        ) as response:
            response_json = await response.json()
            if response.status == 201:
                return response_json["id"]
            raise Exception(response_json)


async def create_or_update_application_with_secret(
    auth_headers: dict[str, str], app_id_env_var: str, app_secret_env_var: str, app_payload: dict[str, Any]
) -> tuple[str, str, str]:
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

        # Wait for application to created and in cache before creating SP
        wait_for_cache_sync()

    if created_app or (object_id and os.getenv(app_secret_env_var, "no-secret") == "no-secret"):
        print(f"Adding client secret to {app_id}")
        client_secret = await add_client_secret(auth_headers, object_id)
        update_azd_env(app_secret_env_var, client_secret)

    sp_id = await get_service_principal(auth_headers, app_id)
    if not sp_id:
        print(f"Adding service principal to {app_id}")
        sp_id = await add_service_principal(auth_headers, app_id)

    return (object_id, app_id, sp_id)


def wait_for_cache_sync(wait=30):
    print(f"Waiting {wait} seconds for cache to sync")
    time.sleep(wait)


def update_azd_env(name, val):
    # val could start with '-' which would cause azd to think it's a flag
    # so use '--' to signal end of parameter parsing
    subprocess.run(f"azd env set {name} -- {val}", shell=True)


def test_authentication_enabled():
    use_authentication = os.getenv("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    require_access_control = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL", "").lower() == "true"
    if require_access_control and not use_authentication:
        print("AZURE_ENFORCE_ACCESS_CONTROL is true, but AZURE_USE_AUTHENTICATION is false. Stopping...")
        return False

    if not use_authentication:
        return False

    return True


async def setup_server_know_applications(auth_headers: dict[str, str], server_object_id: str, client_app_id: str):
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
