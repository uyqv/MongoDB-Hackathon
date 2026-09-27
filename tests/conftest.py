"""Keep ordinary test runs independent of local credentials and Atlas state."""
import os

import pytest


def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true",
                     help="Enable MongoDB tests in disposable test databases")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        if os.environ.get("DB_NAME") != "second_shift_david":
            raise pytest.UsageError("--run-integration requires DB_NAME=second_shift_david")
        return
    skip = pytest.mark.skip(reason="MongoDB integration test; use --run-integration with a test database")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
