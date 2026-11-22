"""Read-only Mac readiness check. Never prints environment values or secrets."""

import json
import subprocess
from pathlib import Path
from urllib.request import urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    env = {}
    for line in (root / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value.strip()
    checks = {
        "deepseek_key_configured": bool(env.get("DEEPSEEK_API_KEY")),
        "docker_provider": env.get("SANDBOX_PROVIDER") == "docker",
        "infra_profile": "infra" in env.get("COMPOSE_PROFILES", "").split(","),
    }
    try:
        with urlopen("http://localhost:8000/health", timeout=10) as response:
            checks["backend"] = json.load(response).get("status") == "healthy"
    except (OSError, ValueError):
        checks["backend"] = False
    try:
        with urlopen("http://localhost:5173", timeout=10) as response:
            checks["frontend"] = response.status == 200
    except (OSError, ValueError):
        checks["frontend"] = False
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=15,
        )
        checks["docker_access"] = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        checks["docker_access"] = False
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
