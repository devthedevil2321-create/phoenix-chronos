<div align="center">

# 🔥 Phoenix Chronos

### *The Open-Source Checkpoint & Replay Engine for Developers*

*"Checkpoint your development environment. Restore it when things go wrong."*

[![License](https://img.shields.io/badge/license-Apache2.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Termux-green)](#)
[![Status](https://img.shields.io/badge/status-Pre--Alpha-orange)](#)
[![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python)](https://python.org)

---

**Every developer has experienced this.**
> *"Everything worked yesterday."*

Then suddenly:
* ❌ A package update breaks the project.
* ❌ An environment variable changes.
* ❌ A dependency conflict appears.
* ❌ A toolchain upgrade causes failures.
* ❌ A configuration file is accidentally modified.
* ❌ Hours are spent trying to return to the last working state.

Git remembers your code.
**Phoenix Chronos aims to remember your development environment.**

</div>

---

# 🚀 Why Phoenix Chronos?

Phoenix Chronos is an open-source project exploring a new idea:

> **Checkpoint your development environment and restore a reproducible working state when something goes wrong.**

Instead of only tracking source code, Chronos captures the broader development context:
* 📂 Project files
* 📦 Package versions (pip, npm, cargo, go)
* ⚙️ Environment variables (sanitized & tracked)
* 🐙 Git repository state
* 🧪 Build outputs, command validations, and test results

---

# ✨ Core Features

## 📸 1. Development Checkpoints
```bash
chronos checkpoint -m "Installed experimental package"
```
Save a robust snapshot of your entire workspace, files, and dependencies instantly.

---

## 🔄 2. Restore Workspace
```bash
chronos restore latest
```
Restore the latest reproducible checkpoint, with an automatically computed **Restore Plan** for packages and environment variables.

---

## 📜 3. History Timeline
```bash
chronos timeline
```
Browse your development checkpoints and visual timeline.

---

## 🔍 4. Diff Changes
```bash
chronos diff checkpoint-1 checkpoint-2
```
Instantly see file, package, and environment changes between two checkpoints.

---

## 📊 5. Workspace Status
```bash
chronos status
```
Inspect real-time deviations from the latest checkpoint (modified, untracked, and missing files).

---

# 🏗️ Architecture

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

# 🤝 Contributing

Contributions are welcome! Please open an issue before starting major changes so we can discuss the design.

Let's make local development reliable and fun! 🚀

---

# 📄 License

Licensed under the Apache 2.0 License.
