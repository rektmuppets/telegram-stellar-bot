import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { initializeSignClient, signClient, connectWallet } from './walletconnect/session.js';
import { saveWalletLink, getUserByUsername, addUser, db } from './database.js';
import { logError } from './walletconnect/utils.js';

dotenv.config();

const projectId = process.env.PROJECT_ID;
const appPort = process.env.PORT || 4000; // Default to 4000 if PORT is not set
const app = express();

app.use(cors());
app.use(express.json());

// Debugging Middleware: Logs all incoming requests
app.use((req, res, next) => {
    console.log(`[DEBUG] Incoming Request: ${req.method} ${req.url}`);
    next();
});

// Initialize WalletConnect
initializeSignClient(projectId, {
    name: 'Photon Bot for Stellar',
    description: 'WalletConnect Example',
    url: 'https://api.photonbot.xyz',
    icons: ['https://assets.reown.com/reown-profile-pic.png'],
}).catch((err) => {
    logError('WalletConnect Initialization Error', err);
    process.exit(1);
});

// Endpoint to generate QR code
app.get('/connect-wallet', async (req, res) => {
    try {
        console.log('Calling connectWallet...');
        const qrCode = await connectWallet();
        res.json({ qrCode });
    } catch (err) {
        logError('Connect Wallet Error', err);
        res.status(500).json({ error: 'Failed to generate QR code.' });
    }
});

// Endpoint to retrieve active sessions
app.get('/sessions', async (req, res) => {
    try {
        if (!signClient) {
            return res.status(500).json({ error: 'SignClient not initialized.' });
        }

        const sessions = signClient.session.values;
        console.log('Active Sessions:', sessions);

        if (!sessions || sessions.length === 0) {
            return res.status(200).json({ sessions: [] });
        }

        const formattedSessions = sessions.map((session) => {
            const { topic, namespaces } = session;
            const stellarNamespace = namespaces.stellar || {};
            const accounts = stellarNamespace.accounts || [];
            const publicKeys = accounts.map((account) => account.split(':')[2]);

            return {
                topic,
                namespaces,
                publicKeys,
            };
        });

        res.status(200).json({ sessions: formattedSessions });
    } catch (error) {
        logError('Session Retrieval Error', error);
        res.status(500).json({ error: 'Failed to retrieve sessions.' });
    }
});

// Test Database Endpoint
app.get('/test-db', async (req, res) => {
    try {
        const result = await db.query('SELECT NOW()');
        res.status(200).json({ message: 'Database connection successful!', timestamp: result.rows[0].now });
    } catch (error) {
        console.error('Database Connection Error:', error);
        res.status(500).json({ error: 'Failed to connect to the database.' });
    }
});

// Get User by Username Endpoint
app.get('/user/:username', async (req, res) => {
    const { username } = req.params;

    try {
        const user = await getUserByUsername(username);
        if (!user) {
            return res.status(404).json({ error: 'User not found.' });
        }

        res.status(200).json(user);
    } catch (error) {
        console.error('❌ Get User Error:', error);
        res.status(500).json({ error: 'Failed to retrieve user.' });
    }
});

// Add User Endpoint
app.post('/add-user', async (req, res) => {
    console.log('Incoming Request Headers:', req.headers);
    console.log('Raw Request Body:', req.body);

    const { username, walletAddress, telegramID, referralCode } = req.body;

    if (!username || !walletAddress || !telegramID) {
        console.log('Validation failed. Body:', req.body);
        return res.status(400).json({ error: 'Missing required fields.' });
    }

    try {
        const user = await addUser(username, walletAddress, telegramID, referralCode || null);
        res.status(201).json({ message: 'User added successfully.', user });
    } catch (error) {
        console.error('❌ Add User Error:', error);
        res.status(500).json({ error: 'Failed to add user.' });
    }
});

// Start the server
app.listen(appPort, () => {
    console.log(`✅ Server running at http://localhost:${appPort}`);
});
