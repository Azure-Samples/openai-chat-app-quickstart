param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'aca'
param exists bool
param openAiDeploymentName string
param openAiEndpoint string
param openAiApiVersion string
param openAiComAPIKeySecretName string
param azureKeyVaultName string

param authClientId string
param authClientSecretName string
param authTenantId string
param authLoginEndpoint string

// The issuer is different depending if we are in a workforce or external tenant
var openIdIssuer = empty(authLoginEndpoint) ? '${environment().authentication.loginEndpoint}${authTenantId}/v2.0' : 'https://${authLoginEndpoint}/${authTenantId}/v2.0'

resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource keyVault 'Microsoft.KeyVault/vaults@2022-07-01' existing = {
  name: azureKeyVaultName
}


module webKVAccess 'core/security/keyvault-access.bicep' = {
  name: 'web-keyvault-access'
  params: {
    keyVaultName: keyVault.name
    principalId: acaIdentity.properties.principalId
  }
}


module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: acaIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    env: [
      {
        name: 'AZURE_OPENAI_CHATGPT_DEPLOYMENT'
        value: openAiDeploymentName
      }
      {
        name: 'AZURE_OPENAI_ENDPOINT'
        value: openAiEndpoint
      }
      {
        name: 'AZURE_OPENAI_API_VERSION'
        value: openAiApiVersion
      }
      {
        name: 'RUNNING_IN_PRODUCTION'
        value: 'true'
      }
      // Must be named AZURE_CLIENT_ID for DefaultAzureCredential to find it automatically
      {
        name: 'AZURE_CLIENT_ID'
        value: acaIdentity.properties.clientId
      }
      {
        name: 'OPENAICOM_API_KEY_SECRET_NAME'
        value: openAiComAPIKeySecretName
      }
      {
        name: 'AZURE_KEY_VAULT_NAME'
        value: azureKeyVaultName
      }
    ]
    targetPort: 50505
    keyvaultIdentities: {
      'microsoft-provider-authentication-secret': {
        keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${authClientSecretName}'
        identity: acaIdentity.id
      }
    }
  }
  dependsOn: [
    webKVAccess
  ]
}


module auth 'core/host/container-apps-auth.bicep' = {
  name: '${serviceName}-container-apps-auth-module'
  params: {
    name: app.outputs.name
    clientId: authClientId
    clientSecretName: 'microsoft-provider-authentication-secret'
    openIdIssuer: openIdIssuer
  }
}

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = acaIdentity.properties.principalId
output SERVICE_ACA_NAME string = app.outputs.name
output SERVICE_ACA_URI string = app.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = app.outputs.imageName
