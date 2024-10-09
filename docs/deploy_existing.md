
# Deploying with existing Azure resources

If you already have existing Azure resources, or if you want to specify the exact name of new Azure Resource, you can do so by setting `azd` environment values.
You should set these values before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deployment).

* [Resource group](#resource-group)
* [Azure OpenAI resource](#azure-openai-resource)

## Resource group

1. Run `azd env set AZURE_RESOURCE_GROUP {Name of existing resource group}`
1. Run `azd env set AZURE_LOCATION {Location of existing resource group}`

## Azure OpenAI resource

If you already have an OpenAI resource and would like to re-use it, run `azd env set` to specify the values for the existing OpenAI resource.

```shell
azd env set AZURE_OPENAI_RESOURCE {name of OpenAI resource}
azd env set AZURE_OPENAI_RESOURCE_GROUP {name of resource group that it's inside}
azd env set AZURE_OPENAI_RESOURCE_GROUP_LOCATION {location for that group}
azd env set AZURE_OPENAI_SKU_NAME {name of the SKU, defaults to "S0"}
```

If you don't want to deploy a new Azure OpenAI resource and just want to use an existing one via its endpoint, you can set the following values:

```shell
azd env set CREATE_AZURE_OPENAI false
azd env set AZURE_OPENAI_CHAT_DEPLOYMENT gpt-35-turbo
azd env set AZURE_OPENAI_ENDPOINT https://YOUR-ENDPOINT-HERE
```

> [!NOTE]
> Your existing endpoint needs to have the appropriate Role-based access control (RBAC) role assigned. For guidance, refer to [Role-based access control for Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/how-to/role-based-access-control).