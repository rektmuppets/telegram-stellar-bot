import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import os from 'os';
import { initializeSignClient, signClient, connectWallet } from './walletconnect/session.js'; // Import connectWallet
import { saveWalletLink } from './database.js';
import { logError } from './walletconnect/utils.js';
import { getUserByUsername } from './database.js';
import { db } from './database.js';

dotenv.config();

const projectId = process.env.PROJECT_ID;
const reownApiKey = process.env.REOWN_API_KEY;
const appPort = process.env.PORT;

const app = express();
app.use(cors());
app.use(express.json());

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
        const qrCode = await connectWallet(); // Use connectWallet from session.js
        res.json({ qrCode });
    } catch (err) {
        logError('Connect Wallet Error', err);
        res.status(500).json({ error: 'Failed to generate QR code.' });
    }
});

// Sessions endpoint
app.get('/sessions', async (req, res) => {
  try {
      if (!signClient) {
          return res.status(500).json({ error: 'SignClient not initialized.' });
      }

      const sessions = signClient.session.values; // Access signClient.session.values
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

app.get('/test-db', async (req, res) => {
    try {
        const result = await db.query('SELECT NOW()');
        res.status(200).json({ message: 'Database connection successful!', timestamp: result.rows[0].now });
    } catch (error) {
        console.error('Database Connection Error:', error);
        res.status(500).json({ error: 'Failed to connect to the database.' });
    }
});


// Start the server
app.listen(appPort, () => {
  console.log(`✅ Server running at http://localhost:${appPort}`);
});
