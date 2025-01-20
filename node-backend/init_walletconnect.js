import { createAppKit } from '@reown/appkit';
import { mainnet } from '@reown/appkit/networks';
import { SignClient } from '@walletconnect/sign-client';
import QRCode from 'qrcode';
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// Load environment variables (dotenv automatically looks for .env if present)
dotenv.config();

// Ensure PROJECT_ID is loaded
const projectId = process.env.PROJECT_ID;
if (!projectId) {
  console.error("⚠️ PROJECT_ID is not defined in the environment variables.");
  throw new Error("PROJECT_ID is required to initialize WalletConnect.");
}

const appPort = process.env.PORT || 4000; // Use PORT from .env or default to 4000

console.log(`✅ Loaded PROJECT_ID: ${projectId}`);
console.log(`✅ Loaded PORT: ${appPort}`);

// Metadata for WalletConnect session
const metadata = {
  name: 'Photon Bot for Stellar',
  description: 'WalletConnect Example',
  url: `http://localhost:${appPort}`, // Update this to your domain later
  icons: ['https://assets.reown.com/reown-profile-pic.png'],
};

// Initialize AppKit
console.log('Initializing AppKit...');
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

// Endpoint to link wallet with Telegram ID
app.post('/link-wallet', (req, res) => {
  const { telegramID, walletAddress, sessionTopic } = req.body;

  if (!telegramID || !walletAddress) {
    console.error('⚠️ Invalid data received for /link-wallet:', req.body);
    return res.status(400).json({ error: 'Invalid data received.' });
  }

  console.log(`✅ Linked Telegram ID ${telegramID} to wallet ${walletAddress}`);
  linkedData[telegramID] = { walletAddress, sessionTopic };

  res.status(200).json({ message: 'Telegram ID linked successfully!' });
});

// Endpoint to get wallet details by Telegram ID
app.get('/link-wallet/:telegramID', (req, res) => {
  const { telegramID } = req.params;

  console.log(`Fetching wallet details for Telegram ID: ${telegramID}`);
  if (linkedData[telegramID]) {
    res.status(200).json(linkedData[telegramID]);
  } else {
    console.warn(`⚠️ No wallet linked to Telegram ID: ${telegramID}`);
    res.status(404).json({ error: 'No wallet linked to this Telegram ID.' });
  }
});

// Function to connect wallet and generate WalletConnect QR code
async function connectWallet() {
  try {
    console.log('Initializing WalletConnect SignClient...');
    const signClient = await SignClient.init({
      projectId,
      metadata,
    });
    console.log('✅ SignClient initialized successfully.');

    signClient.on('session_update', (event) => {
      console.log('Session updated:', JSON.stringify(event, null, 2));
    });

    signClient.on('session_delete', (event) => {
      console.log('Session deleted:', JSON.stringify(event, null, 2));
    });

    console.log('Creating WalletConnect session...');
    const session = await signClient.connect({
      requiredNamespaces: {
        stellar: {
          chains: ['stellar:pubnet'],
          methods: ['stellar_signTransaction'],
          events: [],
        },
      },
    });

    console.log(
      'Session Payload:',
      JSON.stringify(
        {
          requiredNamespaces: {
            stellar: {
              chains: ['stellar:pubnet'],
              methods: ['stellar_signTransaction'],
              events: [],
            },
          },
        },
        null,
        2
      )
    );

    console.log('Waiting for session details to populate...');
    await new Promise((resolve) => setTimeout(resolve, 10000)); // 10-second delay

    if (session.namespaces && session.namespaces['stellar:pubnet']) {
      console.log(
        '✅ Namespaces:',
        JSON.stringify(session.namespaces['stellar:pubnet'], null, 2)
      );
    } else {
      console.warn('⚠️ Namespaces are missing from the session.');
    }

    const qrCodeData = await QRCode.toDataURL(session.uri);
    console.log('✅ WalletConnect QR Code generated successfully.');
    return qrCodeData;
  } catch (error) {
    console.error('⚠️ Error generating WalletConnect QR code:', error);
    throw error;
  }
}

// Endpoint to generate WalletConnect QR code
app.get('/connect-wallet', async (req, res) => {
  try {
    console.log('Generating QR code for Connect Wallet...');
    const qrCodeData = await connectWallet();
    res.status(200).json({ qrCode: qrCodeData });
  } catch (error) {
    console.error('⚠️ Error in /connect-wallet endpoint:', error);
    res.status(500).json({ error: 'Failed to generate QR code.' });
  }
});

app.listen(appPort, () => {
  console.log(`✅ Server running at http://localhost:${appPort}`);
});
