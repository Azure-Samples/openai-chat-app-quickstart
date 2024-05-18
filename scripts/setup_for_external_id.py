import asyncio
import os

from auth_common import (
    add_application_owner,
    create_or_update_application_with_secret,
    get_current_user,
    get_microsoft_graph_service_principal,
    get_tenant_details,
    update_azd_env,
)
from azure.identity.aio import AzureDeveloperCliCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.required_resource_access import RequiredResourceAccess
from msgraph.generated.models.resource_access import ResourceAccess
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from msgraph.generated.models.app_role_assignment import AppRoleAssignment


def client_app():
    return Application(
        display_name="azd Application Creation helper",
        sign_in_audience="AzureADMyOrg",
        required_resource_access=[
            RequiredResourceAccess(
                resource_app_id="00000003-0000-0000-c000-000000000000",
                resource_access=[
                    # Graph Application.ReadWrite.All
                    ResourceAccess(id="1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9", type="Role"),
                    # Graph EventListener.ReadWrite.All
                    ResourceAccess(id="0edf5e9e-4ce8-468a-8432-d08631d18c43", type="Role"),
                    # Graph DelegatedPermissionGrant.ReadWrite.All
                    ResourceAccess(id="8e8e4742-1d95-4f68-9d56-6ee75648c72a", type="Role"),
                    # Graph Organization.ReadWrite.All
                    ResourceAccess(id="292d869f-3427-49a8-9dab-8c70152b74e9", type="Role"),
                    # Graph User.Read.All
                    ResourceAccess(id="df021288-bdef-4463-88db-98f22de89214", type="Role"),
                ],
            )
        ]
    )

def app_roles() -> str:
    app_roles = [
        # Graph Application.ReadWrite.All
        "1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9",
        # Graph EventListener.ReadWrite.All
        "0edf5e9e-4ce8-468a-8432-d08631d18c43",
        # Graph DelegatedPermissionGrant.ReadWrite.All
        "8e8e4742-1d95-4f68-9d56-6ee75648c72a",
        # Graph Organization.ReadWrite.All
        "292d869f-3427-49a8-9dab-8c70152b74e9",
        # Graph User.Read.All
        "df021288-bdef-4463-88db-98f22de89214",
    ]
    return app_roles


async def grant_approle(graph_client:GraphServiceClient, sp_obj_id: str, resource_id: str, app_role: str):
    request_body = AppRoleAssignment(
        principal_id = sp_obj_id,
        resource_id = resource_id,
        app_role_id = app_role
    )
    try:
        await graph_client.service_principals.by_service_principal_id(sp_obj_id).app_role_assignments.post(request_body)
    except ODataError as e:
        if e.error.message != "Permission being assigned already exists on the object":
            raise e


#
# for an external ID tenant, the login domain is a subdomain of ciamlogin.com, not onmicrosoft.com
#
def login_domain_for(default_domain: str) -> str:
    prefix = default_domain.split(".")[0]
    return f"{prefix}.ciamlogin.com"


async def main():
    tenant_id = os.getenv("AZURE_AUTH_TENANT_ID", None)
    if not tenant_id:
        print("Please set AZURE_AUTH_TENANT_ID environment variable")
        exit(1)

    print(f"Setting up External ID Service Principal in tenant {tenant_id}")
    credential = AzureDeveloperCliCredential(tenant_id=tenant_id)
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
    
    (tenant_type, default_domain) = await get_tenant_details(credential, tenant_id)
    if tenant_type != "CIAM":
        print("You don't need to run this script for non-ExternalId tenant...")
        exit(0)
    # Convert default domain to login domain
    login_domain = login_domain_for(default_domain)
    print(f"Using login domain {login_domain} for tenant {tenant_id}")

    # Update azd env
    update_azd_env("AZURE_AUTH_TENANT_ID", tenant_id)
    update_azd_env("AZURE_AUTH_LOGIN_ENDPOINT", login_domain)

    print("Checking if we need to create application registration...")
    (obj_id, app_id, sp_id) = await create_or_update_application_with_secret(
        graph_client,
        app_id_env_var="AZURE_AUTH_EXTID_APP_ID",
        app_secret_env_var="AZURE_AUTH_EXTID_APP_SECRET",
        request_app=client_app(),
    )

    print("Granting Application consent...")
    graph_sp_id = await get_microsoft_graph_service_principal(graph_client)
    for app_role in app_roles():
        print(f"Granting app role {app_role}...")
        await grant_approle(graph_client, sp_id, graph_sp_id, app_role)

    print(f"Adding application owner for {app_id}")
    owner_id = await get_current_user(graph_client)
    await add_application_owner(graph_client, obj_id, owner_id)
    update_azd_env("AZURE_AUTH_EXTID_APP_OWNER", owner_id)
    print("External ID setup is complete! Now follow the steps for deployment.")


if __name__ == "__main__":
    asyncio.run(main())
