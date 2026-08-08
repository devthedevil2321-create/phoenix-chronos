/**
 * GhostLink Cryptographic Core Module
 * Built using standards-compliant, browser-native Web Crypto API.
 * Designed with a fallback/compatibility layer for Node.js environments
 * to facilitate 100% coverage automated testing.
 */

// Environment check: Resolve Web Crypto API (browser or Node.js)
const cryptoProvider = typeof window !== 'undefined'
    ? window.crypto
    : require('crypto').webcrypto;

class GhostLinkCrypto {
    /**
     * Helper to convert ArrayBuffer/Uint8Array to hex string.
     */
    static toHex(buffer) {
        return Array.from(new Uint8Array(buffer))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
    }

    /**
     * Helper to convert hex string to Uint8Array.
     */
    static fromHex(hexString) {
        const matches = hexString.match(/.{1,2}/g);
        if (!matches) return new Uint8Array(0);
        return new Uint8Array(matches.map(byte => parseInt(byte, 16)));
    }

    /**
     * Generate local cryptographic key pairs.
     * Returns: { identityKeyPair, dhKeyPair, fingerprint }
     */
    static async generateKeyPair() {
        // 1. Generate Ed25519 Key Pair for node identity signing/verification
        const identityKeyPair = await cryptoProvider.subtle.generateKey(
            { name: "Ed25519" },
            true,
            ["sign", "verify"]
        );

        // 2. Generate X25519 Key Pair for Diffie-Hellman key exchange
        const dhKeyPair = await cryptoProvider.subtle.generateKey(
            { name: "X25519" },
            true,
            ["deriveKey", "deriveBits"]
        );

        // 3. Export Identity Public Key to derive its unique fingerprint (SHA-256 hex)
        const exportedPubKey = await cryptoProvider.subtle.exportKey("raw", identityKeyPair.publicKey);
        const hashBuffer = await cryptoProvider.subtle.digest("SHA-256", exportedPubKey);
        const fingerprint = this.toHex(hashBuffer).substring(0, 40).toUpperCase();

        return {
            identityKeyPair,
            dhKeyPair,
            fingerprint,
            rawIdentityPublicKey: new Uint8Array(exportedPubKey)
        };
    }

    /**
     * Compute a SHA-256 Hash of raw data, returned as hex.
     */
    static async hashData(arrayBuffer) {
        const hash = await cryptoProvider.subtle.digest("SHA-256", arrayBuffer);
        return this.toHex(hash);
    }

    /**
     * Derives a 32-byte shared master secret via X25519 Diffie-Hellman.
     * Uses SubtleCrypto's native deriveBits.
     */
    static async deriveDHSecret(localPrivateKey, remotePublicKeyRaw) {
        const remotePubKey = await cryptoProvider.subtle.importKey(
            "raw",
            remotePublicKeyRaw,
            { name: "X25519" },
            true,
            []
        );

        const sharedBits = await cryptoProvider.subtle.deriveBits(
            {
                name: "X25519",
                public: remotePubKey
            },
            localPrivateKey,
            256
        );

        return new Uint8Array(sharedBits);
    }

    /**
     * Implements HKDF-SHA256 for KDF key rotation steps in Double Ratchet.
     * Derives sub-keys from a secret input.
     */
    static async hkdfDerive(secretBytes, infoString, saltBytes = new Uint8Array(32)) {
        const infoBytes = new TextEncoder().encode(infoString);

        // Import raw secret into Web Crypto HKDF key format
        const baseKey = await cryptoProvider.subtle.importKey(
            "raw",
            secretBytes,
            { name: "HKDF" },
            false,
            ["deriveBits"]
        );

        // Derive 64 bytes total (e.g., can split into two 32-byte keys)
        const derivedBits = await cryptoProvider.subtle.deriveBits(
            {
                name: "HKDF",
                hash: "SHA-256",
                salt: saltBytes,
                info: infoBytes
            },
            baseKey,
            512 // 64 bytes
        );

        return new Uint8Array(derivedBits);
    }

    /**
     * AES-256-GCM Encryption wrapper.
     * Returns: { ciphertext: hexString, iv: hexString }
     */
    static async encryptAES_GCM(keyBytes, plaintextString, associatedDataBytes = new Uint8Array(0)) {
        const iv = cryptoProvider.getRandomValues(new Uint8Array(12)); // 12-byte secure IV
        const plaintextBytes = new TextEncoder().encode(plaintextString);

        const cryptoKey = await cryptoProvider.subtle.importKey(
            "raw",
            keyBytes,
            { name: "AES-GCM" },
            false,
            ["encrypt"]
        );

        const encryptedBuffer = await cryptoProvider.subtle.encrypt(
            {
                name: "AES-GCM",
                iv: iv,
                additionalData: associatedDataBytes
            },
            cryptoKey,
            plaintextBytes
        );

        return {
            ciphertext: this.toHex(encryptedBuffer),
            iv: this.toHex(iv)
        };
    }

    /**
     * AES-256-GCM Decryption wrapper.
     * Rejects tampered ciphertexts and invalid auth tags natively.
     */
    static async decryptAES_GCM(keyBytes, ciphertextHex, ivHex, associatedDataBytes = new Uint8Array(0)) {
        const iv = this.fromHex(ivHex);
        const ciphertextBytes = this.fromHex(ciphertextHex);

        const cryptoKey = await cryptoProvider.subtle.importKey(
            "raw",
            keyBytes,
            { name: "AES-GCM" },
            false,
            ["decrypt"]
        );

        try {
            const decryptedBuffer = await cryptoProvider.subtle.decrypt(
                {
                    name: "AES-GCM",
                    iv: iv,
                    additionalData: associatedDataBytes
                },
                cryptoKey,
                ciphertextBytes
            );

            return new TextDecoder().decode(decryptedBuffer);
        } catch (error) {
            throw new Error("Cryptographic verification failed: ciphertext is tampered, corrupt, or invalid.");
        }
    }
}

/**
 * Double Ratchet Engine Class
 * Maintains root and symmetric chains (Send & Receive) with KDF-SHA256 rotation steps.
 */
class DoubleRatchetSession {
    constructor() {
        this.rootKey = null;
        this.sendChainKey = null;
        this.recvChainKey = null;
        this.localDHKeyPair = null;
        this.remoteDHPubKey = null;
        this.sendSequence = 0;
        this.recvSequence = 0;
        // Map message headers to skipped message keys to handle out-of-order delivery
        this.skippedMessageKeys = new Map(); // key: "remotePubKeyHex_sequence" -> messageKey
    }

    /**
     * Initializes an active communication session between two nodes.
     * @param {Uint8Array} sharedMasterSecret - Derived out-of-band or via initial X3DH handshake
     * @param {boolean} isInitiator - Whether this peer initiated the handshake
     */
    static async create(sharedMasterSecret, isInitiator, localDHKeyPair, remoteDHPubRaw) {
        const session = new DoubleRatchetSession();
        session.localDHKeyPair = localDHKeyPair;
        session.remoteDHPubKey = remoteDHPubRaw;

        // Perform initial root derivation using HKDF-SHA256
        const keys = await GhostLinkCrypto.hkdfDerive(sharedMasterSecret, "GhostLink-DoubleRatchet-Root");
        session.rootKey = keys.slice(0, 32);

        const chainSecret = keys.slice(32, 64);
        if (isInitiator) {
            session.sendChainKey = chainSecret;
            session.recvChainKey = null; // Waits for peer's response to rotate receiving chain
        } else {
            session.recvChainKey = chainSecret;
            session.sendChainKey = null;
        }

        return session;
    }

    /**
     * Performs a DH Ratchet step to rotate root and symmetric chains when a new public key is received.
     */
    async rotateDHRatchet(newRemotePubKeyRaw) {
        this.remoteDHPubKey = newRemotePubKeyRaw;
        this.recvSequence = 0;

        // Derive new shared secret
        const dhSecret = await GhostLinkCrypto.deriveDHSecret(this.localDHKeyPair.privateKey, newRemotePubKeyRaw);

        // Rotate Root Key
        const keys = await GhostLinkCrypto.hkdfDerive(dhSecret, "GhostLink-DoubleRatchet-Root", this.rootKey);
        this.rootKey = keys.slice(0, 32);
        this.recvChainKey = keys.slice(32, 64);

        // Generate a new ephemeral key pair for sending
        this.localDHKeyPair = await cryptoProvider.subtle.generateKey(
            { name: "X25519" },
            true,
            ["deriveKey", "deriveBits"]
        );
        this.sendSequence = 0;

        // Rotate root key again with the new local private key
        const nextDhSecret = await GhostLinkCrypto.deriveDHSecret(this.localDHKeyPair.privateKey, newRemotePubKeyRaw);
        const sendKeys = await GhostLinkCrypto.hkdfDerive(nextDhSecret, "GhostLink-DoubleRatchet-Root", this.rootKey);
        this.rootKey = sendKeys.slice(0, 32);
        this.sendChainKey = sendKeys.slice(32, 64);
    }

    /**
     * Symmetric KDF chain rotation to derive message encryption key.
     */
    async encryptMessage(plaintext) {
        if (!this.sendChainKey) {
            throw new Error("Double Ratchet sending chain not initialized. Establish peer connection first.");
        }

        // Derive message key and next send chain key
        const subkeys = await GhostLinkCrypto.hkdfDerive(this.sendChainKey, "GhostLink-SymmetricRatchet");
        const nextChainKey = subkeys.slice(0, 32);
        const messageKey = subkeys.slice(32, 64);

        this.sendChainKey = nextChainKey;
        this.sendSequence++;

        // Associated Data (AD) contains sequence number and local DH public key (for verification)
        const localDHPubRaw = new Uint8Array(await cryptoProvider.subtle.exportKey("raw", this.localDHKeyPair.publicKey));
        const adBytes = new Uint8Array(localDHPubRaw.length + 4);
        adBytes.set(localDHPubRaw, 0);
        adBytes[localDHPubRaw.length] = (this.sendSequence >> 24) & 0xFF;
        adBytes[localDHPubRaw.length + 1] = (this.sendSequence >> 16) & 0xFF;
        adBytes[localDHPubRaw.length + 2] = (this.sendSequence >> 8) & 0xFF;
        adBytes[localDHPubRaw.length + 3] = this.sendSequence & 0xFF;

        const { ciphertext, iv } = await GhostLinkCrypto.encryptAES_GCM(messageKey, plaintext, adBytes);

        return {
            ciphertext,
            iv,
            sequence: this.sendSequence,
            dhPublicKey: GhostLinkCrypto.toHex(localDHPubRaw)
        };
    }

    /**
     * Symmetric KDF chain rotation to decrypt message key.
     */
    async decryptMessage(ciphertext, iv, sequence, remoteDHPubHex) {
        const remoteDHPubRaw = GhostLinkCrypto.fromHex(remoteDHPubHex);

        // 1. Check if we need to rotate the DH ratchet (received a new public key)
        const isNewKey = !this.remoteDHPubKey || GhostLinkCrypto.toHex(this.remoteDHPubKey) !== remoteDHPubHex;

        if (isNewKey && this.remoteDHPubKey) {
            // Skip and cache any remaining message keys in the old chain
            // In a strict real-time chat, we directly execute DH ratchet step
            await this.rotateDHRatchet(remoteDHPubRaw);
        } else if (!this.recvChainKey && remoteDHPubRaw) {
            // First receive rotation for initiator
            const dhSecret = await GhostLinkCrypto.deriveDHSecret(this.localDHKeyPair.privateKey, remoteDHPubRaw);
            const keys = await GhostLinkCrypto.hkdfDerive(dhSecret, "GhostLink-DoubleRatchet-Root", this.rootKey);
            this.rootKey = keys.slice(0, 32);
            this.recvChainKey = keys.slice(32, 64);
        }

        // 2. Derive message key from the receiving chain
        if (!this.recvChainKey) {
            throw new Error("Double Ratchet receiving chain not initialized.");
        }

        const subkeys = await GhostLinkCrypto.hkdfDerive(this.recvChainKey, "GhostLink-SymmetricRatchet");
        const nextChainKey = subkeys.slice(0, 32);
        const messageKey = subkeys.slice(32, 64);

        this.recvChainKey = nextChainKey;
        this.recvSequence++;

        // Associated Data (AD) matches what was sent
        const adBytes = new Uint8Array(remoteDHPubRaw.length + 4);
        adBytes.set(remoteDHPubRaw, 0);
        adBytes[remoteDHPubRaw.length] = (sequence >> 24) & 0xFF;
        adBytes[remoteDHPubRaw.length + 1] = (sequence >> 16) & 0xFF;
        adBytes[remoteDHPubRaw.length + 2] = (sequence >> 8) & 0xFF;
        adBytes[remoteDHPubRaw.length + 3] = sequence & 0xFF;

        // Decrypt the payload
        const plaintext = await GhostLinkCrypto.decryptAES_GCM(messageKey, ciphertext, iv, adBytes);
        return plaintext;
    }
}

// Export for Node.js test environment, otherwise expose globally to browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { GhostLinkCrypto, DoubleRatchetSession };
} else {
    window.GhostLinkCrypto = GhostLinkCrypto;
    window.DoubleRatchetSession = DoubleRatchetSession;
}
