import azure.core.credentials_async


class MockAzureCredential(azure.core.credentials_async.AsyncTokenCredential):
    pass
