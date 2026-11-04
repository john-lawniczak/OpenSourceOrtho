import time
from pathlib import Path

import pytest

from orthoplan.geometry_jobs import GeometryJobs


def wait_done(manager, key):
    for _ in range(150):
        result = manager.get(key)
        if result["status"] != "running":
            return result
        time.sleep(0.05)
    pytest.fail("worker did not finish")


def test_worker_result_and_cleanup(tmp_path):
    manager = GeometryJobs()
    try:
        job = manager.start("evaluate", {"id": "job-test"}, workspace=tmp_path, ui_dir=Path("ui"))
        result = wait_done(manager, job["job_id"])
        assert result["status"] == "complete"
        assert "ok" in result["result"]
        directories = [j["directory"].name for j in manager.jobs.values()]
    finally:
        manager.close()
    assert all(not Path(p).exists() for p in directories)


def test_cancel_and_capacity(tmp_path):
    manager = GeometryJobs(max_active=1)
    try:
        job = manager.start("evaluate", {}, workspace=tmp_path, ui_dir=Path("ui"))
        with pytest.raises(ValueError, match="busy"):
            manager.start("evaluate", {}, workspace=tmp_path, ui_dir=Path("ui"))
        result = manager.get(job["job_id"], cancel=True)
        assert result["status"] == "cancelled"
        assert manager.jobs[job["job_id"]]["process"].poll() is not None
        assert manager.get("unknown")["status"] == "missing"
    finally:
        manager.close()


@pytest.mark.parametrize(
    "limits, expected",
    [({"timeout": 0}, "timed out"), ({"max_result_bytes": 0}, "exceeded result limit")],
)
def test_limits_terminate_workers(tmp_path, limits, expected):
    manager = GeometryJobs(**limits)
    try:
        job = manager.start("evaluate", {}, workspace=tmp_path, ui_dir=Path("ui"))
        assert wait_done(manager, job["job_id"])["status"] == expected
    finally:
        manager.close()


def test_memory_limit_kills_live_worker(tmp_path, monkeypatch):
    import subprocess

    real_popen = subprocess.Popen
    manager = GeometryJobs(memory_mb=1)
    # Use an actual long-lived child so completion cannot race the RSS sample.
    monkeypatch.setattr(
        "orthoplan.geometry_jobs.subprocess.Popen",
        lambda command, **kwargs: (
            real_popen(
                [__import__("sys").executable, "-c", "import time; time.sleep(10)"], **kwargs
            )
            if "-m" in command
            else real_popen(command, **kwargs)
        ),
    )
    try:
        job = manager.start("evaluate", {}, workspace=tmp_path, ui_dir=Path("ui"))
        assert wait_done(manager, job["job_id"])["status"] == "exceeded memory limit"
    finally:
        manager.close()
