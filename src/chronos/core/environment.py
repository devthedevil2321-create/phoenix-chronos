import os
import subprocess

def get_git_state(root_dir: str) -> dict:
    """Safely retrieves Git repository state."""
    state = {
        "commit": None,
        "branch": None,
        "status": None
    }
    # Check if git is installed and directory is a git repo
    if not os.path.exists(os.path.join(root_dir, ".git")):
        return state

    try:
        # Commit
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root_dir,
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        state["commit"] = commit
    except Exception:
        pass

    try:
        # Branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root_dir,
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        state["branch"] = branch
    except Exception:
        pass

    try:
        # Status
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root_dir,
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        state["status"] = status if status else "clean"
    except Exception:
        state["status"] = "unknown"

    return state

def collect_environment(config: dict) -> dict:
    """Collects system/env variables specified in the configuration."""
    env_vars = {}
    tracked_names = config.get("environment_variables", [])

    # Always include some default ones if present
    for name in tracked_names:
        val = os.environ.get(name)
        if val is not None:
            # Simple sanitization/masking for potential credentials (e.g. key, token, secret)
            # though user config should ideally handle what is included.
            if any(secret_word in name.lower() for secret_word in ["key", "token", "secret", "password"]):
                env_vars[name] = "********"
            else:
                env_vars[name] = val
    return env_vars
