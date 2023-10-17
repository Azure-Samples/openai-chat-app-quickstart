param name string

param useAuthentication bool
param clientId string
param clientSecretName string
param openIdIssuer string


resource app 'Microsoft.App/containerApps@2023-05-02-preview' existing = {
  name: name
}

resource auth 'Microsoft.App/containerApps/authConfigs@2023-05-02-preview' = if (useAuthentication) {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      redirectToProvider: 'azureactivedirectory'
      unauthenticatedClientAction: 'RedirectToLoginPage'
    }
    identityProviders: {
      azureActiveDirectory: {
        registration: {
          clientId: clientId
          clientSecretSettingName: clientSecretName
          openIdIssuer: openIdIssuer
        }
      }
    }
  }
}

