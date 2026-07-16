import os
import hashlib
import fnmatch
import zipfile
import subprocess
from datetime import datetime
from chronos.core.db import DB
from chronos.core.config import ConfigManager
from chronos.core.environment import get_git_state, collect_environment
from chronos.adapters.package_manager import get_installed_packages

def get_chronos_dir(root_dir: str) -> str:
    return os.path.join(root_dir, ".chronos")

def get_db_path(root_dir: str) -> str:
    return os.path.join(get_chronos_dir(root_dir), "chronos.db")

def init_chronos(root_dir: str) -> str:
    """Initializes the Chronos project."""
    chronos_dir = get_chronos_dir(root_dir)
    os.makedirs(chronos_dir, exist_ok=True)
    os.makedirs(os.path.join(chronos_dir, "snapshots"), exist_ok=True)

    # Init config
    config_mgr = ConfigManager(root_dir)
    config_mgr.initialize()

    # Init database
    db_path = get_db_path(root_dir)
    DB(db_path)

    # Append .chronos to .gitignore if not present
    gitignore_path = os.path.join(root_dir, ".gitignore")
    lines = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    has_chronos_ignore = any(line.strip() == ".chronos/" or line.strip() == ".chronos" for line in lines)
    if not has_chronos_ignore:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if lines and not lines[-1].endswith("\n"):
                f.write("\n")
            f.write("# Chronos environment database and snapshots\n.chronos/\n")

    return f"Initialized empty Chronos repository in {chronos_dir}"

def calculate_sha256(filepath: str) -> str:
    """Calculates SHA256 of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return ""

def matches_pattern(filepath: str, patterns: list) -> bool:
    """Checks if filepath matches any pattern in glob patterns list."""
    filepath_normalized = filepath.replace(os.sep, "/").strip("/")
    path_segments = filepath_normalized.split("/")

    # Check common ignores based on path segment matching
    # This is highly robust and handles folders like .git, .chronos, node_modules, etc.
    ignore_names = {".git", ".chronos", "node_modules", "__pycache__", ".venv", "venv", "target", ".gradle", ".idea", ".vscode"}
    for segment in path_segments:
        if segment in ignore_names:
            return True

    # Standard fnmatch for specific globs or user include patterns
    for pattern in patterns:
        pattern_normalized = pattern.replace(os.sep, "/").strip("/")

        # Exact or direct wildcard match
        if fnmatch.fnmatch(filepath_normalized, pattern_normalized):
            return True

        # Handle double wildcards robustly
        if "**" in pattern_normalized:
            # e.g., "**/*" or "**/*.py"
            # Try matching with **/ replaced with * (for nested files)
            if fnmatch.fnmatch(filepath_normalized, pattern_normalized.replace("**/", "*")):
                return True
            # Try matching with **/ removed (for root files)
            if fnmatch.fnmatch(filepath_normalized, pattern_normalized.replace("**/", "")):
                return True
            # Try matching with /** removed (for prefix matching of directories)
            if fnmatch.fnmatch(filepath_normalized, pattern_normalized.replace("/**", "")):
                return True
            if fnmatch.fnmatch(filepath_normalized, pattern_normalized.replace("/**", "/*")):
                return True

    return False

def get_tracked_files_list(root_dir: str, config: dict) -> list[str]:
    """Returns absolute paths of all tracked files based on config include/exclude."""
    included_files = []
    includes = config.get("include", ["**/*"])
    excludes = config.get("exclude", [])

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Determine relative directory path
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = ""

        # Prune excluded directories to avoid walking them at all
        prune_dirs = []
        for d in dirnames:
            rel_d = os.path.join(rel_dir, d) if rel_dir else d
            if matches_pattern(rel_d, excludes):
                prune_dirs.append(d)
        for d in prune_dirs:
            dirnames.remove(d)

        for f in filenames:
            rel_file = os.path.join(rel_dir, f) if rel_dir else f

            # Skip if matches excludes
            if matches_pattern(rel_file, excludes):
                continue

            # Check if matches any includes
            if matches_pattern(rel_file, includes):
                included_files.append(os.path.join(dirpath, f))

    return included_files

def create_checkpoint(root_dir: str, message: str) -> str:
    """Creates a new checkpoint of the development state."""
    db_path = get_db_path(root_dir)
    if not os.path.exists(db_path):
        raise ValueError("Chronos repository not initialized. Run 'chronos init' first.")

    db = DB(db_path)
    config_mgr = ConfigManager(root_dir)
    config = config_mgr.load()

    # Pre-checkpoint command
    pre_cmd = config.get("commands", {}).get("pre_checkpoint", "")
    if pre_cmd:
        print(f"Running pre-checkpoint command: {pre_cmd}")
        subprocess.run(pre_cmd, shell=True, cwd=root_dir)

    # 1. Gather git, env, and packages metadata
    git_state = get_git_state(root_dir)
    env_vars = collect_environment(config)
    packages = get_installed_packages(root_dir)

    # 2. Track files and compute hashes
    tracked_filepaths = get_tracked_files_list(root_dir, config)
    tracked_files_metadata = []

    # Generate unique ID for checkpoint
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
    import uuid
    short_uuid = uuid.uuid4().hex[:8]
    checkpoint_id = f"cp_{timestamp_str}_{short_uuid}"

    # Zip snapshot setup
    snapshot_filename = f"{checkpoint_id}.zip"
    snapshot_path = os.path.join(get_chronos_dir(root_dir), "snapshots", snapshot_filename)

    with zipfile.ZipFile(snapshot_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filepath in tracked_filepaths:
            rel_path = os.path.relpath(filepath, root_dir)
            sha256 = calculate_sha256(filepath)
            stat = os.stat(filepath)

            tracked_files_metadata.append((rel_path, sha256, stat.st_size, stat.st_mtime))
            # Write to snapshot zip
            zipf.write(filepath, rel_path)

    # Save to SQLite DB
    db.create_checkpoint(
        checkpoint_id=checkpoint_id,
        message=message,
        git_commit=git_state["commit"],
        git_branch=git_state["branch"],
        git_status=git_state["status"],
        snapshot_path=os.path.join(".chronos", "snapshots", snapshot_filename)
    )
    db.add_environment_variables(checkpoint_id, env_vars)
    db.add_packages(checkpoint_id, packages)
    db.add_tracked_files(checkpoint_id, tracked_files_metadata)

    # Post-checkpoint command
    post_cmd = config.get("commands", {}).get("post_checkpoint", "")
    if post_cmd:
        print(f"Running post-checkpoint command: {post_cmd}")
        subprocess.run(post_cmd, shell=True, cwd=root_dir)

    return checkpoint_id
