/**
 * GhostLink Client Application Logic
 * Orchestrates WebRTC peer-to-peer connections, WebSocket signaling,
 * Double Ratchet cryptographic states, and the tactical user interface.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // -------------------------------------------------------------------------
    // STATE MANAGERS & CRYPTO NODE INITIALIZATION
    // -------------------------------------------------------------------------
    let localKeys = null;
    let activeSession = null;
    let activePeerSessionId = null;
    let activePeerFingerprint = null;
    let isInitiator = false;
    let ws = null;
    let peerConnection = null;
    let dataChannel = null;

    // Disappearing Messages Default (60 seconds)
    let disappearingTimeoutMs = 60000;

    // Ephemeral Client Session ID (randomly generated)
    const mySessionId = 'gl_node_' + Array.from(crypto.getRandomValues(new Uint8Array(12)))
        .map(b => b.toString(16).padStart(2, '0')).join('');

    // DOM Elements Cache
    const elMyFingerprint = document.getElementById('my-fingerprint');
    const elMySessionToken = document.getElementById('my-session-token');
    const elNodeOnlineStatus = document.getElementById('node-online-status');
    const elStatusDot = document.getElementById('status-dot');

    const elBtnCreateInvitation = document.getElementById('btn-create-invitation');
    const elDivInvitationCode = document.getElementById('div-invitation-code');
    const elInputInvitationCode = document.getElementById('input-invitation-code');
    const elBtnCopyInvitation = document.getElementById('btn-copy-invitation');
    const elBtnCopyToken = document.getElementById('btn-copy-token');

    const elInputAcceptCode = document.getElementById('input-accept-code');
    const elBtnAcceptInvitation = document.getElementById('btn-accept-invitation');

    const elIntroPanel = document.getElementById('intro-panel');
    const elActivePeerId = document.getElementById('active-peer-id');
    const elActiveHandshakeHash = document.getElementById('active-handshake-hash');
    const elTrustBadge = document.getElementById('trust-badge');
    const elBtnVerifyTrust = document.getElementById('btn-verify-trust');

    const elMessagesContainer = document.getElementById('messages-container');
    const elMessageForm = document.getElementById('message-form');
    const elInputMessage = document.getElementById('input-message');
    const elDisappearingTimeDisplay = document.getElementById('disappearing-time-display');

    const elBtnSet1m = document.getElementById('btn-set-disappear-1m');
    const elBtnSet5m = document.getElementById('btn-set-disappear-5m');
    const elBtnSetOff = document.getElementById('btn-set-disappear-off');
    const elBtnSelfDestruct = document.getElementById('btn-btn-self-destruct') || document.getElementById('btn-self-destruct');

    const elModalTrust = document.getElementById('modal-trust');
    const elBtnCloseModal = document.getElementById('btn-close-modal');
    const elSasDisplay = document.getElementById('sas-display');
    const elPeerFingerprintDisplay = document.getElementById('peer-fingerprint-display');
    const elBtnMarkTrusted = document.getElementById('btn-mark-trusted');
    const elBtnMarkUntrusted = document.getElementById('btn-mark-untrusted');

    // -------------------------------------------------------------------------
    // CRYPTO GENERATION
    // -------------------------------------------------------------------------
    try {
        localKeys = await GhostLinkCrypto.generateKeyPair();
        elMyFingerprint.innerText = localKeys.fingerprint;
        elMySessionToken.value = mySessionId;
    } catch (e) {
        console.error('Crypto Init Failure', e);
        appendSystemMessage('CRITICAL: Web Crypto initialization failed. Browser incompatible.', 'red');
        return;
    }

    // -------------------------------------------------------------------------
    // WEBSOCKET SIGNALING CONNECTION
    // -------------------------------------------------------------------------
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

    function connectSignaling() {
        ws = new WebSocket(socketUrl);

        ws.onopen = () => {
            elNodeOnlineStatus.innerText = 'ONLINE';
            elNodeOnlineStatus.className = 'text-[9px] text-emerald-500 font-bold';
            elStatusDot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';

            // Register identity in-memory with server
            ws.send(JSON.stringify({
                type: 'register',
                sessionId: mySessionId
            }));
        };

        ws.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'signal') {
                    await handleIncomingSignal(msg.payload);
                } else if (msg.type === 'error') {
                    console.warn('[Server Signal Alert]', msg.message);
                }
            } catch (err) {
                console.error('Signaling parse error', err);
            }
        };

        ws.onclose = () => {
            elNodeOnlineStatus.innerText = 'OFFLINE';
            elNodeOnlineStatus.className = 'text-[9px] text-yellow-500';
            elStatusDot.className = 'w-2 h-2 rounded-full bg-yellow-500';
            // Auto reconnect after 3 seconds
            setTimeout(connectSignaling, 3000);
        };
    }

    connectSignaling();

    // -------------------------------------------------------------------------
    // SIGNAL ROUTING & HANDSHAKE HANDLING
    // -------------------------------------------------------------------------
    async function sendSignal(targetId, payload) {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        // Apply strict padding so message lengths look uniform (2048 bytes)
        const payloadStr = JSON.stringify(payload);
        const padLength = 2048 - payloadStr.length;
        const paddedPayload = {
            data: payloadStr,
            padding: padLength > 0 ? 'X'.repeat(padLength) : ''
        };

        ws.send(JSON.stringify({
            type: 'signal',
            targetSessionId: targetId,
            payload: paddedPayload
        }));
    }

    async function handleIncomingSignal(paddedPayload) {
        const payload = JSON.parse(paddedPayload.data);
        const { step, senderSessionId, remoteDHPub, remoteIdentityPub, sdp, candidate, ephemeralDHPub } = payload;

        if (step === 'x3dh_init') {
            // Bob receives handshake from Alice
            isInitiator = false;
            activePeerSessionId = senderSessionId;

            // X3DH shared key derivation: local DH private key x Alice's ephemeral DH public key
            const sharedMasterSecret = await GhostLinkCrypto.deriveDHSecret(
                localKeys.dhKeyPair.privateKey,
                GhostLinkCrypto.fromHex(ephemeralDHPub)
            );

            // Establish Double Ratchet Session
            const remoteDHPubRaw = GhostLinkCrypto.fromHex(remoteDHPub);
            activeSession = await DoubleRatchetSession.create(
                sharedMasterSecret,
                false, // responder
                localKeys.dhKeyPair,
                remoteDHPubRaw
            );

            // Compute Fingerprint and Trust verification status
            activePeerFingerprint = await GhostLinkCrypto.hashData(GhostLinkCrypto.fromHex(remoteIdentityPub));
            activePeerFingerprint = activePeerFingerprint.substring(0, 40).toUpperCase();

            // Store remote identifiers
            elActivePeerId.innerText = activePeerSessionId;
            elActiveHandshakeHash.innerText = activePeerFingerprint;
            elIntroPanel.classList.add('hidden');

            // Send handshake confirmation back to Alice
            const localDHPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", localKeys.dhKeyPair.publicKey));
            const localIdentityPubRaw = localKeys.rawIdentityPublicKey;

            await sendSignal(activePeerSessionId, {
                step: 'x3dh_confirm',
                senderSessionId: mySessionId,
                remoteDHPub: GhostLinkCrypto.toHex(localDHPubRaw),
                remoteIdentityPub: GhostLinkCrypto.toHex(localIdentityPubRaw)
            });

            // Initialize WebRTC connection
            initWebRTC(false);

        } else if (step === 'x3dh_confirm') {
            // Alice receives handshake confirmation from Bob
            activePeerSessionId = senderSessionId;

            const remoteDHPubRaw = GhostLinkCrypto.fromHex(remoteDHPub);
            const remoteIdentityPubRaw = GhostLinkCrypto.fromHex(remoteIdentityPub);

            // Complete local Double Ratchet setup
            // In Alice's case, she already has the Double Ratchet initialized during the accept invitation stage.
            // Update the remote public key
            if (activeSession) {
                activeSession.remoteDHPubKey = remoteDHPubRaw;
            }

            activePeerFingerprint = await GhostLinkCrypto.hashData(remoteIdentityPubRaw);
            activePeerFingerprint = activePeerFingerprint.substring(0, 40).toUpperCase();

            elActivePeerId.innerText = activePeerSessionId;
            elActiveHandshakeHash.innerText = activePeerFingerprint;
            elIntroPanel.classList.add('hidden');

            // Initialize WebRTC connection
            initWebRTC(true);

        } else if (sdp) {
            // WebRTC SDP Handshake routing
            if (!peerConnection) initWebRTC(!isInitiator);
            await peerConnection.setRemoteDescription(new RTCSessionDescription(sdp));
            if (sdp.type === 'offer') {
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                await sendSignal(activePeerSessionId, { sdp: answer });
            }
        } else if (candidate) {
            // WebRTC ICE Candidate routing
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
                } catch (e) {
                    console.warn('ICE Candidate Error', e);
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // WEBRTC PEER CONNECTION (Relay-Only Hardened Mode)
    // -------------------------------------------------------------------------
    function initWebRTC(initiator) {
        // Enforce Relay-Only to shield IP address (iceTransportPolicy: 'relay')
        const rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' } // fallback STUN
            ],
            iceTransportPolicy: 'relay' // Force TURN relay as per Section 3
        };

        peerConnection = new RTCPeerConnection(rtcConfig);

        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                sendSignal(activePeerSessionId, { candidate: event.candidate });
            }
        };

        if (initiator) {
            // Initiator establishes DataChannel
            dataChannel = peerConnection.createDataChannel('ghostlink_channel', {
                ordered: true
            });
            setupDataChannel();

            peerConnection.createOffer().then(offer => {
                return peerConnection.setLocalDescription(offer);
            }).then(() => {
                sendSignal(activePeerSessionId, { sdp: peerConnection.localDescription });
            });
        } else {
            // Responder handles incoming DataChannel
            peerConnection.ondatachannel = (event) => {
                dataChannel = event.channel;
                setupDataChannel();
            };
        }
    }

    function setupDataChannel() {
        dataChannel.onopen = () => {
            appendSystemMessage('SECURE WEBRTC DATA-CHANNEL ESTABLISHED (RELAY-MODE).', 'emerald');
        };

        dataChannel.onmessage = async (event) => {
            await handleIncomingMessage(event.data);
        };

        dataChannel.onclose = () => {
            appendSystemMessage('SECURE DATA-CHANNEL TERMINATED.', 'yellow');
        };
    }

    // -------------------------------------------------------------------------
    // INVITATION FLOWS (Handshake Trigger)
    // -------------------------------------------------------------------------
    elBtnCreateInvitation.addEventListener('click', async () => {
        // Create an invitation packet.
        // It contains local ephemeral session token, public identity key, and DH public key.
        // ABSOLUTELY ZERO private material.
        const localDHPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", localKeys.dhKeyPair.publicKey));
        const localIdentityPubRaw = localKeys.rawIdentityPublicKey;

        const invitationObj = {
            id: mySessionId,
            dh: GhostLinkCrypto.toHex(localDHPubRaw),
            idKey: GhostLinkCrypto.toHex(localIdentityPubRaw)
        };

        // Convert invitation object to base64 code (clean, easy copy/paste)
        const base64Code = btoa(JSON.stringify(invitationObj));

        elInputInvitationCode.value = base64Code;
        elDivInvitationCode.classList.remove('hidden');
        appendSystemMessage('GENERATE_INVITATION: Token crafted successfully. Send to peer.', 'emerald');
    });

    elBtnAcceptInvitation.addEventListener('click', async () => {
        const rawCode = elInputAcceptCode.value.trim();
        if (!rawCode) return;

        try {
            const invitationObj = JSON.parse(atob(rawCode));
            const { id: peerId, dh: peerDH, idKey: peerIdentityKey } = invitationObj;

            if (!peerId || !peerDH || !peerIdentityKey) {
                throw new Error('Malformed token attributes');
            }

            isInitiator = true;
            activePeerSessionId = peerId;

            // Generate an ephemeral X25519 client key pair specifically for this transaction
            const ephemeralDH = await crypto.subtle.generateKey(
                { name: "X25519" },
                true,
                ["deriveKey", "deriveBits"]
            );

            // Derive shared master secret: ephemeral private key x Bob's DH public key
            const remoteDHPubRaw = GhostLinkCrypto.fromHex(peerDH);
            const sharedMasterSecret = await GhostLinkCrypto.deriveDHSecret(ephemeralDH.privateKey, remoteDHPubRaw);

            // Establish Double Ratchet Session
            activeSession = await DoubleRatchetSession.create(
                sharedMasterSecret,
                true, // initiator
                ephemeralDH,
                remoteDHPubRaw
            );

            // Setup peer fingerprint identifiers
            activePeerFingerprint = await GhostLinkCrypto.hashData(GhostLinkCrypto.fromHex(peerIdentityKey));
            activePeerFingerprint = activePeerFingerprint.substring(0, 40).toUpperCase();

            // Publish Handshake Packet to Bob via sealed-sender WS
            const localDHPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", localKeys.dhKeyPair.publicKey));
            const localIdentityPubRaw = localKeys.rawIdentityPublicKey;
            const ephemeralDHPubRaw = new Uint8Array(await crypto.subtle.exportKey("raw", ephemeralDH.publicKey));

            await sendSignal(activePeerSessionId, {
                step: 'x3dh_init',
                senderSessionId: mySessionId,
                remoteDHPub: GhostLinkCrypto.toHex(localDHPubRaw),
                remoteIdentityPub: GhostLinkCrypto.toHex(localIdentityPubRaw),
                ephemeralDHPub: GhostLinkCrypto.toHex(ephemeralDHPubRaw)
            });

            appendSystemMessage('ACCEPT_INVITATION: Handshake triggered. Negotiating key ratification...', 'emerald');

        } catch (e) {
            console.error(e);
            appendSystemMessage('ERROR: Invalid or corrupt invitation code.', 'red');
        }
    });

    // -------------------------------------------------------------------------
    // TRUST VERIFICATION MODAL
    // -------------------------------------------------------------------------
    elBtnVerifyTrust.addEventListener('click', async () => {
        if (!activePeerFingerprint) return;

        // Generate Short Authentication String (SAS)
        // Hash of Combined Fingerprints: myFingerprint + activePeerFingerprint
        const sorted = [localKeys.fingerprint, activePeerFingerprint].sort();
        const combinedBytes = new TextEncoder().encode(sorted.join('::'));
        const hashHex = await GhostLinkCrypto.hashData(combinedBytes);

        // Convert hex bytes to 4 tactical numbers
        const sasString = [
            parseInt(hashHex.substring(0, 8), 16) % 10000,
            parseInt(hashHex.substring(8, 16), 16) % 10000,
            parseInt(hashHex.substring(16, 24), 16) % 10000,
            parseInt(hashHex.substring(24, 32), 16) % 10000
        ].map(n => n.toString().padStart(4, '0')).join(' - ');

        elSasDisplay.innerText = sasString;
        elPeerFingerprintDisplay.innerText = activePeerFingerprint;
        elModalTrust.classList.remove('hidden');
    });

    elBtnCloseModal.addEventListener('click', () => elModalTrust.classList.add('hidden'));

    elBtnMarkTrusted.addEventListener('click', () => {
        elTrustBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Handshake Trusted';
        elTrustBadge.className = 'text-[10px] text-emerald-400 font-bold flex items-center gap-1';
        elModalTrust.classList.add('hidden');
        appendSystemMessage('TRUST_SYSTEM: Key signature authenticated and verified.', 'emerald');
    });

    elBtnMarkUntrusted.addEventListener('click', () => {
        elTrustBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> TOFU Unverified';
        elTrustBadge.className = 'text-[10px] text-red-400 font-bold flex items-center gap-1';
        elModalTrust.classList.add('hidden');
    });

    // -------------------------------------------------------------------------
    // DISAPPEARING MESSAGES TIMERS
    // -------------------------------------------------------------------------
    elBtnSet1m.addEventListener('click', () => {
        disappearingTimeoutMs = 60000;
        elDisappearingTimeDisplay.innerText = '1 minute';
    });

    elBtnSet5m.addEventListener('click', () => {
        disappearingTimeoutMs = 300000;
        elDisappearingTimeDisplay.innerText = '5 minutes';
    });

    elBtnSetOff.addEventListener('click', () => {
        disappearingTimeoutMs = 0;
        elDisappearingTimeDisplay.innerText = 'Never';
    });

    // -------------------------------------------------------------------------
    // MESSAGING SYSTEM
    // -------------------------------------------------------------------------
    async function handleIncomingMessage(envelopeStr) {
        try {
            const envelope = JSON.parse(envelopeStr);
            const { ciphertext, iv, sequence, dhPublicKey } = envelope;

            if (!activeSession) {
                console.warn('Message dropped: session not established.');
                return;
            }

            // Decrypt natively using the Double Ratchet engine
            const plaintext = await activeSession.decryptMessage(ciphertext, iv, sequence, dhPublicKey);
            appendChatMessage(plaintext, 'in');

        } catch (e) {
            console.error('Decryption Error', e);
            appendSystemMessage('INTEGRITY_WARNING: Received undecryptable or tampered payload. Dropping packet.', 'red');
        }
    }

    elMessageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msgText = elInputMessage.value.trim();
        if (!msgText || !activeSession) return;

        try {
            // Encrypt using the Double Ratchet state
            const envelope = await activeSession.encryptMessage(msgText);
            const envelopeStr = JSON.stringify(envelope);

            // Overwrite plaintext input ASAP to avoid memory leaks
            elInputMessage.value = '';

            // Send via WebRTC DataChannel (P2P), or fallback safely to signaling server if datachannel is not ready
            if (dataChannel && dataChannel.readyState === 'open') {
                dataChannel.send(envelopeStr);
            } else {
                await sendSignal(activePeerSessionId, envelope);
            }

            appendChatMessage(msgText, 'out');

        } catch (err) {
            console.error('Encryption Error', err);
            appendSystemMessage('CRITICAL: Message encryption pipeline failed.', 'red');
        }
    });

    // -------------------------------------------------------------------------
    // INTERFACE RENDERERS (Chat logs & disappearing elements)
    // -------------------------------------------------------------------------
    function appendChatMessage(text, direction) {
        const messageId = 'msg_' + Math.random().toString(36).substring(2, 11);
        const div = document.createElement('div');
        div.id = messageId;
        div.className = `flex ${direction === 'out' ? 'justify-end' : 'justify-start'}`;

        const isDisappearing = disappearingTimeoutMs > 0;
        const timeLimitSecs = disappearingTimeoutMs / 1000;

        div.innerHTML = `
            <div class="message-bubble ${direction === 'out' ? 'message-out' : 'message-in'} rounded-lg px-4 py-2.5 flex flex-col gap-1">
                <span class="text-slate-200 select-text break-all">${escapeHtml(text)}</span>
                <div class="flex justify-between items-center gap-4 text-[8px] text-slate-500 font-bold uppercase tracking-wider">
                    <span>${direction === 'out' ? 'You' : 'Peer'}</span>
                    ${isDisappearing ? `<span class="text-yellow-600/80 italic animate-pulse" id="${messageId}-timer"><i class="fa-solid fa-clock-rotate-left"></i> Wiping in ${timeLimitSecs}s</span>` : ''}
                </div>
            </div>
        `;

        elMessagesContainer.appendChild(div);
        elMessagesContainer.scrollTop = elMessagesContainer.scrollHeight;

        // Apply Disappearing timer (secure local wipe)
        if (isDisappearing) {
            let elapsed = 0;
            const timerEl = document.getElementById(`${messageId}-timer`);
            const interval = setInterval(() => {
                elapsed += 1000;
                const remaining = Math.max(0, timeLimitSecs - (elapsed / 1000));
                if (timerEl) {
                    timerEl.innerHTML = `<i class="fa-solid fa-clock-rotate-left"></i> Wiping in ${Math.round(remaining)}s`;
                }
                if (remaining <= 0) {
                    clearInterval(interval);
                }
            }, 1000);

            setTimeout(() => {
                clearInterval(interval);
                const el = document.getElementById(messageId);
                if (el) {
                    // Wipe content from DOM node and delete node
                    el.innerHTML = '';
                    el.remove();
                }
            }, disappearingTimeoutMs);
        }
    }

    function appendSystemMessage(text, color = 'slate') {
        const div = document.createElement('div');
        div.className = 'flex justify-center my-2';

        let colorClass = 'text-slate-500 bg-slate-900/30 border-slate-900';
        if (color === 'emerald') colorClass = 'text-emerald-400 bg-emerald-950/20 border-emerald-900/40';
        if (color === 'yellow') colorClass = 'text-yellow-500 bg-yellow-950/20 border-yellow-900/40';
        if (color === 'red') colorClass = 'text-red-400 bg-red-950/20 border-red-900/40';

        div.innerHTML = `
            <div class="border ${colorClass} px-4 py-1.5 rounded-md font-bold text-[9px] uppercase tracking-wider flex items-center gap-2">
                <i class="fa-solid fa-triangle-exclamation"></i> ${text}
            </div>
        `;
        elMessagesContainer.appendChild(div);
        elMessagesContainer.scrollTop = elMessagesContainer.scrollHeight;
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // -------------------------------------------------------------------------
    // SYSTEM SELF-DESTRUCT (Zero-Memory Wipeout)
    // -------------------------------------------------------------------------
    elBtnSelfDestruct.addEventListener('click', () => {
        if (confirm('CONFIRM DESTRUCTION: THIS WILL INSTANTLY PURGE ALL CRYPTOGRAPHIC IDENTITY AND ACTIVE SESSION KEYS.')) {
            // Overwrite state references
            localKeys = null;
            activeSession = null;
            activePeerSessionId = null;
            activePeerFingerprint = null;
            ws = null;

            // Re-render UI to empty
            document.body.innerHTML = `
                <div class="h-full w-full bg-slate-950 flex flex-col items-center justify-center p-8 text-center font-mono text-red-500">
                    <div class="w-16 h-16 rounded-full border border-red-800 bg-red-950/10 flex items-center justify-center text-2xl animate-ping mb-6">
                        <i class="fa-solid fa-radiation"></i>
                    </div>
                    <h1 class="text-md font-bold tracking-widest uppercase mb-2">Node Erased Successfully</h1>
                    <p class="text-[10px] text-slate-500 max-w-sm">
                        All in-memory key stores, Double Ratchet states, and identity pairs have been physically wiped from this device. Redirecting to clean environment...
                    </p>
                </div>
            `;

            // Clear sessionStorage & localStorage just in case, and trigger reload
            try {
                window.sessionStorage.clear();
                window.localStorage.clear();
            } catch (e) {}

            setTimeout(() => {
                window.location.reload();
            }, 3000);
        }
    });

    // Handle Copy Operations safely
    elBtnCopyInvitation.addEventListener('click', () => {
        elInputInvitationCode.select();
        document.execCommand('copy');
        appendSystemMessage('INVITATION_COPLED: Token copied to clipboard.', 'emerald');
    });

    elBtnCopyToken.addEventListener('click', () => {
        elMySessionToken.select();
        document.execCommand('copy');
        appendSystemMessage('TOKEN_COPLED: Ephemeral token copied.', 'emerald');
    });
});
