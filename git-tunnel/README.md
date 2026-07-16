# 🚀 git-tunnel

### *High-Performance, Minimal-Dependency P2P Developer Collaboration Utility*

[![Go Version](https://img.shields.io/badge/Go-1.24+-blue.svg?style=for-the-badge&logo=go)](https://golang.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-green.svg?style=for-the-badge)](https://github.com/devthedevil2321-create/git-tunnel)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![GitHub Stars](https://img.shields.io/badge/GitHub-Stars-yellow.svg?style=for-the-badge&logo=github)](https://github.com/devthedevil2321-create/git-tunnel)

---

**`git-tunnel`** is an elite, systems-level developer collaboration utility designed for high-performance pairing, terminal sharing, clipboard syncing, and sandboxed repository replication over P2P WebRTC channels.

With zero external runtime dependencies, `git-tunnel` integrates a Star-topology coordinator, tiered memory buffer pooling, robust state machines, and cryptographically verified human-readable word fingerprints to satisfy strict infrastructure security standards.

---

## ⚡ Key Architectural Highlights

### 1. Channel-Multiplexed WebRTC Architecture
`git-tunnel` multiplexes its session stream into independent application data channels:
*   📟 **Terminal**: Low-latency interactive bash/sh shells with dynamic sizing stream updates (`SIGWINCH`).
*   📋 **Clipboard**: Versioned, MIME-aware cross-node text payload synchronization.
*   📂 **FileSync**: Cryptographically sandboxed, remote repository tracking and reconciliation.
*   🌐 **HTTPTunnel**: On-demand port forwarding for instant web preview sharing (localhost forwarding).
*   📊 **Metrics**: Live networking telemetry and stream latency reporting.

### 2. Tiered Buffer Pooling (`sync.Pool`)
To maximize throughput and prevent garbage collection (GC) pauses under heavy transfers, memory allocation is restricted exclusively to common chunk pools (4KB, 16KB, 64KB) utilizing `sync.Pool`. This blocks unbounded allocation memory leaks completely.

### 3. Human-Verifiable Word Fingerprints
Ditch long, unreadable raw SHA-256 certificate hex strings. `git-tunnel` hashes session secrets into a memorable 4-word sequence (e.g., `"Titan Falcon Forest Cascade"`) for simple, secure manual verification coupled with real-time peer approval prompt loops.

### 4. Deep Sandboxing Denylist
An active, built-in directory-traversal-resistant credentials scanner completely blocks access to sensitive local structures (`.env`, `id_rsa`, `.pem`, `aws_credentials`) regardless of what is declared in `.gitignore`. It recursively supports nested Git worktrees and submodules.

### 5. Multi-Phase State Machine Recovery
The utility runs an advanced connection engine to survive real-world network outages:
`Disconnected` ➔ `ICE Restart` ➔ `Reconnecting` ➔ `Recreated` ➔ `Streams Restored`.

---

## 🚀 CLI Commands & Interactive Usage

### 🛠️ 1. Installation

Build the binary directly with Go:

```bash
git clone https://github.com/devthedevil2321-create/git-tunnel.git
cd git-tunnel
go build -o git-tunnel ./cmd/git-tunnel/main.go
```

---

### 🔑 2. Start Hosting a Session

Instantiate a Star-topology coordinator with interactive peer authorization prompts enabled:

```bash
$ ./git-tunnel host --port 8080
```
*Output:*
```text
🔒 Initializing Git-Tunnel Host Coordinator...
🔑 Verifiable Fingerprint Word Sequence: "Titan Falcon Forest Cascade"
📡 Starting Star-topology network hub on port 8080...
⚡ Network coordinator online. Multi-peer signaling relay ready.

🛡️  Interactive Peer approval prompt triggers online.
👉 Listening for peer requests... Run 'join' on another node to pair.
```

When a peer requests to pair, the coordinator triggers an interactive security prompt:
```text
🔔  PROMPT: Incoming peer connection request from "p1_8f".
👉 Do you authorize this peer connection? [Y/n]:
```

---

### 🔗 3. Joining an Active Session

Connect to the coordinator and verify identity via the word sequence sequence:

```bash
$ ./git-tunnel join --host localhost:8080 --fingerprint "Titan Falcon Forest Cascade"
```
*Output:*
```text
🔗 Attempting secure handshake with localhost:8080...
🔍 Verifying fingerprint sequence: "Titan Falcon Forest Cascade"
⏳ Waiting for peer authorization prompt approval...
✅ Secure handshake finalized! Channels successfully multiplexed.
```

---

### 🛡️ 4. Local Status and Secrets Sandboxing

Check the active sandboxing constraints of your workspace folder:

```bash
$ ./git-tunnel status
```
*Output:*
```text
📁 Checking local sandboxing constraints for: .

🚫 Sandboxing Secrets Denylist Test:
------------------------------------
  • File: .env               -> BLOCKED (DENYLISTED)
  • File: id_rsa             -> BLOCKED (DENYLISTED)
  • File: aws_credentials    -> BLOCKED (DENYLISTED)
  • File: private.pem        -> BLOCKED (DENYLISTED)

✅ Sandboxing verified. Nested Git worktrees & submodules checked recursively.
```

---

### 📊 5. live Telemetry & Allocations

View active multiplexed channels and tiered buffer allocation metrics:

```bash
$ ./git-tunnel stats
```
*Output:*
```text
📊 Git-Tunnel Real-Time Network Transmission Telemetry
=====================================================
📡 Active Channels Multiplexed:
  • Terminal Channel  : Online (Active multiplexed)
  • Clipboard Channel : Online (Active multiplexed)
  • FileSync Channel  : Online (Active multiplexed)
  • HTTPTunnel Channel: Online (Active multiplexed)
  • Metrics Channel   : Online (Active multiplexed)

💾 Tiered Buffer Pooling Telemetry (sync.Pool):
  • 4KB Pool Allocations  : 124 allocations
  • 16KB Pool Allocations : 45 allocations
  • 64KB Pool Allocations : 12 allocations
  • Total Buffer Reuse    : 1823 transactions recycled
```

---

## 📂 Project Directory Structure

```
.
├── cmd/
│   └── git-tunnel/
│       └── main.go           # CLI Entry Point, flag-parsing & telemetry plumbing
├── pkg/
│   ├── session/
│   │   ├── coordinator.go    # Star Coordinator, sync.Pools, word fingerprints, sandbox
│   │   └── coordinator_test.go # Comprehensive unit tests
│   └── webrtc/
│       └── state.go          # Connection State Machine & ICE recovery logic
├── go.mod
└── README.md
```

---

## 🤝 Contributing

We welcome pull requests and issues! For major architectural changes, please open an issue first to discuss your design proposal.

Let's make decentralized, P2P developer collaboration secure, fast, and accessible! 🚀

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
