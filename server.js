import express from 'express';
import { generateWalletConnectURI } from './init-walletconnect.js';

const app = express();
const PORT = 3000;

// WalletConnect QR code endpoint
app.get('/walletconnect-qr', async (req, res) => {
  try {
    const qrCode = await generateWalletConnectURI();
    res.json({ qrCode });
  } catch (err) {
    console.error('Error generating WalletConnect QR:', err);
    res.status(500).send('Error generating QR code');
  }
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
