
# Deploying with existing Azure resources

If you already have existing Azure resources, or if you want to specify the exact name of new Azure Resource, you can do so by setting `azd` environment values.
You should set these values before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deployment).

* [Resource group](#resource-group)
* [Azure OpenAI resource](#azure-openai-resource)
* [OpenAI.com API key](#openaicom-openai-resource)

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

## OpenAI.com OpenAI resource

If you already have an OpenAI.com API key and would like to re-use it, run `azd env set` to specify the values for the existing OpenAI.com API key.

```shell
azd env set OPENAICOM_API_KEY {your OpenAI.com API key}
```

The key will be stored in Key Vault when you run `azd up`, and fetched from Key Vault inside the application code.
You must run `azd up` to store the key in Key Vault before running the application.