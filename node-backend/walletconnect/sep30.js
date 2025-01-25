const { TransactionBuilder, Networks, Keypair } = require('stellar-sdk');
const { encrypt } = require('./utils'); // Helper for encryption
const { saveSigner } = require('../database');

// Create SEP-30 transaction to add lightweight signer
async function createAddSignerTransaction(userPublicKey) {
    const botKeypair = Keypair.random(); // Generate bot keypair
    const transaction = new TransactionBuilder(userPublicKey, {
        fee: '100',
        networkPassphrase: Networks.PUBLIC,
    })
        .addOperation({
            type: 'setOptions',
            signer: { ed25519PublicKey: botKeypair.publicKey(), weight: 1 },
        })
        .setTimeout(30)
        .build();

    return {
        xdr: transaction.toXDR(),
        botPrivateKey: botKeypair.secret(), // Save this securely
    };
}

// Initiate signer setup and save the signer to the database
async function setupSigner(userPublicKey, telegramID) {
    const { xdr, botPrivateKey } = await createAddSignerTransaction(userPublicKey);

    // Encrypt private key and save it to the database
    const encryptedPrivateKey = encrypt(botPrivateKey);
    await saveSigner({ telegramID, walletAddress: userPublicKey, encryptedPrivateKey });

    return xdr; // Return XDR for signing
}

module.exports = { setupSigner };
