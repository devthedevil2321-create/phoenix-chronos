import os
import json

DEFAULT_CONFIG = {
    "include": [
        "**/*"
    ],
    "exclude": [
        "**/.git/**",
        "**/.chronos/**",
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/*.pyc",
        "**/.venv/**",
        "**/venv/**",
        "**/target/**",
        "**/.gradle/**",
        "**/.idea/**",
        "**/.vscode/**"
    ],
    "environment_variables": [
        "PATH",
        "PYTHONPATH",
        "NODE_ENV",
        "JAVA_HOME",
        "GOROOT",
        "GOPATH"
    ],
    "commands": {
        "pre_checkpoint": "",
        "post_checkpoint": "",
        "pre_restore": "",
        "post_restore": ""
    }
}

class ConfigManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.chronos_dir = os.path.join(root_dir, ".chronos")
        self.config_path = os.path.join(self.chronos_dir, "config.json")

    def initialize(self):
        if not os.path.exists(self.chronos_dir):
            os.makedirs(self.chronos_dir, exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)

    def load(self) -> dict:
        if not os.path.exists(self.config_path):
            return DEFAULT_CONFIG
        try:
            with open(self.config_path, "r") as f:
                user_config = json.load(f)
                # Merge user config with DEFAULT_CONFIG to ensure all keys are present
                config = DEFAULT_CONFIG.copy()
                for key, val in user_config.items():
                    if isinstance(val, dict) and key in config:
                        config[key] = {**config[key], **val}
                    else:
                        config[key] = val
                return config
        except Exception:
            return DEFAULT_CONFIG

    def save(self, config: dict):
        if not os.path.exists(self.chronos_dir):
            os.makedirs(self.chronos_dir, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)
