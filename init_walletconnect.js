import { createAppKit } from '@reown/appkit';
import { EthersAdapter } from '@reown/appkit-adapter-ethers';
import { mainnet } from '@reown/appkit/networks';
import { SignClient } from '@walletconnect/sign-client';
import QRCode from 'qrcode';
import express from 'express'; // HTTP server to serve QR code

// Constants
const projectId = 'bfdee2a88917a9e26b82aef708214be7'; // Replace with your WalletConnect project ID
const appPort = 3000; // HTTP server port

// Metadata for your WalletConnect session
const metadata = {
  name: 'Photon Bot for Stellar',
  description: 'WalletConnect Example',
  url: 'http://localhost:3000',
  icons: ['https://assets.reown.com/reown-profile-pic.png'],
};

// Initialize AppKit
console.log('Initializing AppKit...');
const appKit = createAppKit({
  adapters: [new EthersAdapter()],
  networks: [mainnet],
  metadata,
  projectId,
});
console.log('AppKit initialized.');

// Function to generate WalletConnect QR code
async function connectWallet() {
  try {
    console.log('Initializing WalletConnect SignClient...');
    const signClient = await SignClient.init({
      projectId,
      metadata,
    });
    console.log('SignClient initialized.');

    // Create WalletConnect session
    console.log('Creating WalletConnect session...');
    const { uri } = await signClient.connect({
      requiredNamespaces: {
        stellar: {
          methods: ['stellar_signTransaction'], // Define supported Stellar methods
          chains: ['stellar:public'], // Define the Stellar public chain
          events: [], // Define supported events (if any)
        },
      },
    });

    // Generate QR Code
    const qrCodeData = await QRCode.toDataURL(uri);
    console.log('WalletConnect QR Code generated successfully.');
    return qrCodeData;
  } catch (error) {
    console.error('Error generating WalletConnect QR code:', error);
    throw error;
  }
}

// Express.js HTTP server
const app = express();

// HTTP endpoint to fetch the QR code
app.get('/connect-wallet', async (req, res) => {
  try {
    console.log('Generating QR code for Connect Wallet...');
    const qrCodeData = await connectWallet();
    res.status(200).json({ qrCode: qrCodeData });
  } catch (error) {
    res.status(500).json({ error: 'Failed to generate QR code.' });
  }
});

// Start the HTTP server
app.listen(appPort, () => {
  console.log(`Server running at http://localhost:${appPort}`);
});
