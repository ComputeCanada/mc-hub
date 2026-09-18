from mchub import gunicorn_config


def test_gunicorn_does_not_launch_background_processes():
    assert not hasattr(gunicorn_config, "when_ready")
    assert not hasattr(gunicorn_config, "on_exit")
