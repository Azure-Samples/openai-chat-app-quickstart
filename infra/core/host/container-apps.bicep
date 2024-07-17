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
  // Container Envieronment does depend directly on the registry, but we want to wait for the registry to be ready 
  // The time for creating the container environment is used to wait for the container registry to be ready (DNS propagation)
  dependsOn: [containerRegistry]
  params: {
    name: containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    daprEnabled: daprEnabled
  }
}

module containerRegistry 'container-registry.bicep' = {
  name: '${name}-container-registry'
  scope: !empty(containerRegistryResourceGroupName) ? resourceGroup(containerRegistryResourceGroupName) : resourceGroup()
  params: {
    name: containerRegistryName
    location: location
    adminUserEnabled: containerRegistryAdminUserEnabled
    tags: tags
  }
}

// Wait for the registry to be ready before continuing
// DNS propagation can take up to 60 sec
// see: https://learn.microsoft.com/azure/dns/dns-faq#how-long-does-it-take-for-dns-changes-to-take-effect-
resource waitForRegistry 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'wait-for-registry-app-container-registry'
  location: location
  kind: 'AzureCLI'
  dependsOn: [
    containerAppsEnvironment
  ]
  properties: {
    azCliVersion: '2.61.0'
    retentionInterval: 'PT1H' // Retain the script resource for 1 hour after it ends running
    timeout: 'PT5M' // Five minutes
    cleanupPreference: 'OnSuccess'
    scriptContent: '''
      # setting up deployment script takes about 1 minute, which is the max time we need to wait for DNS propagation
      echo "Waited at least 60 seconds for DNS propagation. If container registry is not found, an error will be returned."
    '''
  }
}

output defaultDomain string = containerAppsEnvironment.outputs.defaultDomain
output environmentName string = containerAppsEnvironment.outputs.name
output environmentId string = containerAppsEnvironment.outputs.id

output registryLoginServer string = containerRegistry.outputs.loginServer
output registryName string = containerRegistry.outputs.name
