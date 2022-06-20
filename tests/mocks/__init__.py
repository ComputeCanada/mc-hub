import pytest
from datetime import datetime


@pytest.fixture(autouse=True)
def config_datetime(mocker):
    mocker.patch("datetime.datetime.now", return_value=datetime(2020, 1, 1))
