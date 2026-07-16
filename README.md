<div align="center">

# 🔥 Phoenix Chronos

### *The Open-Source Checkpoint & Replay Engine for Developers*

*"Git tracks your code. Phoenix Chronos tracks your environment."*

[![GitHub Stars](https://img.shields.io/badge/GitHub-Stars-yellow?style=for-the-badge&logo=github)](https://github.com)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Termux%20%7C%20macOS-green?style=for-the-badge)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.12+-blue?style=for-the-badge&logo=python)](https://python.org)

---

**Every developer knows this nightmare:**
*"Everything worked yesterday. Now, a dependency updated, an environment variable changed, or a config was overwritten, and the build is broken. I've spent 4 hours trying to get back to my working state."*

**Phoenix Chronos solves this forever.** It takes zero-friction, lightweight development environment checkpoints, allowing you to restore your exact files, dependencies, environment variables, and git state in seconds.

[🚀 Quick Start](#-quick-start) • [✨ Key Features](#-key-features) • [⚙️ Architecture](#️-architecture) • [📖 CLI Usage](#-cli-usage) • [🤝 Contributing](#-contributing)

</div>

---

## ⚡ What does Chronos Track?

```
📦 Phoenix Chronos Checkpoint
├── 📁 Project Files (Excluding ignored build/venv artifacts)
├── 📦 Package Dependencies (Pip, NPM, Cargo, Go)
├── ⚙️ Environment Variables (PATH, GOROOT, JAVA_HOME, and custom rules)
└── 🐙 Git Repository State (Commit hash, branch name, working tree status)
```

---

## 🚀 Quick Start

### 1. Installation

Install Phoenix Chronos directly from source:

```bash
git clone https://github.com/devthedevil2321-create/phoenix-chronos.git
cd phoenix-chronos
pip install -e .
```

---

### 2. Initialize Chronos in your project

Run `chronos init` inside any directory to set up environment tracking. This creates a lightweight `.chronos` database and configuration file.

```bash
$ chronos init
```
*Output:*
> `Initialized empty Chronos repository in /path/to/project/.chronos`

---

### 3. Create a Checkpoint

Whenever your project is in a working state, take a snapshot!

```bash
$ chronos checkpoint -m "Working state with requests library added"
```
*Output:*
> `Successfully created checkpoint: cp_20231024153022_b3d4f109`

---

### 4. Check Status

Chronos monitors files, environment variables, and packages in real-time, highlighting exact deviations from your last checkpoint.

```bash
$ chronos status
```
*Output:*
```text
🔍 Phoenix Chronos - Dev Environment Status
==========================================
Latest Checkpoint: cp_20231024153022_b3d4f109 ("Working state with requests library added")
Git State: branch=main commit=f4a2b91
------------------------------------------

📁 File Status:
  ~ [Modified]  src/main.py
  + [Untracked] test_new_feature.py

📦 Package Status:
  + [pip] pytest==7.4.3

⚙️ Environment Variables Status:
  ~ PATH (Checkpoint: /usr/bin -> Local: /tmp/untrusted/bin:/usr/bin)
```

---

### 5. Compare History

See what changed between two different checkpoints:

```bash
$ chronos diff cp_20231024153022_b3d4f109 cp_20231024164511_a9f23d41
```

---

### 6. Replay & Restore

Did a dependency break your app? Easily restore your exact files to a previous checkpoint. Chronos will automatically output a **Restore Plan** to guide your package and environment alignment!

```bash
$ chronos restore cp_20231024153022_b3d4f109
```
*Output:*
```text
📋 PHOENIX CHRONOS RESTORE PLAN
================================
Target Checkpoint: cp_20231024153022_b3d4f109
Message:           "Working state with requests library added"
Timestamp:         2023-10-24 15:30:22
--------------------------------

📁 Files to update:
  ~ [Modified] src/main.py
  - [Delete]   test_new_feature.py

📦 Package Alignment Actions Required:
  [Install] pip: requests==2.31.0

⚙️ Environment Variables Alignment Required:
  [Update] PATH (/tmp/untrusted/bin:/usr/bin -> /usr/bin)

Successfully restored workspace files to checkpoint: cp_20231024153022_b3d4f109
Please align your system packages and environment variables as printed above.
```

---

## 🛠️ Configuration (`.chronos/config.json`)

Phoenix Chronos is highly customizable. After running `chronos init`, you can customize `.chronos/config.json`:

```json
{
    "include": [
        "**/*"
    ],
    "exclude": [
        "**/.git/**",
        "**/.chronos/**",
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/*.pyc",
        "**/.venv/**"
    ],
    "environment_variables": [
        "PATH",
        "PYTHONPATH",
        "NODE_ENV"
    ],
    "commands": {
        "pre_checkpoint": "pytest tests/",
        "post_checkpoint": "echo 'Checkpoint taken successfully!'",
        "pre_restore": "",
        "post_restore": ""
    }
}
```

- **pre_checkpoint**: Run verification commands (e.g. tests) that must pass before taking a checkpoint.
- **post_checkpoint**: Fire off custom webhooks or log events.

---

## 🏗️ Architecture

```
                       ┌─────────────────────────┐
                       │       Chronos CLI       │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │     Restore Planner     │
                       └────────────┬────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  SQLite DB   │             │ Snapshot Zip │             │ Env Adapters │
│ (Metadata)   │             │  (Archives)  │             │ (Pip/NPM/Go) │
└──────────────┘             └──────────────┘             └──────────────┘
```

---

## 🕒 Timeline

Easily browse your development checkpoints:

```bash
$ chronos timeline
```
```text
🕒 Phoenix Chronos - Development History Timeline
==================================================
 🔥 (latest)  ID: cp_20231024164511_a9f23d41
 │   Time:    2023-10-24 16:45:11
 │   Git:      [main] (f4a2b91)
 │   Message: Broken experiment with experimental packages
 │
 ●  ID: cp_20231024153022_b3d4f109
     Time:    2023-10-24 15:30:22
     Git:      [main] (e1c9a82)
     Message: Working state with requests library added
```

---

## 🤝 Contributing

Contributions are extremely welcome! If you'd like to help build the future of reproducible development environments, please feel free to submit issues, pull requests, or suggestions.

Let's make local development reliable and fun! 🚀

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
