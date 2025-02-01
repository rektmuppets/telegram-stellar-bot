import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { initializeSignClient, signClient, connectWallet } from './walletconnect/session.js';
import { saveWalletLink, getUserByUsername, addUser, db } from './database.js';
import { logError } from './walletconnect/utils.js';
import { createAddSignerTransaction, encryptPrivateKey, createRemoveSignerTransaction, fetchSequenceNumber } from './walletconnect/sep30.js';


dotenv.config();

const projectId = process.env.PROJECT_ID ||'bfdee2a88917a9e26b82aef708214be7';
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
        if (error.code === '23505') {
            // Handle duplicate key error
            return res.status(409).json({
                error: `A user with this wallet address (${walletAddress}) already exists.`,
            });
        }
        console.error('❌ Add User Error:', error);
        res.status(500).json({ error: 'Failed to add user.' });
    }
});

app.post('/forget-wallet', async (req, res) => {
    const { telegramID } = req.body;

    if (!telegramID) {
        return res.status(400).json({ error: 'Telegram ID is required.' });
    }

    try {
        // Check if the user exists
        const userQuery = 'SELECT id FROM users WHERE telegram_id = $1';
        const userResult = await db.query(userQuery, [telegramID]);

        if (userResult.rows.length === 0) {
            return res.status(404).json({ error: 'User not found.' });
        }

        // Unlink the wallet and signer
        const updateQuery = `
            UPDATE users
            SET wallet_address = NULL, signer_keypair = NULL, is_signer_connected = false
            WHERE telegram_id = $1
            RETURNING *;
        `;
        const updateResult = await db.query(updateQuery, [telegramID]);

        res.status(200).json({
            message: 'Wallet successfully unlinked.',
            user: updateResult.rows[0],
        });
    } catch (error) {
        console.error('❌ Forget Wallet Error:', error);
        res.status(500).json({ error: 'Failed to unlink wallet.' });
    }
});

app.post('/add-signer', async (req, res) => {
    const { sessionTopic, telegramID } = req.body;

    if (!sessionTopic || !telegramID) {
        return res.status(400).json({ error: 'Missing required parameters: sessionTopic or telegramID.' });
    }

    try {
        // Find the WalletConnect session
        const sessions = signClient.session.values;
        const session = sessions.find(s => s.topic === sessionTopic);

        if (!session) {
            return res.status(404).json({ error: 'Session not found for the provided sessionTopic.' });
        }

        // Extract the Stellar public key
        const stellarNamespace = session.namespaces.stellar || {};
        const accounts = stellarNamespace.accounts || [];

        if (accounts.length === 0) {
            return res.status(404).json({ error: 'No Stellar accounts found in the session.' });
        }

        const userPublicKey = accounts[0].split(':')[2];
        console.log('User Public Key:', userPublicKey);

        // Fetch the correct sequence number
        const sequenceNumber = await fetchSequenceNumber(userPublicKey);
        console.log('Fetched Sequence Number:', sequenceNumber);

        // Generate the transaction
        const { xdr, botSecret } = await createAddSignerTransaction(userPublicKey, { sequenceNumber });
        console.log('Generated Transaction XDR:', xdr);

        // Send the transaction via WalletConnect
        const response = await signClient.request({
            topic: sessionTopic,
            chainId: 'stellar:testnet',
            request: {
                method: 'stellar_signAndSubmitXDR',
                params: { xdr },
            },
        });

        if (response.status === 'success') {
            console.log('Signer added successfully!');

            // Encrypt and save the bot's private key
            const encryptedKey = encryptPrivateKey(botSecret);
            res.status(200).json({ message: 'Signer added successfully!', encryptedKey });
        } else if (response.status === 'pending') {
            console.log('Transaction is pending additional signatures.');
            res.status(200).json({ message: 'Transaction is pending additional signatures.' });
        } else {
            console.error('Failed to add signer:', response);
            res.status(500).json({ error: 'Failed to add signer.' });
        }
    } catch (error) {
        if (error.code === -32000 && error.message === 'User rejected the request') {
            console.warn('User rejected the signing request.');
            return res.status(400).json({ error: 'User rejected the signing request.' });
        }

        console.error('Error adding signer:', error);
        res.status(500).json({ error: 'Internal server error.' });
    }
});

app.post('/remove-signer', async (req, res) => {
    const { sessionTopic, telegramID, signerPublicKey } = req.body;

    if (!sessionTopic || !telegramID || !signerPublicKey) {
        return res.status(400).json({ error: 'Missing required parameters: sessionTopic, telegramID, or signerPublicKey.' });
    }

    try {
        // Step 1: Find the WalletConnect session
        const sessions = signClient.session.values;
        const session = sessions.find(s => s.topic === sessionTopic);

        if (!session) {
            return res.status(404).json({ error: 'Session not found for the provided sessionTopic.' });
        }

        // Step 2: Extract user's Stellar public key
        const stellarNamespace = session.namespaces.stellar || {};
        const accounts = stellarNamespace.accounts || [];

        if (accounts.length === 0) {
            return res.status(404).json({ error: 'No Stellar accounts found in the session.' });
        }

        const userPublicKey = accounts[0].split(':')[2];
        console.log('User Public Key:', userPublicKey);

        // Step 3: Fetch the correct sequence number for the account
        const sequenceNumber = await fetchSequenceNumber(userPublicKey);
        console.log('Fetched Sequence Number:', sequenceNumber);

        // Step 4: Generate the remove signer transaction
        const xdr = await createRemoveSignerTransaction(userPublicKey, signerPublicKey);
        console.log('Generated Remove Signer Transaction XDR:', xdr);

        // Step 5: Send the transaction via WalletConnect
        const response = await signClient.request({
            topic: sessionTopic,
            chainId: 'stellar:testnet', // Or 'stellar:testnet' if testing
            request: {
                method: 'stellar_signAndSubmitXDR',
                params: { xdr },
            },
        });

        // Step 6: Handle WalletConnect response
        if (response.status === 'success') {
            console.log('Signer removed successfully!');
            res.status(200).json({ message: 'Signer removed successfully!' });
        } else if (response.status === 'pending') {
            console.log('Transaction is pending additional signatures.');
            res.status(200).json({ message: 'Transaction is pending additional signatures.' });
        } else {
            console.error('Failed to remove signer:', response);
            res.status(500).json({ error: 'Failed to remove signer.' });
        }
    } catch (error) {
        if (error.code === -32000 && error.message === 'User rejected the request') {
            console.warn('User rejected the signing request.');
            return res.status(400).json({ error: 'User rejected the signing request.' });
        }

        console.error('Error removing signer:', error);
        res.status(500).json({ error: 'Internal server error.' });
    }
});

app.get('/reconnect/:telegramID', async (req, res) => {
    const { telegramID } = req.params;

    try {
        const user = await getUserByTelegramID(telegramID);
        if (!user || !user.session_topic) {
            return res.status(404).json({ error: 'No active session found.' });
        }

        console.log(`🔄 Reconnecting session: ${user.session_topic}`);
        const response = await signClient.request({
            topic: user.session_topic,
            chainId: 'stellar:testnet',
            request: { method: 'wallet_reconnect' }
        });

        res.json({ message: 'Session reconnected', response });
    } catch (error) {
        console.error('Reconnect error:', error);
        res.status(500).json({ error: 'Failed to reconnect session.' });
    }
});

// Start the server
app.listen(appPort, () => {
    console.log(`✅ Server running at http://localhost:${appPort}`);
});
