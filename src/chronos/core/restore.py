import os
import zipfile
import subprocess
from chronos.core.db import DB
from chronos.core.config import ConfigManager
from chronos.core.checkpoint import get_db_path, get_chronos_dir, get_tracked_files_list, calculate_sha256
from chronos.adapters.package_manager import get_installed_packages
from chronos.core.environment import collect_environment

def plan_restore(root_dir: str, checkpoint_id: str) -> dict:
    """Computes a plan comparing local dev environment with target checkpoint."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized.")

    db = DB(db_path)

    # Resolve short-hand / "latest" / full checkpoint ID
    target_cp = None
    if checkpoint_id.lower() == "latest":
        target_cp = db.get_latest_checkpoint()
    else:
        target_cp = db.get_checkpoint(checkpoint_id)

    if not target_cp:
        raise ValueError(f"Checkpoint '{checkpoint_id}' not found.")

    resolved_id = target_cp["id"]

    # 1. Compare Tracked Files
    config_mgr = ConfigManager(root_dir)
    config = config_mgr.load()
    local_files = get_tracked_files_list(root_dir, config)

    # Build local file map: rel_path -> sha256
    local_map = {}
    for lf in local_files:
        rel_path = os.path.relpath(lf, root_dir)
        local_map[rel_path] = calculate_sha256(lf)

    checkpoint_files = db.get_tracked_files(resolved_id)
    checkpoint_map = {f["filepath"]: f["sha256"] for f in checkpoint_files}

    files_to_restore = []
    files_to_delete = []

    # Check for modifications & additions in checkpoint relative to local
    for rel_path, cp_sha in checkpoint_map.items():
        if rel_path not in local_map:
            files_to_restore.append((rel_path, "added"))
        elif local_map[rel_path] != cp_sha:
            files_to_restore.append((rel_path, "modified"))

    # Check for untracked local files that were tracked but might need removal to match checkpoint exactly
    # We will safely remove or warn. For strict restore, we remove.
    for rel_path in local_map:
        if rel_path not in checkpoint_map:
            files_to_delete.append(rel_path)

    # 2. Compare Packages
    local_packages = get_installed_packages(root_dir)
    local_pkg_map = {(pkg[0], pkg[1]): pkg[2] for pkg in local_packages} # (mgr, name) -> ver

    checkpoint_packages = db.get_packages(resolved_id)
    checkpoint_pkg_map = {(pkg["manager"], pkg["name"]): pkg["version"] for pkg in checkpoint_packages}

    packages_to_align = []
    for (mgr, name), cp_ver in checkpoint_pkg_map.items():
        loc_ver = local_pkg_map.get((mgr, name))
        if loc_ver is None:
            packages_to_align.append({"manager": mgr, "name": name, "action": "install", "version": cp_ver})
        elif loc_ver != cp_ver:
            packages_to_align.append({"manager": mgr, "name": name, "action": "upgrade/downgrade", "version": cp_ver, "current_version": loc_ver})

    # 3. Compare Env Vars
    local_env = collect_environment(config)
    checkpoint_env = db.get_environment_variables(resolved_id)

    env_to_align = []
    for name, cp_val in checkpoint_env.items():
        loc_val = local_env.get(name)
        if loc_val is None:
            env_to_align.append({"name": name, "action": "set", "value": cp_val})
        elif loc_val != cp_val:
            env_to_align.append({"name": name, "action": "update", "value": cp_val, "current_value": loc_val})

    return {
        "checkpoint": target_cp,
        "files_to_restore": files_to_restore,
        "files_to_delete": files_to_delete,
        "packages_to_align": packages_to_align,
        "env_to_align": env_to_align
    }

def restore_checkpoint(root_dir: str, checkpoint_id: str, dry_run: bool = False) -> str:
    """Restores the workspace to the specified checkpoint state."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized.")

    db = DB(db_path)
    config_mgr = ConfigManager(root_dir)
    config = config_mgr.load()

    # Pre-restore command
    pre_cmd = config.get("commands", {}).get("pre_restore", "")
    if pre_cmd and not dry_run:
        print(f"Running pre-restore command: {pre_cmd}")
        subprocess.run(pre_cmd, shell=True, cwd=root_dir)

    plan = plan_restore(root_dir, checkpoint_id)
    cp = plan["checkpoint"]
    resolved_id = cp["id"]

    if dry_run:
        return f"Dry-run for restoring to checkpoint {resolved_id} ready. See plan."

    # Perform File Restoration
    snapshot_path = os.path.join(root_dir, cp["snapshot_path"])
    if not os.path.exists(snapshot_path):
        raise FileNotFoundError(f"Snapshot zip file '{snapshot_path}' is missing.")

    # 1. Delete files that shouldn't be here (tracked but not in checkpoint)
    for rel_path in plan["files_to_delete"]:
        full_p = os.path.join(root_dir, rel_path)
        if os.path.exists(full_p):
            try:
                os.remove(full_p)
            except Exception as e:
                print(f"Warning: Failed to delete file {rel_path}: {e}")

    # 2. Extract snapshot zip to overwrite/re-create target files
    with zipfile.ZipFile(snapshot_path, "r") as zipf:
        zipf.extractall(root_dir)

    # Post-restore command
    post_cmd = config.get("commands", {}).get("post_restore", "")
    if post_cmd:
        print(f"Running post-restore command: {post_cmd}")
        subprocess.run(post_cmd, shell=True, cwd=root_dir)

    return resolved_id
