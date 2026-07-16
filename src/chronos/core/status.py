import os
from chronos.core.db import DB
from chronos.core.checkpoint import get_db_path, get_tracked_files_list, calculate_sha256
from chronos.core.config import ConfigManager
from chronos.adapters.package_manager import get_installed_packages
from chronos.core.environment import collect_environment, get_git_state

def get_status(root_dir: str) -> dict:
    """Computes differences between active directory state and the latest checkpoint."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized. Run 'chronos init' first.")

    db = DB(db_path)
    latest_cp = db.get_latest_checkpoint()

    config_mgr = ConfigManager(root_dir)
    config = config_mgr.load()

    res = {
        "latest_checkpoint": latest_cp,
        "files": {"modified": [], "untracked": [], "missing": []},
        "packages": {"added": [], "removed": [], "modified": []},
        "env": {"added": [], "removed": [], "modified": []},
        "git": get_git_state(root_dir)
    }

    if not latest_cp:
        # All local files matching config are untracked since there are no checkpoints
        local_files = get_tracked_files_list(root_dir, config)
        res["files"]["untracked"] = [os.path.relpath(lf, root_dir) for lf in local_files]
        return res

    cp_id = latest_cp["id"]

    # 1. Compare Files
    cp_files = {f["filepath"]: f["sha256"] for f in db.get_tracked_files(cp_id)}

    local_files = get_tracked_files_list(root_dir, config)
    local_map = {}
    for lf in local_files:
        rel_p = os.path.relpath(lf, root_dir)
        local_map[rel_p] = calculate_sha256(lf)

    # Missing and Modified
    for rel_p, cp_sha in cp_files.items():
        if rel_p not in local_map:
            res["files"]["missing"].append(rel_p)
        elif local_map[rel_p] != cp_sha:
            res["files"]["modified"].append(rel_p)

    # Untracked
    for rel_p in local_map:
        if rel_p not in cp_files:
            res["files"]["untracked"].append(rel_p)

    # 2. Compare Packages
    cp_pkgs = {(p["manager"], p["name"]): p["version"] for p in db.get_packages(cp_id)}
    local_pkgs = {(p[0], p[1]): p[2] for p in get_installed_packages(root_dir)}

    for (mgr, name), ver in local_pkgs.items():
        if (mgr, name) not in cp_pkgs:
            res["packages"]["added"].append({"manager": mgr, "name": name, "version": ver})
        elif cp_pkgs[(mgr, name)] != ver:
            res["packages"]["modified"].append({
                "manager": mgr, "name": name,
                "checkpoint_version": cp_pkgs[(mgr, name)],
                "local_version": ver
            })

    for (mgr, name), ver in cp_pkgs.items():
        if (mgr, name) not in local_pkgs:
            res["packages"]["removed"].append({"manager": mgr, "name": name, "version": ver})

    # 3. Compare Env
    cp_env = db.get_environment_variables(cp_id)
    local_env = collect_environment(config)

    for name, val in local_env.items():
        if name not in cp_env:
            res["env"]["added"].append({"name": name, "value": val})
        elif cp_env[name] != val:
            res["env"]["modified"].append({
                "name": name,
                "checkpoint_value": cp_env[name],
                "local_value": val
            })

    for name, val in cp_env.items():
        if name not in local_env:
            res["env"]["removed"].append({"name": name, "value": val})

    return res

def render_status(root_dir: str) -> str:
    """Renders the current status comparison nicely."""
    try:
        status_data = get_status(root_dir)
    except Exception as e:
        return str(e)

    lines = []
    lines.append("🔍 Phoenix Chronos - Dev Environment Status")
    lines.append("==========================================")

    latest_cp = status_data["latest_checkpoint"]
    if not latest_cp:
        lines.append("No checkpoints found. Tracked files are currently untracked.")
        lines.append("\n📁 Files Untracked:")
        for f in status_data["files"]["untracked"]:
            lines.append(f"  \033[93m? {f}\033[0m")
        return "\n".join(lines)

    lines.append(f"Latest Checkpoint: \033[94m{latest_cp['id']}\033[0m (\"{latest_cp['message']}\")")
    lines.append(f"Git State: branch={status_data['git']['branch']} commit={status_data['git']['commit'][:7] if status_data['git']['commit'] else 'none'}")
    lines.append("------------------------------------------")

    # Files
    f_diff = status_data["files"]
    if f_diff["modified"] or f_diff["untracked"] or f_diff["missing"]:
        lines.append("\n📁 File Status:")
        for f in f_diff["missing"]:
            lines.append(f"  \033[91m- [Missing]   {f}\033[0m")
        for f in f_diff["modified"]:
            lines.append(f"  \033[93m~ [Modified]  {f}\033[0m")
        for f in f_diff["untracked"]:
            lines.append(f"  \033[92m+ [Untracked] {f}\033[0m")
    else:
        lines.append("\n📁 File Status: Match latest checkpoint completely.")

    # Packages
    p_diff = status_data["packages"]
    if p_diff["added"] or p_diff["removed"] or p_diff["modified"]:
        lines.append("\n📦 Package Status:")
        for p in p_diff["added"]:
            lines.append(f"  \033[92m+ [{p['manager']}] {p['name']}=={p['version']}\033[0m")
        for p in p_diff["modified"]:
            lines.append(f"  \033[93m~ [{p['manager']}] {p['name']} (Checkpoint: {p['checkpoint_version']} -> Local: {p['local_version']})\033[0m")
        for p in p_diff["removed"]:
            lines.append(f"  \033[91m- [{p['manager']}] {p['name']}=={p['version']}\033[0m")
    else:
        lines.append("\n📦 Package Status: Match latest checkpoint completely.")

    # Env Vars
    e_diff = status_data["env"]
    if e_diff["added"] or e_diff["removed"] or e_diff["modified"]:
        lines.append("\n⚙️ Environment Variables Status:")
        for e in e_diff["added"]:
            lines.append(f"  \033[92m+ {e['name']}={e['value']}\033[0m")
        for e in e_diff["modified"]:
            lines.append(f"  \033[93m~ {e['name']} (Checkpoint: {e['checkpoint_value']} -> Local: {e['local_value']})\033[0m")
        for e in e_diff["removed"]:
            lines.append(f"  \033[91m- {e['name']}\033[0m")
    else:
        lines.append("\n⚙️ Environment Variables Status: Match latest checkpoint completely.")

    return "\n".join(lines)
