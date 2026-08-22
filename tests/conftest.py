import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_platform_capability_sdk():
    """Globally mock PlatformCapabilitySDK to prevent network calls during testing."""
    with patch("runtime_core.PlatformCapabilitySDK") as MockSDK:
        instance = MockSDK.return_value
        
        # Create a mock InvocationResult
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.response = {"status": "SUCCESS", "message": "Mock executed by conftest"}
        mock_result.error = None
        
        # Return it from invoke_capability
        instance.invoke_capability.return_value = mock_result
        
        yield
