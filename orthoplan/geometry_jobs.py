"""Bounded, cancellable geometry subprocesses for the local development server.

Watchdog limits are sampled, not a security sandbox. Results expire after five
minutes and are kept on disk so completed meshes do not accumulate in server RAM.
"""

from __future__ import annotations

import atexit
import json
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


class GeometryBusy(ValueError):
    """Retryable admission failure; no worker was created."""


class GeometryJobs:
    def __init__(
        self, *, timeout=120, memory_mb=1024, max_active=2, max_result_bytes=32 * 1024 * 1024
    ):
        self.timeout, self.memory_mb = timeout, memory_mb
        self.max_active, self.max_result_bytes = max_active, max_result_bytes
        self.jobs = {}
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.monitor = threading.Thread(target=self._watch, daemon=True)
        self.monitor.start()

    def start(self, operation, payload, *, workspace, ui_dir):
        if operation not in ("evaluate", "segment", "motion", "contact"):
            raise ValueError("Unsupported geometry operation")
        if not isinstance(payload, dict):
            raise ValueError("Geometry payload must be an object")
        with self.lock:
            if (
                self.closed.is_set()
                or sum(j["status"] == "running" for j in self.jobs.values()) >= self.max_active
            ):
                raise GeometryBusy("Geometry workers are busy. Retry shortly.")
            if len(self.jobs) >= 32:
                raise ValueError("Too many retained jobs. Retry after results expire.")
            directory = tempfile.TemporaryDirectory(prefix="ortho-geometry-")
            root = Path(directory.name)
            source, output = root / "request.json", root / "result.json"
            source.write_text(
                json.dumps(
                    dict(
                        operation=operation,
                        payload=payload,
                        workspace=str(workspace),
                        ui_dir=str(ui_dir),
                    )
                )
            )
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "orthoplan.geometry_worker", str(source), str(output)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                directory.cleanup()
                raise
            key = uuid.uuid4().hex
            self.jobs[key] = dict(
                process=process,
                directory=directory,
                output=output,
                started=time.monotonic(),
                status="running",
                error=None,
            )
            return {"ok": True, "job_id": key, "status": "running"}

    def get(self, key, *, cancel=False):
        with self.lock:
            job = self.jobs.get(key)
            if job is None:
                return {"ok": False, "status": "missing", "errors": ["Job expired or not found."]}
            if cancel:
                if job["status"] == "running":
                    self._stop(job, "cancelled")
                else:
                    job["directory"].cleanup()
                    del self.jobs[key]
                    return {"ok": True, "status": "released"}
            result = {"ok": True, "job_id": key, "status": job["status"]}
            if job["error"]:
                result.update(ok=False, errors=[job["error"]])
            if job["status"] == "complete":
                result["result"] = json.loads(job["output"].read_text())
            return result

    def _stop(self, job, reason):
        process = job["process"]
        if process.poll() is None:
            process.kill()
        process.wait()
        job.update(status=reason, error=f"Geometry job {reason}.")

    def _tick(self):
        with self.lock:
            now = time.monotonic()
            for key, job in list(self.jobs.items()):
                if job["status"] != "running":
                    if now - job["started"] > 300:
                        job["directory"].cleanup()
                        del self.jobs[key]
                    continue
                process, output = job["process"], job["output"]
                if now - job["started"] > self.timeout:
                    self._stop(job, "timed out")
                elif output.exists() and output.stat().st_size > self.max_result_bytes:
                    self._stop(job, "exceeded result limit")
                elif process.poll() is not None:
                    job["status"] = (
                        "complete" if process.returncode == 0 and output.exists() else "failed"
                    )
                    if job["status"] == "failed":
                        job["error"] = "Geometry worker failed."
                else:
                    # ps RSS is KiB on supported local macOS/Linux servers.
                    try:
                        rss = subprocess.run(
                            ["ps", "-o", "rss=", "-p", str(process.pid)],
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        if rss.returncode != 0 and process.poll() is None:
                            self._stop(job, "memory monitoring unavailable")
                        elif (
                            rss.returncode == 0
                            and int(rss.stdout.strip() or "0") > self.memory_mb * 1024
                        ):
                            self._stop(job, "exceeded memory limit")
                    except (OSError, ValueError, subprocess.TimeoutExpired):
                        self._stop(job, "memory monitoring unavailable")

    def _watch(self):
        while not self.closed.wait(0.2):
            self._tick()

    def close(self):
        self.closed.set()
        self.monitor.join(timeout=3)
        with self.lock:
            for job in self.jobs.values():
                if job["status"] == "running":
                    self._stop(job, "cancelled")
                job["directory"].cleanup()
            self.jobs.clear()


jobs = GeometryJobs()
atexit.register(jobs.close)
