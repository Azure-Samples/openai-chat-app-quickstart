targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

param acaExists bool = false

// Parameters for the Azure AI resource:
param aiServicesResourceGroupName string = ''
@minLength(1)
@description('Location for the Azure AI resource')
// https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-serverless-availability#deepseek-models-from-microsoft
@allowed([
  'eastus'
  'eastus2'
  'northcentralus'
  'southcentralus'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param aiServicesResourceLocation string
param disableKeyBasedAuth bool = true

// Parameters for the specific Azure AI deployment:
param aiServicesDeploymentName string = 'DeepSeek-R1'


var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${name}-rg'
  location: location
  tags: tags
}

resource aiServicesResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(aiServicesResourceGroupName)) {
  name: !empty(aiServicesResourceGroupName) ? aiServicesResourceGroupName : resourceGroup.name
}

var prefix = '${name}-${resourceToken}'

var aiServicesNameAndSubdomain = '${resourceToken}-aiservices'
module aiServices 'br/public:avm/res/cognitive-services/account:0.7.2' = {
  name: 'deepseek'
  scope: resourceGroup
  params: {
    name: aiServicesNameAndSubdomain
    location: aiServicesResourceLocation
    tags: tags
    kind: 'AIServices'
    customSubDomainName: aiServicesNameAndSubdomain
    sku:  'S0'
    publicNetworkAccess: 'Enabled'
    deployments: [
      {
        name: aiServicesDeploymentName
        model: {
          format: 'DeepSeek'
          name: 'DeepSeek-R1'
          version: '1'
        }
        sku: {
          name: 'GlobalStandard'
          capacity: 1
        }
      }]
    disableLocalAuth: disableKeyBasedAuth
    roleAssignments: [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'Cognitive Services User'
      }
    ]
  }
}

module logAnalyticsWorkspace 'core/monitor/loganalytics.bicep' = {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: '${prefix}-loganalytics'
    location: location
    tags: tags
  }
}

// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: '${prefix}-containerapps-env'
    containerRegistryName: '${replace(prefix, '-', '')}registry'
    logAnalyticsWorkspaceName: logAnalyticsWorkspace.outputs.name
  }
}

// Container app frontend
module aca 'aca.bicep' = {
  name: 'aca'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix,19)}-ca', '--', '-')
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    aiServicesDeploymentName: aiServicesDeploymentName
    aiServicesEndpoint: 'https://${aiServices.outputs.name}.services.ai.azure.com/models'
    exists: acaExists
  }
}


module aiServicesRoleBackend 'core/security/role.bicep' = {
  scope: aiServicesResourceGroup
  name: 'aiservices-role-backend'
  params: {
    principalId: aca.outputs.SERVICE_ACA_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId

output AZURE_DEEPSEEK_DEPLOYMENT string = aiServicesDeploymentName
output AZURE_INFERENCE_ENDPOINT string = 'https://${aiServices.outputs.name}.services.ai.azure.com/models'

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.SERVICE_ACA_IDENTITY_PRINCIPAL_ID
output SERVICE_ACA_NAME string = aca.outputs.SERVICE_ACA_NAME
output SERVICE_ACA_URI string = aca.outputs.SERVICE_ACA_URI
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.SERVICE_ACA_IMAGE_NAME

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName
