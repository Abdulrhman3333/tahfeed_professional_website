'use strict';

console.log('[bot] starting...');

require('dotenv').config();

const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = parseInt(process.env.PORT || '3001', 10);
const HOST = process.env.HOST || '0.0.0.0';
const TOKEN = process.env.WA_BOT_TOKEN || '';
const MIN_DELAY_MS = parseInt(process.env.MIN_DELAY_MS || '4000', 10);
const MAX_DELAY_MS = parseInt(process.env.MAX_DELAY_MS || '12000', 10);
const SESSION_DIR = process.env.SESSION_DIR || './.wwebjs_auth';
const CHROMIUM_PATH = process.env.PUPPETEER_EXECUTABLE_PATH || process.env.CHROMIUM_PATH || '';

if (!TOKEN) {
    console.warn('[bot] WA_BOT_TOKEN is empty - the /send endpoint will reject every request. Set WA_BOT_TOKEN in the environment.');
}

console.log(`[bot] PORT=${PORT} HOST=${HOST} SESSION_DIR=${SESSION_DIR}`);
console.log(`[bot] Chromium: ${CHROMIUM_PATH || '(bundled puppeteer)'}`);

const puppeteerOptions = {
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
    ],
};
if (CHROMIUM_PATH) {
    puppeteerOptions.executablePath = CHROMIUM_PATH;
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
    puppeteer: puppeteerOptions,
});

let isReady = false;

client.on('qr', (qr) => {
    console.log('[bot] Scan this QR with WhatsApp on your phone:');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('[bot] Authenticated.');
});

client.on('auth_failure', (msg) => {
    console.error('[bot] Auth failure:', msg);
});

client.on('ready', () => {
    isReady = true;
    console.log('[bot] WhatsApp client is ready.');
});

client.on('disconnected', (reason) => {
    isReady = false;
    console.warn('[bot] Disconnected:', reason);
});

function rand(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function toChatId(phone) {
    const digits = String(phone || '').replace(/\D/g, '');
    if (!digits) return null;
    let normalized = digits;
    if (normalized.startsWith('00')) normalized = normalized.slice(2);
    if (normalized.startsWith('0')) normalized = '966' + normalized.slice(1);
    else if (normalized.startsWith('5')) normalized = '966' + normalized;
    if (!normalized.startsWith('966')) return null;
    return `${normalized}@c.us`;
}

const app = express();
app.use(express.json({ limit: '4mb' }));

app.get('/health', (_req, res) => {
    res.json({ ok: true, ready: isReady });
});

app.post('/send', async (req, res) => {
    const provided = req.headers['x-bot-token'] || '';
    if (!TOKEN || provided !== TOKEN) {
        return res.status(401).json({ ok: false, error: 'unauthorized' });
    }
    if (!isReady) {
        return res.status(503).json({ ok: false, error: 'whatsapp_client_not_ready' });
    }

    const messages = Array.isArray(req.body && req.body.messages) ? req.body.messages : [];
    if (messages.length === 0) {
        return res.json({ ok: true, results: [] });
    }

    const minDelay = Number.isFinite(req.body.min_delay_ms) ? req.body.min_delay_ms : MIN_DELAY_MS;
    const maxDelay = Number.isFinite(req.body.max_delay_ms) ? req.body.max_delay_ms : MAX_DELAY_MS;

    const results = [];

    for (let i = 0; i < messages.length; i++) {
        const item = messages[i] || {};
        const phone = item.phone;
        const text = (item.text || '').toString();
        const label = item.label || '';

        const chatId = toChatId(phone);
        if (!chatId) {
            results.push({ phone, label, ok: false, error: 'invalid_phone' });
            continue;
        }
        if (!text.trim()) {
            results.push({ phone, label, ok: false, error: 'empty_text' });
            continue;
        }

        try {
            await client.sendMessage(chatId, text);
            results.push({ phone, label, ok: true });
            console.log(`[bot] sent -> ${phone}${label ? ' (' + label + ')' : ''}`);
        } catch (err) {
            const message = err && err.message ? err.message : String(err);
            results.push({ phone, label, ok: false, error: message });
            console.error(`[bot] failed -> ${phone}: ${message}`);
        }

        if (i < messages.length - 1) {
            const delay = rand(Math.min(minDelay, maxDelay), Math.max(minDelay, maxDelay));
            await sleep(delay);
        }
    }

    res.json({ ok: true, results });
});

app.listen(PORT, HOST, () => {
    console.log(`[bot] HTTP listening on http://${HOST}:${PORT}`);
});

console.log('[bot] launching Chromium via puppeteer (this may take 30-90s on a Pi)...');
client.initialize().catch((err) => {
    console.error('[bot] client.initialize() failed:', err);
});
