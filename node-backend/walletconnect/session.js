import { SignClient } from '@walletconnect/sign-client';
import QRCode from 'qrcode';

let signClient;

export async function initializeSignClient(projectId, metadata) {
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
        console.error('❌ WalletConnect SignClient Initialization Error:', error);
        throw error;
    }
}

export async function connectWallet() {
    try {
        if (!signClient) {
            throw new Error('SignClient not initialized.');
        }

        const session = await signClient.connect({
            requiredNamespaces: {
                stellar: {
                    chains: ['stellar:pubnet'],
                    methods: ['stellar_signAndSubmitXDR', 'stellar_signXDR'],
                    events: [],
                },
            },
        });

        const qrCodeData = await QRCode.toDataURL(session.uri); // Generate QR code for the session URI
        console.log('✅ QR Code generated for WalletConnect session.');
        return qrCodeData;
    } catch (error) {
        console.error('❌ Error generating WalletConnect QR Code:', error);
        throw error;
    }
}

export { signClient };
