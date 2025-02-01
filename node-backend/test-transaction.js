import express from 'express';
import cors from 'cors';
import axios from 'axios'; // ✅ Fetch session from your running WalletConnect session server
import dotenv from 'dotenv';
import { signClient } from './walletconnect/session.js';

dotenv.config();
const app = express();
const appPort = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// ✅ Fetch the active WalletConnect session topic dynamically
async function getActiveSessionTopic() {
    try {
        const response = await axios.get('http://localhost:4000/sessions'); // ✅ Fetch session from your session server
        const sessions = response.data.sessions; // ✅ Ensure this matches the JSON format
        if (sessions && sessions.length > 0) {
            return sessions[0].topic; // ✅ Return the first active session topic
        } else {
            return null;
        }
    } catch (error) {
        console.error('❌ Error fetching WalletConnect session:', error);
        return null;
    }
}

// ✅ Endpoint to Sign & Submit XDR Transactions via WalletConnect
app.post('/sign-transaction', async (req, res) => {
    try {
        const { xdr } = req.body;

        const sessionTopic = await getActiveSessionTopic(); // ✅ Fetch the correct topic
        if (!sessionTopic) {
            return res.status(404).json({ error: 'No active WalletConnect sessions found.' });
        }

        if (!signClient) {
            return res.status(500).json({ error: 'WalletConnect SignClient not initialized.' });
        }

        // 🔹 Check if the session exists
        const session = signClient.session.get(sessionTopic);
        if (!session) {
            return res.status(404).json({ error: 'Session not found in WalletConnect SignClient.' });
        }

        console.log(`🔹 Signing transaction via WalletConnect: ${xdr}`);

        // 🔹 Send the XDR transaction for signing
        const response = await signClient.request({
            topic: sessionTopic,
            chainId: 'stellar:testnet', // Change to 'stellar:public' for mainnet
            request: {
                method: 'stellar_signAndSubmitXDR',
                params: { xdr },
            },
        });

        console.log(`✅ Signed Transaction Response:`, response);

        // 🔹 Return the signed transaction
        res.status(200).json({ signedXDR: response.result || response });
    } catch (error) {
        console.error('❌ Error signing transaction:', error);
        res.status(500).json({ error: 'Failed to sign transaction.' });
    }
});

// ✅ Start the server
app.listen(appPort, () => {
    console.log(`✅ WalletConnect Transaction Server running at http://localhost:${appPort}`);
});
