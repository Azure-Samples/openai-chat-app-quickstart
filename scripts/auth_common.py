import os
import subprocess
import time

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from kiota_abstractions.api_error import APIError
from msgraph import GraphServiceClient
from msgraph.generated.applications.item.add_password.add_password_post_request_body import (
    AddPasswordPostRequestBody,
)
from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.generated.models.o_auth2_permission_grant import OAuth2PermissionGrant
from msgraph.generated.service_principals.service_principals_request_builder import ServicePrincipalsRequestBuilder
from msgraph.generated.models.reference_create import ReferenceCreate


async def get_application(graph_client: GraphServiceClient, client_id: str) -> str | None:
    try:
        app = await graph_client.applications_with_app_id(client_id).get()
        return app.id
    except APIError:
        return None


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


# https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0&tabs=python
async def get_current_user(graph_client: GraphServiceClient) -> (str | None):
    result = await graph_client.me.get()
    return result.id


async def get_microsoft_graph_service_principal(graph_client: GraphServiceClient) -> str:
    query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        filter="appId eq '00000003-0000-0000-c000-000000000000'"
    )
    request_configuration = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
        query_parameters=query_params,
    )
    result = await graph_client.service_principals.get(request_configuration=request_configuration)
    return result.value[0].id


async def create_application(graph_client: GraphServiceClient, request_app: Application) -> tuple[str, str]:
    app = await graph_client.applications.post(request_app)
    object_id = app.id
    client_id = app.app_id
    return object_id, client_id


# https://learn.microsoft.com/en-us/graph/api/application-list-owners?view=graph-rest-1.0&tabs=python
async def get_application_owners(graph_client: GraphServiceClient, app_obj_id: str) -> list[str]:
    result = await graph_client.applications.by_application_id(app_obj_id).owners.get()
    return [item.id for item in result.value]


async def add_application_owner(graph_client: GraphServiceClient, app_obj_id: str, owner_id: str) -> bool:
    object_ids = await get_application_owners(graph_client, app_obj_id)
    if owner_id in object_ids:
        print("Application owner already exists, not creating new one")
        return False
    else:
        print("Adding application owner")
        await _add_application_owner(graph_client, app_obj_id, owner_id)


# https://learn.microsoft.com/en-us/graph/api/application-post-owners?view=graph-rest-1.0&tabs=python
async def _add_application_owner(graph_client: GraphServiceClient, app_obj_id: str, owner_id: str) -> bool:
    request_body = ReferenceCreate(
        odata_id=f"https://graph.microsoft.com/v1.0/directoryObjects/{owner_id}",
    )
    return await graph_client.applications.by_application_id(app_obj_id).owners.ref.post(request_body)


# https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list?view=graph-rest-1.0&tabs=http
async def get_service_principal(graph_client: GraphServiceClient, app_id: str) -> (str | None):
    query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        filter=f"appId eq '{app_id}'"
    )
    request_configuration = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
        query_parameters=query_params,
    )
    result = await graph_client.service_principals.get(request_configuration=request_configuration)
    if not result.value or len(result.value) == 0:
        return None
    return result.value[0].id


# https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-serviceprincipals?view=graph-rest-1.0&tabs=python
async def add_service_principal(graph_client: GraphServiceClient, app_id: str):
    request_principal = ServicePrincipal(app_id=app_id, tags=["WindowsAzureActiveDirectoryIntegratedApp"])
    sp = await graph_client.service_principals.post(request_principal)
    return sp.id


async def add_client_secret(graph_client: GraphServiceClient, object_id: str) -> str:
    request_password = AddPasswordPostRequestBody(
        password_credential=PasswordCredential(display_name="WebAppSecret"),
    )
    result = await graph_client.applications.by_application_id(object_id).add_password.post(request_password)
    return result.secret_text


# no docs found!!
async def get_permission_grant(
    graph_client: GraphServiceClient, obj_id: str, resource_id: str, scope: str
) -> (str | None):
    from msgraph.generated.oauth2_permission_grants.oauth2_permission_grants_request_builder import (
        OAuth2PermissionGrantsRequestBuilder,
    )

    query_params = OAuth2PermissionGrantsRequestBuilder.OAuth2PermissionGrantsRequestBuilderGetQueryParameters(
        filter=f"clientId eq '{obj_id}' and resourceId eq '{resource_id}'"
    )
    request_configuration = (
        OAuth2PermissionGrantsRequestBuilder.OAuth2PermissionGrantsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params,
        )
    )
    result = await graph_client.oauth2_permission_grants.get(request_configuration=request_configuration)
    for permission in result:
        if permission.scope == scope:
            return permission.id
    return None


# https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-post?view=graph-rest-1.0&tabs=python
async def create_permission_grant(graph_client: GraphServiceClient, obj_id: str, resource_id: str, scope: str) -> str:
    request_body = OAuth2PermissionGrant(
        client_id=obj_id,
        consent_type="AllPrincipals",
        resource_id=resource_id,
        scope=scope,
    )

    result = await graph_client.oauth2_permission_grants.post(request_body)
    return result.id


async def create_or_update_application_with_secret(
    graph_client: GraphServiceClient, app_id_env_var: str, app_secret_env_var: str, request_app: Application
) -> tuple[str, str, str]:
    app_id = os.getenv(app_id_env_var, "no-id")
    created_app = False
    object_id = None
    if app_id != "no-id":
        print(f"Checking if application {app_id} exists")
        object_id = await get_application(graph_client, app_id)

    if object_id:
        print("Application already exists, not creating new one")
        await graph_client.applications.by_application_id(object_id).patch(request_app)
    else:
        print("Creating application registration")
        object_id, app_id = await create_application(graph_client, request_app)
        update_azd_env(app_id_env_var, app_id)
        created_app = True

        # Wait for application to created and in cache before creating SP
        wait_for_cache_sync()

    if created_app or (object_id and os.getenv(app_secret_env_var, "no-secret") == "no-secret"):
        print(f"Adding client secret to {app_id}")
        client_secret = await add_client_secret(graph_client, object_id)
        update_azd_env(app_secret_env_var, client_secret)

    sp_id = await get_service_principal(graph_client, app_id)
    if not sp_id:
        print(f"Adding service principal to {app_id}")
        sp_id = await add_service_principal(graph_client, app_id)

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
