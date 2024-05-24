"""pytest fixtures."""
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield
