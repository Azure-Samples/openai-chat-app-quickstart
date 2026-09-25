import azure.core.credentials_async


class MockAzureCredential(azure.core.credentials_async.AsyncTokenCredential):
    async def get_token(self, *scopes, **kwargs):
        """Mock get_token method that returns a fake token."""
        import time

        from azure.core.credentials import AccessToken

        # Return a mock token that expires in 1 hour
        return AccessToken("mock_token", int(time.time()) + 3600)

    async def close(self):
        """Mock close method."""
        pass
