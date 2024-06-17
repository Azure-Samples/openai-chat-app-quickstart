
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

If you don't want to deploy a new Azure OpenAI resource and just want to use an existing one via its endpoint and key, you can set the following values:

```shell
azd env set CREATE_AZURE_OPENAI false
azd env set AZURE_OPENAI_CHATGPT_DEPLOYMENT gpt-35-turbo
azd env set AZURE_OPENAI_ENDPOINT https://YOUR-ENDPOINT-HERE
azd env set AZURE_OPENAI_KEY YOUR-KEY-HERE
```

⚠️ We don't recommend using key-based access in production, but it may be useful for testing or development purposes.