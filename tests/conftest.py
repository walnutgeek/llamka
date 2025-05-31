import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item


def pytest_configure(config: Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test that requires real API calls"
    )


def pytest_addoption(parser: Parser) -> None:
    """Add command line options for running integration tests."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that require real API calls",
    )


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    """Skip integration tests unless --run-integration flag is provided."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
