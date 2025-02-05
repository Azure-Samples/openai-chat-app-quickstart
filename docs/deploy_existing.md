
# Deploying with existing Azure resources

If you already have existing Azure resources, or if you want to specify the exact name of new Azure Resource, you can do so by setting `azd` environment values.
You should set these values before running `azd up`. Once you've set them, return to the [deployment steps](../README.md#deployment).

* [Resource group](#resource-group)

## Resource group

1. Run `azd env set AZURE_RESOURCE_GROUP {Name of existing resource group}`
1. Run `azd env set AZURE_LOCATION {Location of existing resource group}`
