"""Tiny API wrapper: the Celery worker submits pipeline runs here.
Jobs run Nextflow pipelines defined in pipelines/."""
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()
BANKS_DIR = Path("/data/dbs")
PIPELINES = Path("/srv/pipelines")
JOBS: dict[str, dict] = {}


@app.post("/jobs")
def create_job(pipeline: str, bank: str, version: str,
               params: dict | None = None):
    """Start a Nextflow pipeline in the background (fire and forget)."""
    job_id = str(uuid.uuid4())
    log_path = BANKS_DIR / bank / f"pipeline-{version}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "nextflow", "-log", str(log_path), "run",
        str(PIPELINES / pipeline),
        "--bank", bank, "--version", version,
        "--banks_dir", str(BANKS_DIR),
    ]
    # Extra params become --param value CLI arguments
    for key, value in (params or {}).items():
        cmd += [f"--{key}", str(value)]

    log_file = log_path.open("w")
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    JOBS[job_id] = {"status": "running", "pid": proc.pid, "log": str(log_path)}
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return {"status": "unknown"}
    # Reap the process to detect completion
    from fastapi.concurrency import run_in_threadpool
    proc = subprocess.CompletedProcess
    # (simplified; in production track with asyncio or psutil)
    if job["status"] == "running":
        try:
            pid_alive = Path(f"/proc/{job['pid']}").exists()
        except Exception:
            pid_alive = False
        if not pid_alive:
            job["status"] = "success"  # assume success; refine with exit code
    return job