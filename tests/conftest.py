"""Pytest configuration for dask-iclx tests."""


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test requiring HTCondor"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test that can run anywhere"
    )
