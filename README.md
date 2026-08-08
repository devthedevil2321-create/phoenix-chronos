<div align="center">

# 👻 GhostLink

### *God-Mode, Military-Grade Private Chat*

*"Git tracks your code. GhostLink tracks nothing — and that is its ultimate power."*

[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-green?style=for-the-badge)](https://github.com)
[![WebCrypto API](https://img.shields.io/badge/WebCrypto-Native-orange?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)
[![Node.js](https://img.shields.io/badge/node-v22+-blue?style=for-the-badge)](https://nodejs.org)

---

**Every user knows the modern nightmare:**
*"Every chat app wants my email, phone number, and contacts. Their databases leak, their servers get breached, and my private conversations are sold to the highest bidder."*

**GhostLink solves this forever.** Built on a zero-trust architecture, GhostLink operates completely in-memory, uses peer-to-peer WebRTC connections, and protects every packet with standard Double Ratchet end-to-end encryption. No accounts. No databases. No permanent identity.

[⚡ Architecture Core](#-architecture-core) • [🚀 Quick Start](#-quick-start) • [🛡️ Trust Verification](#️-trust-verification) • [🧪 Testing](#-testing) • [📦 Hardened Policies](#-hardened-policies)

</div>

---

## ⚡ Architecture Core

```
📦 GhostLink Security Layers
├── 🔐 Sovereign Keys (X25519 DH / Ed25519 Signatures generated locally)
├── 🤝 Initial Handshake (X3DH-like Authenticated Key Exchange over WebSocket)
├── 🔄 Ongoing Session (Double Ratchet DH + Symmetric KDF message-key rotation)
├── 📦 Authenticated Encryption (AES-256-GCM AEAD — tampering is rejected natively)
└── 📡 Signaling (Sealed-sender style routing using ephemeral session tokens)
```

---

## 🚀 Quick Start

### 1. Installation

Install GhostLink and its lightweight, zero-persistence signaling dependencies:

```bash
git clone https://github.com/devthedevil2321-create/ghostlink.git
cd ghostlink
npm install
```

---

### 2. Launch the Signaling Server

Start the lightweight, zero-log WebSocket signaling server:

```bash
npm start
```
*Output:*
> `🔥 GhostLink Signaling Server running on port 3000`
> `Visit http://localhost:3000 in your browser to start secure, private chats.`

---

### 3. Establish a Private Handshake

1. Open **two independent browser windows** at `http://localhost:3000` (representing Alice and Bob).
2. On Alice's client, click **Generate Invitation** to craft a single-use handshake token.
3. Copy the token and paste it into Bob's client under **Accept Friend's Code**.
4. Click **Accept Invitation**.
5. The clients will perform an **X3DH-like handshake** over the sealed-sender signaling server, automatically derive a byte-identical master secret, initialize the **Double Ratchet Engine**, and establish a direct **WebRTC DataChannel** in relay-only mode.

---

## 🛡️ Trust Verification

GhostLink handles trust verification out-of-band to completely eliminate Man-in-the-Middle (MitM) impersonation:

1. Click **Verify Trust** at the top right of the active workspace.
2. Compare the **Short Authentication String (SAS)** printed on both clients.
3. If they match, click **Verify Trust** to pin the identity signature of your peer.

---

## ⚙️ Configuration & Hardened Defaults

GhostLink is hardened at both the protocol and application layers:
- **No Persistence**: No database ever touches message contents or signaling envelopes. State is 100% in-memory and wiped on exit.
- **Relay-Only WebRTC**: Configured with `iceTransportPolicy: 'relay'` to prevent public IP leaks, routing exclusively via TURN relays.
- **Disappearing Messages**: Features 1-minute, 5-minute, or customizable automatic local memory/DOM wipeout.
- **Self-Destruct**: Clicking "Self-Destruct" instantly overwrites and purges private keys, active session states, local logs, and reloads to a clean, fresh state.
- **Content Security Policy (CSP)**: Injected with strict headers to prevent inline JS execution, cross-site scripting (XSS), or unauthorized network calls.

---

## 🧪 Testing

To run the automated cryptographic test suite and verify the integrity of the X25519 DH, HKDF-SHA256, Double Ratchet, and AES-256-GCM pipelines:

```bash
npm test
```

*Expected Output:*
```text
🧪 Starting GhostLink Cryptographic & Protocol Tests...

▶ Test 1: Key Generation...
✓ Key Generation test passed successfully.

▶ Test 2: Ephemeral Diffie-Hellman Key Agreement...
✓ X25519 DH Key Agreement passed successfully.

▶ Test 3: HKDF KDF Chain Derivation...
✓ HKDF KDF Chain Derivation passed successfully.

▶ Test 4: Double Ratchet State Machine & Rotations...
✓ Double Ratchet encryption & decryption passed successfully.
✓ Double Ratchet symmetric KDF-chain rotation passed successfully.

▶ Test 5: Cryptographic Tamper & Integrity Rejection...
✓ Cryptographic Tamper Rejection verified successfully.

🏁 ALL GHOSTLINK PROTOCOL & CRYPTO TESTS PASSED SUCCESSFULLY! 🚀
```

---

Made with ❤️ by Dev
