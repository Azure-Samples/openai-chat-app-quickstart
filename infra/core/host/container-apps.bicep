metadata description = 'Creates an Azure Container Registry and an Azure Container Apps environment.'
param name string
param location string = resourceGroup().location
param tags object = {}

param containerAppsEnvironmentName string
param containerRegistryName string
param containerRegistryResourceGroupName string = ''
param containerRegistryAdminUserEnabled bool = false
param logAnalyticsWorkspaceName string
param applicationInsightsName string = ''
param daprEnabled bool = false

module containerAppsEnvironment 'container-apps-environment.bicep' = {
  name: '${name}-container-apps-environment'
  params: {
    name: containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    daprEnabled: daprEnabled
  }
}

module containerRegistry 'container-registry.bicep' = if (empty(containerRegistryResourceGroupName)) {
  name: '${name}-container-registry'
  params: {
    name: containerRegistryName
    location: location
    adminUserEnabled: containerRegistryAdminUserEnabled
    tags: tags
  }
}

module containerRegistryExternalRG 'container-registry.bicep' = if (!empty(containerRegistryResourceGroupName)) {
  name: '${name}-container-registry-external'
  scope: resourceGroup(containerRegistryResourceGroupName)
  params: {
    name: containerRegistryName
    location: location
    adminUserEnabled: containerRegistryAdminUserEnabled
    tags: tags
  }
}

output defaultDomain string = containerAppsEnvironment.outputs.defaultDomain
output environmentName string = containerAppsEnvironment.outputs.name
output environmentId string = containerAppsEnvironment.outputs.id

output registryLoginServer string = empty(containerRegistryResourceGroupName) ? containerRegistry.outputs.loginServer : containerRegistryExternalRG.outputs.loginServer
output registryName string = empty(containerRegistryResourceGroupName) ? containerRegistry.outputs.name : containerRegistryExternalRG.outputs.name
