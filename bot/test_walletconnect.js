import express from 'express';
import { SignClient } from '@walletconnect/sign-client';

const app = express();
app.use(express.json());

// Constants
const projectId = 'bfdee2a88917a9e26b82aef708214be7'; // Your WalletConnect project ID

// Metadata for your WalletConnect session
const metadata = {
  name: 'Photon Bot for Stellar',
  description: 'WalletConnect Example',
  url: 'http://localhost:3000',
  icons: ['https://assets.reown.com/reown-profile-pic.png'],
};

// Test WalletConnect session
app.get('/test-walletconnect', async (req, res) => {
  try {
    const signClient = await SignClient.init({
      projectId,
      metadata,
    });

    const session = await signClient.connect({
      requiredNamespaces: {
        stellar: {
          methods: ['stellar_signTransaction'],
          chains: ['stellar:public'],
          events: [],
        },
      },
    });

    res.json({ session });
  } catch (error) {
    console.error('Error testing WalletConnect session:', error);
    res.status(500).json({ error: 'Test failed.' });
  }
});

app.listen(3000, () => console.log('Test server running on http://localhost:3000'));
