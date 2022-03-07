import pytest

"""
Adds the --build-live-cluster option when running pytests, which is disabled by default.
This option allows the tests in test_live_cluster.py to run.

Inspired by:
https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
"""


def pytest_addoption(parser):
    parser.addoption(
        "--build-live-cluster",
        action="store_true",
        default=False,
        help="Builds a live cluster using OpenStack credentials provided in environment variables (slow)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "build_live_cluster: Marks test as building live clusters"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--build-live-cluster"):
        return
    skip_build_live_cluster = pytest.mark.skip(
        reason="need --build-live-cluster to build live clusters"
    )
    for item in items:
        if "build_live_cluster" in item.keywords:
            item.add_marker(skip_build_live_cluster)

