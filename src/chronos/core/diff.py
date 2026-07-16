import os
from chronos.core.db import DB
from chronos.core.checkpoint import get_db_path

def diff_checkpoints(root_dir: str, cp1_id: str, cp2_id: str) -> dict:
    """Compares two checkpoints and returns files, packages, and environment differences."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized.")

    db = DB(db_path)

    # Resolve checkpoints
    cp1 = db.get_checkpoint(cp1_id)
    cp2 = db.get_checkpoint(cp2_id)

    if not cp1:
        raise ValueError(f"Checkpoint '{cp1_id}' not found.")
    if not cp2:
        raise ValueError(f"Checkpoint '{cp2_id}' not found.")

    res = {
        "cp1": cp1,
        "cp2": cp2,
        "files": {"added": [], "removed": [], "modified": []},
        "packages": {"added": [], "removed": [], "modified": []},
        "env": {"added": [], "removed": [], "modified": []}
    }

    # 1. Compare Files
    files1 = {f["filepath"]: f["sha256"] for f in db.get_tracked_files(cp1["id"])}
    files2 = {f["filepath"]: f["sha256"] for f in db.get_tracked_files(cp2["id"])}

    for filepath, sha in files2.items():
        if filepath not in files1:
            res["files"]["added"].append(filepath)
        elif files1[filepath] != sha:
            res["files"]["modified"].append(filepath)

    for filepath in files1:
        if filepath not in files2:
            res["files"]["removed"].append(filepath)

    # 2. Compare Packages
    pkgs1 = {(p["manager"], p["name"]): p["version"] for p in db.get_packages(cp1["id"])}
    pkgs2 = {(p["manager"], p["name"]): p["version"] for p in db.get_packages(cp2["id"])}

    for (mgr, name), ver in pkgs2.items():
        if (mgr, name) not in pkgs1:
            res["packages"]["added"].append({"manager": mgr, "name": name, "version": ver})
        elif pkgs1[(mgr, name)] != ver:
            res["packages"]["modified"].append({
                "manager": mgr, "name": name,
                "cp1_version": pkgs1[(mgr, name)],
                "cp2_version": ver
            })

    for (mgr, name), ver in pkgs1.items():
        if (mgr, name) not in pkgs2:
            res["packages"]["removed"].append({"manager": mgr, "name": name, "version": ver})

    # 3. Compare Environment Variables
    env1 = db.get_environment_variables(cp1["id"])
    env2 = db.get_environment_variables(cp2["id"])

    for name, val in env2.items():
        if name not in env1:
            res["env"]["added"].append({"name": name, "value": val})
        elif env1[name] != val:
            res["env"]["modified"].append({
                "name": name,
                "cp1_value": env1[name],
                "cp2_value": val
            })

    for name, val in env1.items():
        if name not in env2:
            res["env"]["removed"].append({"name": name, "value": val})

    return res

def render_diff(root_dir: str, cp1_id: str, cp2_id: str) -> str:
    """Renders a readable comparison between two checkpoints."""
    try:
        diff_data = diff_checkpoints(root_dir, cp1_id, cp2_id)
    except Exception as e:
        return str(e)

    lines = []
    lines.append(f"🔍 Phoenix Chronos - Checkpoint Diff")
    lines.append(f"Comparing checkpoint A (\033[94m{diff_data['cp1']['id']}\033[0m) -> B (\033[94m{diff_data['cp2']['id']}\033[0m)")
    lines.append("==================================================")

    # Files
    f_diff = diff_data["files"]
    if f_diff["added"] or f_diff["removed"] or f_diff["modified"]:
        lines.append("\n📁 Files:")
        for f in f_diff["added"]:
            lines.append(f"  \033[92m+ [Added]    {f}\033[0m")
        for f in f_diff["modified"]:
            lines.append(f"  \033[93m~ [Modified] {f}\033[0m")
        for f in f_diff["removed"]:
            lines.append(f"  \033[91m- [Removed]  {f}\033[0m")
    else:
        lines.append("\n📁 Files: No changes detected.")

    # Packages
    p_diff = diff_data["packages"]
    if p_diff["added"] or p_diff["removed"] or p_diff["modified"]:
        lines.append("\n📦 Packages:")
        for p in p_diff["added"]:
            lines.append(f"  \033[92m+ [{p['manager']}] {p['name']}=={p['version']}\033[0m")
        for p in p_diff["modified"]:
            lines.append(f"  \033[93m~ [{p['manager']}] {p['name']} ({p['cp1_version']} -> {p['cp2_version']})\033[0m")
        for p in p_diff["removed"]:
            lines.append(f"  \033[91m- [{p['manager']}] {p['name']}=={p['version']}\033[0m")
    else:
        lines.append("\n📦 Packages: No changes detected.")

    # Env
    e_diff = diff_data["env"]
    if e_diff["added"] or e_diff["removed"] or e_diff["modified"]:
        lines.append("\n⚙️ Environment Variables:")
        for e in e_diff["added"]:
            lines.append(f"  \033[92m+ {e['name']}={e['value']}\033[0m")
        for e in e_diff["modified"]:
            lines.append(f"  \033[93m~ {e['name']} ({e['cp1_value']} -> {e['cp2_value']})\033[0m")
        for e in e_diff["removed"]:
            lines.append(f"  \033[91m- {e['name']}={e['value']}\033[0m")
    else:
        lines.append("\n⚙️ Environment Variables: No changes detected.")

    return "\n".join(lines)
