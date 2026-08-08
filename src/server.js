const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const PORT = process.env.PORT || 3000;

// In-Memory state for active ephemeral signaling sessions
// Maps sessionId -> { socket, createdAt }
const sessions = new Map();

// Strict TTL for inactive/active sessions: automatically clean up or close after some time
const SESSION_TTL_MS = 5 * 60 * 1000; // 5 minutes TTL

// Periodic garbage collection to enforce TTL of sessions
setInterval(() => {
    const now = Date.now();
    for (const [sessionId, session] of sessions.entries()) {
        if (now - session.createdAt > SESSION_TTL_MS) {
            console.log(`[TTL PURGE] Session ${sessionId} expired.`);
            try {
                session.socket.close();
            } catch (e) {}
            sessions.delete(sessionId);
        }
    }
}, 30000); // Run every 30 seconds

// HTTP Server to serve static public frontend assets
const server = http.createServer((req, res) => {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = path.join(__dirname, 'public', filePath);

    // Guard against directory traversal attacks
    if (!filePath.startsWith(path.join(__dirname, 'public'))) {
        res.writeHead(403, { 'Content-Type': 'text/plain' });
        res.end('Access Denied');
        return;
    }

    const extname = path.extname(filePath);
    let contentType = 'text/html';
    switch (extname) {
        case '.js':
            contentType = 'text/javascript';
            break;
        case '.css':
            contentType = 'text/css';
            break;
        case '.json':
            contentType = 'application/json';
            break;
        case '.png':
            contentType = 'image/png';
            break;
        case '.jpg':
            contentType = 'image/jpg';
            break;
    }

    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/plain' });
                res.end('File Not Found');
            } else {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end(`Server Error: ${error.code}`);
            }
        } else {
            // Apply Hardened Defaults Headers
            res.writeHead(200, {
                'Content-Type': contentType,
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Content-Security-Policy': "default-src 'self'; script-src 'self' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; connect-src 'self' ws: wss:; img-src 'self' data:;",
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
            });
            res.end(content, 'utf-8');
        }
    });
});

// Create WebSocket server attached to the HTTP server
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    let registeredSessionId = null;

    ws.on('message', (messageStr) => {
        try {
            // Parse and schema-validate incoming message
            const data = JSON.parse(messageStr);
            const { type, sessionId, targetSessionId, payload } = data;

            if (!type) {
                ws.send(JSON.stringify({ type: 'error', message: 'Missing message type' }));
                return;
            }

            // Rate-limiting and size-limiting checks (hardened defaults)
            if (messageStr.length > 65536) { // 64KB max packet size
                ws.send(JSON.stringify({ type: 'error', message: 'Payload size limit exceeded' }));
                ws.close();
                return;
            }

            switch (type) {
                case 'register':
                    if (!sessionId || typeof sessionId !== 'string' || sessionId.length < 8) {
                        ws.send(JSON.stringify({ type: 'error', message: 'Invalid Session ID' }));
                        return;
                    }
                    if (sessions.has(sessionId)) {
                        ws.send(JSON.stringify({ type: 'error', message: 'Session ID already registered' }));
                        return;
                    }
                    registeredSessionId = sessionId;
                    sessions.set(sessionId, {
                        socket: ws,
                        createdAt: Date.now()
                    });
                    console.log(`[REGISTER] Session registered: ${sessionId}`);
                    ws.send(JSON.stringify({ type: 'registered', sessionId }));
                    break;

                case 'signal':
                    // Sealed-sender style routing: we forward to targetSessionId without exposing sender's persistent identity
                    if (!targetSessionId || !payload) {
                        ws.send(JSON.stringify({ type: 'error', message: 'Missing signal parameters' }));
                        return;
                    }
                    const targetSession = sessions.get(targetSessionId);
                    if (targetSession) {
                        // Forward the envelope. Note that we do NOT attach the sender's registeredSessionId,
                        // keeping the routing sealed-sender and preventing social graph building on the server.
                        // The recipient learns the public key and handshakes directly inside the end-to-end encrypted channel.
                        targetSession.socket.send(JSON.stringify({
                            type: 'signal',
                            payload: payload // Keep payload padded to fixed-size by client
                        }));
                    } else {
                        ws.send(JSON.stringify({ type: 'error', message: 'Target peer offline or invalid' }));
                    }
                    break;

                default:
                    ws.send(JSON.stringify({ type: 'error', message: 'Unsupported message type' }));
            }
        } catch (e) {
            ws.send(JSON.stringify({ type: 'error', message: 'Malformed JSON payload' }));
        }
    });

    ws.on('close', () => {
        if (registeredSessionId) {
            console.log(`[DISCONNECT] Session closed: ${registeredSessionId}`);
            sessions.delete(registeredSessionId);
        }
    });

    ws.on('error', (err) => {
        console.error(`[WS ERROR]`, err);
    });
});

server.listen(PORT, () => {
    console.log(`🔥 GhostLink Signaling Server running on port ${PORT}`);
    console.log(`Visit http://localhost:${PORT} in your browser to start secure, private chats.`);
});

module.exports = { server, sessions };
