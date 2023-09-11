from collections import namedtuple

MockToken = namedtuple("MockToken", ["token", "expires_on"])


class MockAzureCredential:
    def __init__(self, *args, **kwargs):
        pass

    async def get_token(self, uri):
        return MockToken("mock_token", 9999999999)
