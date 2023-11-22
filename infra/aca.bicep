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

@description('Enable Auth')
param useAuthentication bool
param clientId string

param tenantId string
param loginEndpoint string

@secure()
param clientSecret string
#disable-next-line secure-secrets-in-params
param clientSecretName string = 'microsoft-provider-authentication-secret'

// the issuer is different depending if we are in a workforce or external tenant
var openIdIssuer = empty(tenantId) ? '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0' : 'https://${loginEndpoint}/${tenantId}/v2.0'

var secrets = !useAuthentication ? [] : [{
    name: clientSecretName
    value: clientSecret
}]

resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
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
        name: 'RUNNING_IN_PRODUCTION'
        value: 'true'
      }
      {
        name: 'AZURE_OPENAI_CLIENT_ID'
        value: acaIdentity.properties.clientId
      }
    ]
    targetPort: 50505
    secrets: secrets
  }
}


module auth 'core/host/container-auth.bicep' = {
  name: '${serviceName}-container-auth-module'
  params: {
    name: app.outputs.name
    useAuthentication: useAuthentication
    clientId: clientId
    clientSecretName: clientSecretName
    openIdIssuer: openIdIssuer
  }
}

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = acaIdentity.properties.principalId
output SERVICE_ACA_NAME string = app.outputs.name
output SERVICE_ACA_URI string = app.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = app.outputs.imageName

