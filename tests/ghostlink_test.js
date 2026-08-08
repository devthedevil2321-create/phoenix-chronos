/**
 * Automated Cryptographic & Protocol Test Suite for GhostLink
 * Executes within Node.js to assert and verify the cryptographic integrity,
 * key rotation, and tamper-resistance of the Double Ratchet engine.
 */

const assert = require('assert').strict;
const { GhostLinkCrypto, DoubleRatchetSession } = require('../src/public/crypto.js');

async function runTests() {
    console.log('🧪 Starting GhostLink Cryptographic & Protocol Tests...\n');

    try {
        // ----------------------------------------------------
        // TEST 1: Key Generation & Fingerprint Derivation
        // ----------------------------------------------------
        console.log('▶ Test 1: Key Generation...');
        const aliceNode = await GhostLinkCrypto.generateKeyPair();
        assert.ok(aliceNode.identityKeyPair, 'Alice identity key pair must exist');
        assert.ok(aliceNode.dhKeyPair, 'Alice DH key pair must exist');
        assert.strictEqual(typeof aliceNode.fingerprint, 'string', 'Fingerprint must be a string');
        assert.strictEqual(aliceNode.fingerprint.length, 40, 'Fingerprint must be a 40-character SHA-256 substring');
        console.log('✓ Key Generation test passed successfully.\n');

        // ----------------------------------------------------
        // TEST 2: Ephemeral DH Shared Secret derivation (X25519)
        // ----------------------------------------------------
        console.log('▶ Test 2: Ephemeral Diffie-Hellman Key Agreement...');
        const bobNode = await GhostLinkCrypto.generateKeyPair();

        const rawAliceDHPubKey = await bobNode.dhKeyPair.publicKey; // to export
        const exportedAliceDH = new Uint8Array(await require('crypto').webcrypto.subtle.exportKey("raw", aliceNode.dhKeyPair.publicKey));
        const exportedBobDH = new Uint8Array(await require('crypto').webcrypto.subtle.exportKey("raw", bobNode.dhKeyPair.publicKey));

        // Alice derives DH secret using Bob's public key
        const aliceSecret = await GhostLinkCrypto.deriveDHSecret(aliceNode.dhKeyPair.privateKey, exportedBobDH);

        // Bob derives DH secret using Alice's public key
        const bobSecret = await GhostLinkCrypto.deriveDHSecret(bobNode.dhKeyPair.privateKey, exportedAliceDH);

        assert.deepEqual(aliceSecret, bobSecret, 'Derived Diffie-Hellman secrets must be byte-identical');
        console.log('✓ X25519 DH Key Agreement passed successfully.\n');

        // ----------------------------------------------------
        // TEST 3: HKDF Derivation (KDF Chains)
        // ----------------------------------------------------
        console.log('▶ Test 3: HKDF KDF Chain Derivation...');
        const salt = new Uint8Array(32);
        const derived1 = await GhostLinkCrypto.hkdfDerive(aliceSecret, 'GhostLink-TestChain', salt);
        const derived2 = await GhostLinkCrypto.hkdfDerive(bobSecret, 'GhostLink-TestChain', salt);

        assert.deepEqual(derived1, derived2, 'HKDF derivations from identical inputs must match');
        assert.strictEqual(derived1.length, 64, 'HKDF output length must match requested entropy (64 bytes)');
        console.log('✓ HKDF KDF Chain Derivation passed successfully.\n');

        // ----------------------------------------------------
        // TEST 4: Double Ratchet Session & Rotational Messaging
        // ----------------------------------------------------
        console.log('▶ Test 4: Double Ratchet State Machine & Rotations...');

        // Derive shared master secret (simulating initial X3DH)
        const sharedMasterSecret = aliceSecret;

        // Create Alice's and Bob's active Double Ratchet sessions
        const aliceSession = await DoubleRatchetSession.create(sharedMasterSecret, true, aliceNode.dhKeyPair, exportedBobDH);
        const bobSession = await DoubleRatchetSession.create(sharedMasterSecret, false, bobNode.dhKeyPair, exportedAliceDH);

        // Alice encrypts a message to Bob
        const plaintext1 = "CONFIDENTIAL_OPERATIONAL_COMMAND: MISSION_GO";
        const envelope1 = await aliceSession.encryptMessage(plaintext1);

        assert.strictEqual(envelope1.sequence, 1, 'Alice first message sequence must be 1');
        assert.ok(envelope1.ciphertext, 'Ciphertext must exist');
        assert.ok(envelope1.iv, 'IV must exist');

        // Bob decrypts the message from Alice
        const decrypted1 = await bobSession.decryptMessage(
            envelope1.ciphertext,
            envelope1.iv,
            envelope1.sequence,
            envelope1.dhPublicKey
        );

        assert.strictEqual(decrypted1, plaintext1, 'Bob decrypted plaintext must match Alice original plaintext');
        console.log('✓ Double Ratchet encryption & decryption passed successfully.');

        // Alice encrypts a second message to Bob (symmetric KDF rotation only, no DH change yet)
        const plaintext2 = "SECURE_UPDATE: ALIGNING_TO_COORDINATES";
        const envelope2 = await aliceSession.encryptMessage(plaintext2);

        assert.strictEqual(envelope2.sequence, 2, 'Alice second message sequence must be 2');

        const decrypted2 = await bobSession.decryptMessage(
            envelope2.ciphertext,
            envelope2.iv,
            envelope2.sequence,
            envelope2.dhPublicKey
        );

        assert.strictEqual(decrypted2, plaintext2, 'Bob decrypted second plaintext must match');
        console.log('✓ Double Ratchet symmetric KDF-chain rotation passed successfully.\n');

        // ----------------------------------------------------
        // TEST 5: Tamper Rejection and Integrity Rejection
        // ----------------------------------------------------
        console.log('▶ Test 5: Cryptographic Tamper & Integrity Rejection...');
        const tamperedCiphertext = envelope2.ciphertext.substring(0, envelope2.ciphertext.length - 8) + '00000000'; // Corrupting auth tag / ciphertext bytes

        await assert.rejects(
            async () => {
                await bobSession.decryptMessage(
                    tamperedCiphertext,
                    envelope2.iv,
                    envelope2.sequence,
                    envelope2.dhPublicKey
                );
            },
            /Cryptographic verification failed/,
            'Decrypting tampered ciphertext must throw an integrity verification error'
        );
        console.log('✓ Cryptographic Tamper Rejection verified successfully.\n');

        console.log('🏁 ALL GHOSTLINK PROTOCOL & CRYPTO TESTS PASSED SUCCESSFULLY! 🚀');

    } catch (e) {
        console.error('❌ Test execution failed:', e);
        process.exit(1);
    }
}

runTests();
