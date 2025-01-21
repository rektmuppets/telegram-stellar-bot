import { createAppKit } from '@reown/appkit';
import { mainnet } from '@reown/appkit/networks';
import { SignClient } from '@walletconnect/sign-client';
import QRCode from 'qrcode';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Ensure essential environment variables are loaded
const projectId = process.env.PROJECT_ID;
const reownApiKey = process.env.REOWN_API_KEY;
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
  url: `https://api.photonbot.xyz`, // Update to match your domain
  icons: ['https://assets.reown.com/reown-profile-pic.png'],
};

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

const app = express();
app.use(cors());
app.use(express.json());

const linkedData = {}; // Store linked data in memory

// Reown verification endpoint
app.get('/.well-known/reown-verify', (req, res) => {
  console.log('✅ Serving Reown verification key');
  res.status(200).send(reownApiKey);
});

// Endpoint to link wallet with Telegram ID
app.post('/link-wallet', (req, res) => {
  const { telegramID, walletAddress, sessionTopic } = req.body;

  if (!telegramID || !walletAddress) {
    console.error('⚠️ Invalid data received for /link-wallet:', req.body);
    return res.status(400).json({ error: 'Invalid data received.' });
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
    const signClient = await SignClient.init({
      projectId,
      metadata,
    });

    signClient.on('session_update', (event) => {
      console.log('Session updated:', JSON.stringify(event, null, 2));
    });

    signClient.on('session_delete', (event) => {
      console.log('Session deleted:', JSON.stringify(event, null, 2));
    });

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
    console.error('⚠️ Error generating WalletConnect QR code:', error);
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

// Start the server
app.listen(appPort, () => {
  console.log(`✅ Server running at http://localhost:${appPort}`);
});
