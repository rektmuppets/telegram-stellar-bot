import { createAppKit } from '@reown/appkit';
import { mainnet } from '@reown/appkit/networks';
import { SignClient } from '@walletconnect/sign-client';
import QRCode from 'qrcode';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import os from 'os';

// Load environment variables
dotenv.config();

const projectId = process.env.PROJECT_ID || 'bfdee2a88917a9e26b82aef708214be7';
const reownApiKey = process.env.REOWN_API_KEY || 'c0a1c1e4-83db-4d0a-9322-483fa104f3ec';
const appPort = process.env.PORT || 4000;

if (!projectId) {
  throw new Error("PROJECT_ID is not defined in the environment variables.");
}
if (!reownApiKey) {
  throw new Error("REOWN_API_KEY is not defined in the environment variables.");
}

console.log(`✅ Loaded PROJECT_ID: ${projectId}`);
console.log(`✅ Loaded REOWN_API_KEY: ${reownApiKey}`);
console.log(`✅ Loaded PORT: ${appPort}`);

// Metadata for WalletConnect session
const metadata = {
  name: 'Photon Bot for Stellar',
  description: 'WalletConnect Example',
  url: `https://api.photonbot.xyz`,
  icons: ['https://assets.reown.com/reown-profile-pic.png'],
};

const app = express();
app.use(cors());
app.use(express.json());

let signClient;
const errorLog = []; // Keep track of errors
const linkedData = {}; // Store linked data in memory

// Initialize AppKit
let appKit;
try {
  appKit = createAppKit({
    networks: [mainnet],
    metadata,
    projectId,
  });
  console.log('✅ AppKit initialized successfully.');
} catch (err) {
  console.error('⚠️ Failed to initialize AppKit:', err);
  process.exit(1);
}

// Initialize WalletConnect SignClient
async function initializeSignClient() {
  try {
    signClient = await SignClient.init({
      projectId,
      metadata,
    });
    console.log('✅ WalletConnect SignClient initialized.');

    signClient.on('session_update', (event) => {
      console.log('🔄 Session updated:', JSON.stringify(event, null, 2));
    });

    signClient.on('session_delete', (event) => {
      console.log('🗑️ Session deleted:', JSON.stringify(event, null, 2));
    });
  } catch (error) {
    logError('SignClient Initialization Error', error);
    process.exit(1);
  }
}

// Log errors to memory for debugging
function logError(context, error) {
  const timestamp = new Date().toISOString();
  const message = typeof error === 'string' ? error : error.message || JSON.stringify(error);
  errorLog.push({ timestamp, context, message });
  console.error(`❌ [${timestamp}] ${context}: ${message}`);
}

// Health check endpoint
app.get('/health', (req, res) => {
  const uptime = process.uptime();
  const memoryUsage = process.memoryUsage();
  const cpuUsage = os.loadavg();
  res.status(200).json({
    status: 'healthy',
    uptime,
    memoryUsage,
    cpuUsage,
    recentErrors: errorLog.slice(-5), // Last 5 errors
  });
});

// Endpoint to link wallet with Telegram ID
app.post('/link-wallet', (req, res) => {
  const { telegramID, walletAddress, sessionTopic } = req.body;

  if (!telegramID || !walletAddress) {
    const error = 'Invalid data received for /link-wallet';
    logError(error, req.body);
    return res.status(400).json({ error });
  }

  linkedData[telegramID] = { walletAddress, sessionTopic };
  console.log(`✅ Linked Telegram ID ${telegramID} to wallet ${walletAddress}`);
  res.status(200).json({ message: 'Telegram ID linked successfully!' });
});

// Endpoint to get wallet details by Telegram ID
app.get('/link-wallet/:telegramID', (req, res) => {
  const { telegramID } = req.params;
  const walletData = linkedData[telegramID];

  if (walletData) {
    res.status(200).json(walletData);
  } else {
    res.status(404).json({ error: 'No wallet linked to this Telegram ID.' });
  }
});

// Function to connect wallet and generate WalletConnect QR code
async function connectWallet() {
  try {
    const session = await signClient.connect({
      requiredNamespaces: {
        stellar: {
          chains: ['stellar:pubnet'],
          methods: ['stellar_signAndSubmitXDR', 'stellar_signXDR'],
          events: [],
        },
      },
    });

    const qrCodeData = await QRCode.toDataURL(session.uri);
    return qrCodeData;
  } catch (error) {
    logError('QR Code Generation Error', error);
    throw error;
  }
}

// Endpoint to generate WalletConnect QR code
app.get('/connect-wallet', async (req, res) => {
  try {
    const qrCodeData = await connectWallet();
    res.status(200).json({ qrCode: qrCodeData });
  } catch (error) {
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
    if (!sessions || sessions.length === 0) {
      // Return an empty array if no sessions exist
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

// Start the server
initializeSignClient().then(() => {
  app.listen(appPort, () => {
    console.log(`✅ Server running at http://localhost:${appPort}`);
  });
});

// Uncaught exception handling
process.on('uncaughtException', (error) => {
  logError('Uncaught Exception', error);
});

process.on('unhandledRejection', (reason) => {
  logError('Unhandled Rejection', reason);
});
