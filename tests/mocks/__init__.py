import pytest
from datetime import datetime


@pytest.fixture(autouse=True)
def mock_load_config(mocker):
    mocker.patch("mchub.configuration.load_config", return_value={})
