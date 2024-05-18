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

@description('Flag to decide where to create OpenAI role for current user')
param createRoleForUser bool = true

param acaExists bool = false

param deployAzureOpenAi bool = true

param openAiResourceName string = ''
param openAiResourceGroupName string = ''
param openAiResourceGroupLocation string = ''
param openAiDeploymentName string = 'chatgpt'
param openAiSkuName string = ''
param openAiDeploymentCapacity int = 30
param openAiApiVersion string = ''

var openAiConfig = {
  modelName: deployAzureOpenAi ? 'gpt-35-turbo' : 'gpt-3.5-turbo'
  deploymentName: !empty(openAiDeploymentName) ? openAiDeploymentName : 'chatgpt'
  deploymentCapacity: openAiDeploymentCapacity != 0 ? openAiDeploymentCapacity : 30
}

@secure()
param openAiComAPIKey string = ''
param openAiComAPIKeySecretName string = 'openai-com-api-key'

param authClientId string
@secure()
param authClientSecret string
param authClientSecretName string = 'AZURE-AUTH-CLIENT-SECRET'
param authTenantId string
param loginEndpoint string
param tenantId string = tenant().tenantId
var tenantIdForAuth = !empty(authTenantId) ? authTenantId : tenantId

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${name}-rg'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' existing = if (!empty(openAiResourceGroupName)) {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

var prefix = '${name}-${resourceToken}'

module openAi 'core/ai/cognitiveservices.bicep' = if (deployAzureOpenAi) {
  name: 'openai'
  scope: openAiResourceGroup
  params: {
    name: !empty(openAiResourceName) ? openAiResourceName : '${resourceToken}-cog'
    location: !empty(openAiResourceGroupLocation) ? openAiResourceGroupLocation : location
    tags: tags
    sku: {
      name: !empty(openAiSkuName) ? openAiSkuName : 'S0'
    }
    deployments: [
      {
        name: openAiConfig.deploymentName
        model: {
          format: 'OpenAI'
          name: openAiConfig.modelName
          version: '0125'
        }
        sku: {
          name: 'Standard'
          capacity: openAiConfig.deploymentCapacity
        }
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



// Currently, we only need Key Vault for storing Search service key,
// which is only used for free tier
module keyVault 'core/security/keyvault.bicep' = {
  name: 'keyvault'
  scope: resourceGroup
  params: {
    name: '${replace(take(prefix, 17), '-', '')}-vault'
    location: location
    principalId: principalId
  }
}

module openAiComAPIKeyStorage 'core/security/keyvault-secret.bicep' = if (!empty(openAiComAPIKey)) {
  name: 'openai-key-secret'
  scope: resourceGroup
  params: {
    keyVaultName: keyVault.outputs.name
    name: openAiComAPIKeySecretName
    secretValue: openAiComAPIKey
  }
}


module authClientSecretStorage 'core/security/keyvault-secret.bicep' = if (!empty(authClientSecret)) {
    name: 'secrets'
    scope: resourceGroup
    params: {
      keyVaultName: keyVault.outputs.name
      name: authClientSecretName
      secretValue: authClientSecret
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
    openAiDeploymentName: deployAzureOpenAi ? openAiDeploymentName : ''
    openAiEndpoint: deployAzureOpenAi ? openAi.outputs.endpoint : ''
    openAiApiVersion: deployAzureOpenAi ? openAiApiVersion : ''
    openAiComAPIKeySecretName: openAiComAPIKeySecretName
    exists: acaExists
    authClientId: authClientId
    authClientSecretName: authClientSecretName
    authTenantId: tenantIdForAuth
    authLoginEndpoint: loginEndpoint
    azureKeyVaultName: keyVault.outputs.name
  }
  dependsOn: [authClientSecretStorage]
}


module openAiRoleUser 'core/security/role.bicep' = if (createRoleForUser && deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'User'
  }
}


module openAiRoleBackend 'core/security/role.bicep' = if (deployAzureOpenAi) {
  scope: openAiResourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: aca.outputs.SERVICE_ACA_IDENTITY_PRINCIPAL_ID
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
    principalType: 'ServicePrincipal'
  }
}


output AZURE_LOCATION string = location

output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = deployAzureOpenAi ? openAiDeploymentName : ''
output AZURE_OPENAI_API_VERSION string = deployAzureOpenAi ? openAiApiVersion : ''
output AZURE_OPENAI_ENDPOINT string = deployAzureOpenAi ? openAi.outputs.endpoint : ''
output AZURE_OPENAI_RESOURCE string = deployAzureOpenAi ? openAi.outputs.name : ''
output AZURE_OPENAI_RESOURCE_GROUP string = deployAzureOpenAi ? openAiResourceGroup.name : ''
output AZURE_OPENAI_SKU_NAME string = deployAzureOpenAi ? openAi.outputs.skuName : ''
output AZURE_OPENAI_RESOURCE_GROUP_LOCATION string = deployAzureOpenAi ? openAiResourceGroup.location : ''
output OPENAICOM_API_KEY_SECRET_NAME string = openAiComAPIKeySecretName
output OPENAI_MODEL_NAME string = openAiConfig.modelName

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.SERVICE_ACA_IDENTITY_PRINCIPAL_ID
output SERVICE_ACA_NAME string = aca.outputs.SERVICE_ACA_NAME
output SERVICE_ACA_URI string = aca.outputs.SERVICE_ACA_URI
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.SERVICE_ACA_IMAGE_NAME

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName

output AZURE_KEY_VAULT_NAME string = keyVault.outputs.name
