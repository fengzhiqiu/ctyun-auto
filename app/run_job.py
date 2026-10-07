"""Run cron and manual tasks with the same environment and per-task lock."""
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

JOBS = {"login": "/app/login_script.py", "pc": "/app/pc_login.py"}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in JOBS:
        raise SystemExit("Usage: python /app/run_job.py {login|pc} [--config-redeem]")
    name = sys.argv[1]
    os.environ.update(json.loads(Path("/run/ctyun/environment.json").read_text()))
    with open(f"/run/ctyun/{name}.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[*] {name} 任务正在运行，跳过重复启动；请等待现有任务结束。")
            return 0
        return subprocess.call([sys.executable, "-u", JOBS[name], *sys.argv[2:]])


if __name__ == "__main__":
    sys.exit(main())
