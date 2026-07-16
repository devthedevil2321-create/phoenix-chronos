import os
from datetime import datetime
from chronos.core.db import DB
from chronos.core.checkpoint import get_db_path

def get_timeline(root_dir: str) -> list[dict]:
    """Retrieves all checkpoints sorted by timestamp."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized.")

    db = DB(db_path)
    return db.get_all_checkpoints()

def render_timeline(root_dir: str) -> str:
    """Returns a beautiful ASCII representation of the checkpoint history."""
    try:
        checkpoints = get_timeline(root_dir)
    except Exception as e:
        return str(e)

    if not checkpoints:
        return "No checkpoints found. Start by running 'chronos checkpoint <message>'!"

    lines = []
    lines.append("🕒 Phoenix Chronos - Development History Timeline")
    lines.append("==================================================")

    for i, cp in enumerate(checkpoints):
        # Format Timestamp
        try:
            dt = datetime.fromisoformat(cp["timestamp"])
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = cp["timestamp"]

        indicator = "●"
        connector = "│"
        if i == 0:
            indicator = "🔥 (latest)"
        if i == len(checkpoints) - 1:
            connector = " "

        branch_info = f" [{cp['git_branch']}]" if cp["git_branch"] else ""
        commit_info = f" ({cp['git_commit'][:7]})" if cp["git_commit"] else ""

        lines.append(f" {indicator}  ID: \033[94m{cp['id']}\033[0m")
        lines.append(f" {connector}   Time:    {time_str}")
        lines.append(f" {connector}   Git:     {branch_info}{commit_info}")
        lines.append(f" {connector}   Message: \033[92m{cp['message']}\033[0m")
        if i < len(checkpoints) - 1:
            lines.append(" │")

    return "\n".join(lines)
