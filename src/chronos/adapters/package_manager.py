import os
import json
import re

class PackageManagerAdapter:
    """Base adapter for detecting and reading package versions."""
    def detect(self, root_dir: str) -> bool:
        raise NotImplementedError

    def get_packages(self, root_dir: str) -> list[tuple[str, str]]:
        """Returns list of tuples: (package_name, version)"""
        raise NotImplementedError

class PipAdapter(PackageManagerAdapter):
    def detect(self, root_dir: str) -> bool:
        # Check requirements.txt or pipfile or pyproject.toml
        return (os.path.exists(os.path.join(root_dir, "requirements.txt")) or
                os.path.exists(os.path.join(root_dir, "pyproject.toml")))

    def get_packages(self, root_dir: str) -> list[tuple[str, str]]:
        packages = []
        req_path = os.path.join(root_dir, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Match packages like package==1.2.3 or package>=1.2.3
                    match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)\s*==\s*([a-zA-Z0-9_\-\.\+]+)", line)
                    if match:
                        packages.append((match.group(1), match.group(2)))
                    else:
                        match_approx = re.match(r"^([a-zA-Z0-9_\-\[\]]+)", line)
                        if match_approx:
                            packages.append((match_approx.group(1), "any"))

        # Also let's try using pip list if we can execute, but to be safe and portable,
        # we can check sys/importlib or local packages. Let's do a quick fallback check
        # using requirements.txt parser mainly. Let's keep it robust.
        return list(set(packages))

class NpmAdapter(PackageManagerAdapter):
    def detect(self, root_dir: str) -> bool:
        return os.path.exists(os.path.join(root_dir, "package.json"))

    def get_packages(self, root_dir: str) -> list[tuple[str, str]]:
        packages = []
        pkg_path = os.path.join(root_dir, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    dependencies = data.get("dependencies", {})
                    devDependencies = data.get("devDependencies", {})
                    for name, ver in {**dependencies, **devDependencies}.items():
                        # Clean version strings like ^1.2.3, ~1.2.3
                        ver_clean = ver.lstrip("^~>=")
                        packages.append((name, ver_clean))
            except Exception:
                pass
        return packages

class CargoAdapter(PackageManagerAdapter):
    def detect(self, root_dir: str) -> bool:
        return os.path.exists(os.path.join(root_dir, "Cargo.toml"))

    def get_packages(self, root_dir: str) -> list[tuple[str, str]]:
        packages = []
        cargo_path = os.path.join(root_dir, "Cargo.toml")
        if os.path.exists(cargo_path):
            # Parse dependency lines in Cargo.toml manually to avoid requiring non-standard libraries
            # This is robust enough for typical Cargo.toml files
            try:
                with open(cargo_path, "r", encoding="utf-8") as f:
                    in_deps = False
                    for line in f:
                        line = line.strip()
                        if line.startswith("[dependencies]") or line.startswith("[dev-dependencies]"):
                            in_deps = True
                            continue
                        elif line.startswith("[") and in_deps:
                            in_deps = False

                        if in_deps and "=" in line:
                            parts = line.split("=")
                            name = parts[0].strip().strip('"')
                            val = parts[1].strip().strip('"')
                            # Handle complex dependency specifications like: package = { version = "1.0" }
                            if "version" in val:
                                v_match = re.search(r'version\s*=\s*"([^"]+)"', val)
                                if v_match:
                                    val = v_match.group(1)
                            val = val.strip('"{} ')
                            packages.append((name, val))
            except Exception:
                pass
        return packages

class GoAdapter(PackageManagerAdapter):
    def detect(self, root_dir: str) -> bool:
        return os.path.exists(os.path.join(root_dir, "go.mod"))

    def get_packages(self, root_dir: str) -> list[tuple[str, str]]:
        packages = []
        go_mod_path = os.path.join(root_dir, "go.mod")
        if os.path.exists(go_mod_path):
            try:
                with open(go_mod_path, "r", encoding="utf-8") as f:
                    in_require = False
                    for line in f:
                        line = line.strip()
                        if line.startswith("require ("):
                            in_require = True
                            continue
                        elif line.startswith(")") and in_require:
                            in_require = False

                        if in_require:
                            parts = line.split()
                            if len(parts) >= 2:
                                packages.append((parts[0], parts[1]))
                        elif line.startswith("require") and not line.startswith("require ("):
                            parts = line.split()
                            if len(parts) >= 3:
                                packages.append((parts[1], parts[2]))
            except Exception:
                pass
        return packages

ADAPTERS = {
    "pip": PipAdapter(),
    "npm": NpmAdapter(),
    "cargo": CargoAdapter(),
    "go": GoAdapter()
}

def get_installed_packages(root_dir: str) -> list[tuple[str, str, str]]:
    """Returns a list of (manager_name, package_name, version) for detected environments."""
    all_packages = []
    for mgr, adapter in ADAPTERS.items():
        if adapter.detect(root_dir):
            for name, ver in adapter.get_packages(root_dir):
                all_packages.append((mgr, name, ver))
    return all_packages
