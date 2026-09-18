import subprocess

from mchub.services import background_worker as worker


def test_failed_child_restarts_with_backoff_without_restarting_peer(mocker):
    clock = mocker.patch.object(worker.time, "monotonic", return_value=0)
    observer, culler, replacement = mocker.Mock(), mocker.Mock(), mocker.Mock()
    for process in (observer, culler, replacement):
        process.poll.return_value = None
    popen = mocker.patch.object(worker.subprocess, "Popen", side_effect=[observer, culler, replacement])
    supervisor = worker.Supervisor()
    supervisor.tick()
    assert [call.args[0][2] for call in popen.call_args_list] == list(worker.MODULES)
    observer.poll.return_value = 1
    supervisor.tick()
    assert popen.call_count == 2
    clock.return_value = 1
    supervisor.tick()
    assert popen.call_count == 3
    assert supervisor.children[worker.MODULES[1]]["process"] is culler
    culler.terminate.assert_not_called()
    replacement.poll.return_value = 0  # Even unexpected clean exits restart.
    supervisor.tick()
    clock.return_value = 2
    supervisor.tick()
    assert popen.call_count == 3  # Second failure waits two seconds.


def test_spawn_failure_does_not_prevent_other_worker_starting(mocker):
    mocker.patch.object(worker.time, "monotonic", return_value=0)
    peer = mocker.Mock()
    mocker.patch.object(worker.subprocess, "Popen", side_effect=[OSError("spawn failed"), peer])
    supervisor = worker.Supervisor()
    supervisor.tick()
    assert supervisor.children[worker.MODULES[0]]["retry_at"] == 1
    assert supervisor.children[worker.MODULES[1]]["process"] is peer


def test_shutdown_terminates_both_then_kills_slow_child(mocker):
    slow, peer = mocker.Mock(), mocker.Mock()
    slow.poll.return_value = peer.poll.return_value = None
    mocker.patch.object(worker.subprocess, "Popen", side_effect=[slow, peer])
    supervisor = worker.Supervisor()
    supervisor.tick()
    def wait(**_):
        peer.terminate.assert_called_once()
        raise subprocess.TimeoutExpired("slow", 10)
    # Assert that shutdown signals both workers before waiting on the slow one.
    slow.wait.side_effect = lambda **kwargs: wait(**kwargs) if kwargs else None
    supervisor.shutdown()
    slow.terminate.assert_called_once()
    slow.kill.assert_called_once()
    peer.wait.assert_called_once()
    assert supervisor.stopping.is_set()


def test_second_supervisor_cannot_claim_same_database_volume(tmp_path, mocker):
    import fcntl
    import pytest
    mocker.patch.object(worker, "DATABASE_PATH", str(tmp_path))
    run = mocker.patch.object(worker.Supervisor, "run")
    with (tmp_path / "background-worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(SystemExit, match="already owns"):
            worker.main()
    run.assert_not_called()
    mocker.patch.object(worker.signal, "signal")
    worker.main()
    run.assert_called_once()
