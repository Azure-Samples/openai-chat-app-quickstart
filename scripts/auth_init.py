import asyncio
import datetime
import os
import random

import aiohttp
from auth_common import (
    TIMEOUT,
    add_application_owner,
    create_or_update_application_with_secret,
    create_permission_grant,
    get_auth_headers,
    get_current_user,
    get_microsoft_graph_service_principal,
    get_permission_grant,
    get_tenant_details,
    test_authentication_enabled,
    update_azd_env,
)
from kiota_abstractions.base_request_configuration import RequestConfiguration

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential, ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.application import Application
from msgraph.generated.models.implicit_grant_settings import ImplicitGrantSettings
from msgraph.generated.models.required_resource_access import RequiredResourceAccess
from msgraph.generated.models.resource_access import ResourceAccess
from msgraph.generated.models.spa_application import SpaApplication
from msgraph.generated.models.web_application import WebApplication
from msgraph_beta.generated.models.external_users_self_service_sign_up_events_flow import ExternalUsersSelfServiceSignUpEventsFlow
from msgraph_beta.generated.models.on_user_create_start_handler import OnUserCreateStartHandler
from msgraph_beta.generated.models.on_interactive_auth_flow_start_handler import OnInteractiveAuthFlowStartHandler
from msgraph_beta.generated.models.on_authentication_method_load_start_handler import OnAuthenticationMethodLoadStartHandler
from msgraph_beta.generated.models.on_attribute_collection_handler import OnAttributeCollectionHandler
from msgraph_beta.generated.identity.authentication_events_flows.authentication_events_flows_request_builder import AuthenticationEventsFlowsRequestBuilder

def random_app_identifier():
    rand = random.Random()
    rand.seed(datetime.datetime.now().timestamp())
    return rand.randint(1000, 100000)


def client_app(identifier: int) -> Application:
    return Application(
        display_name=f"ChatGPT Sample Client App {identifier}",
        sign_in_audience="AzureADMyOrg",
        web=WebApplication(
            redirect_uris=["http://localhost:50505/.auth/login/aad/callback"],
            implicit_grant_settings=ImplicitGrantSettings(enable_id_token_issuance=True),
        ),
        spa=SpaApplication(redirect_uris=["http://localhost:50505/redirect"]),
        required_resource_access=[
            RequiredResourceAccess(
                resource_app_id="00000003-0000-0000-c000-000000000000",
                resource_access=[
                    ResourceAccess(id="e1fe6dd8-ba31-4d61-89e7-88639da4683d", type="Scope"),  # Graph User.Read
                    ResourceAccess(id="7427e0e9-2fba-42fe-b0c0-848c9e6a8182", type="Scope"),  # offline_access
                    ResourceAccess(id="37f7f235-527c-4136-accd-4a02d197296e", type="Scope"),  # openid
                    ResourceAccess(id="14dad69e-099b-42c9-810b-d002981feec1", type="Scope"),  # profile
                ],
            )
        ],
    )


def permission_scopes() -> str:
    return " ".join(["User.Read", "offline_access", "openid", "profile"])


# Not supported? https://learn.microsoft.com/en-us/graph/api/resources/externalusersselfservicesignupeventsflow?view=graph-rest-beta
def create_client_userflow_payload(identifier: int):
    return ExternalUsersSelfServiceSignUpEventsFlow(
        priority=500,
        description=f"ChatGPT Sample User Flow {identifier}",
        display_name=f"ChatGPT Sample User Flow {identifier}",
        on_user_create_start=OnUserCreateStartHandler(
            user_type_to_create="member",
            access_packages=[],
        ),
        on_interactive_auth_flow_start=OnInteractiveAuthFlowStartHandler(
            is_sign_up_allowed=True,
        ),
        on_authentication_method_load_start=OnAuthenticationMethodLoadStartHandler(
            identity_providers=[
                {
                    "displayName": "Email One Time Passcode",
                    "state": "null",
                    "identityProviderType": "EmailOTP",
                    "id": "EmailOtpSignup-OAUTH",
                    "@odata.type": "#microsoft.graph.builtInIdentityProvider",
                }
            ]
        ),
        on_attribute_collection=OnAttributeCollectionHandler(
            attributes=[
                {
                    "displayName": "Email Address",
                    "dataType": "string",
                    "description": "Email address of the user",
                    "id": "email",
                    "userFlowAttributeType": "builtIn",
                },
                {
                    "description": "Display Name of the User.",
                    "displayName": "Display Name",
                    "id": "displayName",
                    "dataType": "string",
                    "userFlowAttributeType": "builtIn",
                },
            ],
            access_packages=[],
            attribute_collection_page={
                "views": [
                    {
                        "inputs": [
                            {
                                "options": [],
                                "validationRegEx": "^[a-zA-Z0-9.!#$%&amp;&#8217;'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:.[a-zA-Z0-9-]+)*$",  # noqa: E501
                                "attribute": "email",
                                "required": "true",
                                "label": "Email Address",
                                "writeToDirectory": "true",
                                "inputType": "text",
                                "hidden": "true",
                                "editable": "false",
                            },
                            {
                                "options": [],
                                "validationRegEx": "^.*",
                                "attribute": "displayName",
                                "required": "true",
                                "label": "Display Name",
                                "writeToDirectory": "true",
                                "inputType": "text",
                                "hidden": "false",
                                "editable": "true",
                            },
                        ]
                    }
                ]
            }
        )
    )


# Beta: https://learn.microsoft.com/graph/api/resources/externalusersselfservicesignupeventsflow?view=graph-rest-beta
async def get_userflow(graph_client_beta: GraphServiceClient, identifier: str) -> (str | None):
    app_name = f"ChatGPT Sample User Flow {identifier}"

    query_params = AuthenticationEventsFlowsRequestBuilder.AuthenticationEventsFlowsRequestBuilderGetQueryParameters(
        filter=f"displayName eq '{app_name}'",
    )
    request_configuration = RequestConfiguration(
        query_parameters=query_params,
    )
    result = await graph_client_beta.identity.authentication_events_flows.get(request_configuration=request_configuration)
    if result.value:
        return result.value[0].id
    return None


# Not supported? https://learn.microsoft.com/en-us/graph/api/resources/externalusersselfservicesignupeventsflow?view=graph-rest-beta
async def create_userflow(auth_headers: dict[str, str], app_payload: object) -> str:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            "https://graph.microsoft.com/beta/identity/AuthenticationEventsFlows", json=app_payload
        ) as response:
            response_json = await response.json()
            if response.status == 201:
                return response_json["id"]

            raise Exception(response_json)


# Not supported? https://learn.microsoft.com/en-us/graph/api/resources/externalusersselfservicesignupeventsflow?view=graph-rest-beta
async def get_apps_for_userflow(auth_headers: dict[str, str], userflow_id: str) -> list[str]:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.get(
            f"https://graph.microsoft.com/beta/identity/AuthenticationEventsFlows/{userflow_id}/conditions/applications/includeApplications"
        ) as response:
            if response.status == 200:
                response_json = await response.json()
                if response_json["value"]:
                    ids = [item["appId"] for item in response_json["value"]]
                    return ids
                return []
            raise Exception(response_json)


async def add_app_to_userflow(auth_headers: dict[str, str], userflow_id: str, app_id: str) -> bool:
    apps = await get_apps_for_userflow(auth_headers, userflow_id)
    if app_id in apps:
        print("User flow already has application, not adding new one")
        return True
    return await _add_app_to_userflow(auth_headers, userflow_id, app_id)


# Not supported? https://learn.microsoft.com/en-us/graph/api/resources/externalusersselfservicesignupeventsflow?view=graph-rest-beta
async def _add_app_to_userflow(auth_headers: dict[str, str], userflow_id: str, app_id: str) -> bool:
    async with aiohttp.ClientSession(headers=auth_headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
        async with session.post(
            f"https://graph.microsoft.com/beta/identity/AuthenticationEventsFlows/{userflow_id}/conditions/applications/includeApplications",
            json={"@odata.type": "#microsoft.graph.authenticationConditionApplication", "appId": app_id},
        ) as response:
            response_json = await response.json()
            if response.status == 201:
                return True

            raise Exception(response_json)


def get_credential(tenantId: str) -> AsyncTokenCredential:
    client_id = os.getenv("AZURE_AUTH_EXTID_APP_ID", None)
    if client_id is None:
        print("Using Azd CLI Credential")
        return AzureDeveloperCliCredential(tenant_id=tenantId)
    client_secret = os.getenv("AZURE_AUTH_EXTID_APP_SECRET", None)
    print(f"Using Client Secret Credential... {client_id}")
    return ClientSecretCredential(tenant_id=tenantId, client_id=client_id, client_secret=client_secret)


async def main():
    if not test_authentication_enabled():
        print("Not setting up authentication...")
        exit(0)

    print("Setting up authentication...")
    tenant_id = os.getenv("AZURE_AUTH_TENANT_ID", None)
    credential = get_credential(tenant_id)
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
    graph_client_beta = GraphServiceClient(credentials=credential, scopes=scopes)
    try:
        (tenant_type, _) = await get_tenant_details(AzureDeveloperCliCredential(tenant_id=tenant_id), tenant_id)
        if tenant_type == "CIAM":
            current_user = os.getenv("AZURE_AUTH_EXTID_APP_OWNER", None)
        else:
            current_user = await get_current_user(graph_client)

        app_identifier = os.getenv("AZURE_CLIENT_IDENTIFIER", random_app_identifier())
        update_azd_env("AZURE_CLIENT_IDENTIFIER", app_identifier)
        (app_obj_id, app_id, sp_id) = await create_or_update_application_with_secret(
            graph_client,
            app_id_env_var="AZURE_CLIENT_APP_ID",
            app_secret_env_var="AZURE_CLIENT_APP_SECRET",
            request_app=client_app(app_identifier),
        )

        if tenant_type == "CIAM":
            print("Granting Application consent...")
            graph_sp_id = await get_microsoft_graph_service_principal(graph_client_beta)
            grant_id = await get_permission_grant(graph_client, sp_id, graph_sp_id, permission_scopes())
            if grant_id:
                print("Permission grant already exists, not creating new one")
            else:
                print("Creating permission grant")
                await create_permission_grant(graph_client, sp_id, graph_sp_id, permission_scopes())

            if current_user is not None:
                print(f"Setting owner for {app_id}")
                await add_application_owner(graph_client, app_obj_id, current_user)

            userflow_id = await get_userflow(graph_client_beta, app_identifier)
            if userflow_id is None:
                print(f"Creating user flow for {app_id}")
                userflow_id = await create_userflow(graph_client_beta, create_client_userflow_payload(app_identifier))

            print(f"Adding user flow to application {app_id}")
            await add_app_to_userflow(graph_client_beta, userflow_id, app_id)
    finally:
        await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
