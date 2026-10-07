"""Configure persistent device identity and cron without shell interpolation."""
import json
import os
import re
import secrets
from pathlib import Path

DEFAULT_LOGIN_CRON = "0 3,20 * * *"
DEFAULT_PC_CRON = "0 4,6 * * *"


def validate_cron(expression):
    fields = expression.split()
    limits = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    if len(fields) != 5 or "\n" in expression or "\r" in expression:
        raise ValueError("Cron must contain five numeric fields")
    for field, (low, high) in zip(fields, limits):
        for item in field.split(","):
            match = re.fullmatch(r"(\*|[0-9]+(?:-[0-9]+)?)(?:/([0-9]+))?", item)
            if not match:
                raise ValueError("Invalid cron field")
            base, step = match.groups()
            if step is not None and not 1 <= int(step) <= high - low + 1:
                raise ValueError("Invalid cron step")
            if base != "*":
                bounds = [int(x) for x in base.split("-")]
                if any(x < low or x > high for x in bounds) or bounds[0] > bounds[-1]:
                    raise ValueError("Cron value out of range")
    return " ".join(fields)


def configure(env, data_dir=Path("/app/data"), run_dir=Path("/run/ctyun"),
              cron_path=Path("/etc/cron.d/ctyun-cron")):
    user = env.get("APP_USER", "")
    if not re.fullmatch(r"[A-Za-z0-9_.@+-]+", user) or not env.get("APP_PASSWORD"):
        raise ValueError("Set APP_USER and APP_PASSWORD before starting the container")
    login_cron = validate_cron(env.get("LOGIN_CRON", DEFAULT_LOGIN_CRON))
    pc_cron = validate_cron(env.get("PC_CRON", DEFAULT_PC_CRON))
    data_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    device_path = data_dir / f".devicecode_{user}"
    device = env.get("DEVICECODE", "").strip()
    if not device and device_path.is_file():
        device = device_path.read_text().strip()
    if not device:
        device = "web_" + secrets.token_hex(16)
    device_path.write_text(device + "\n")
    device_path.chmod(0o600)

    # JSON preserves quotes, dollar signs and spaces in passwords verbatim.
    runtime_env = {key: env[key] for key in (
        "APP_USER", "APP_PASSWORD", "TZ", "CHROME_PATH", "HTTP_PROXY", "HTTPS_PROXY",
        "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"
    ) if key in env}
    runtime_env.update(DEVICECODE=device, RUNNING_IN_DOCKER="true", PYTHONUNBUFFERED="1")
    env_path = run_dir / "environment.json"
    env_path.write_text(json.dumps(runtime_env))
    env_path.chmod(0o600)
    cron_path.write_text(
        "SHELL=/bin/sh\nPATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
        + f"{login_cron} root /opt/venv/bin/python /app/run_job.py login > /proc/1/fd/1 2>&1\n"
        + f"{pc_cron} root /opt/venv/bin/python /app/run_job.py pc > /proc/1/fd/1 2>&1\n"
    )
    cron_path.chmod(0o644)
    return device


if __name__ == "__main__":
    try:
        configure(os.environ)
        print("[*] 数据目录和定时任务已配置，设备标识已持久化。")
    except (ValueError, OSError) as exc:
        raise SystemExit(f"[!] 容器配置失败: {exc}")
