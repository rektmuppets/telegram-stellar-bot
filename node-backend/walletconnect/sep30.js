import StellarBase from '@stellar/stellar-base';
import crypto from 'crypto';
import axios from 'axios'; // For Horizon API requests

// Function to fetch the sequence number for a Stellar account
export async function fetchSequenceNumber(publicKey) {
    try {
        const response = await axios.get(`https://horizon-testnet.stellar.org/accounts/${publicKey}`); // Testnet URL
        return response.data.sequence;
    } catch (error) {
        console.error('Failed to fetch sequence number:', error.message);
        throw new Error('Unable to fetch sequence number from Horizon.');
    }
}

// Function to create a SEP-30 transaction for adding a lightweight signer with proper thresholds
export async function createAddSignerTransaction(userPublicKey) {
    const sequenceNumber = await fetchSequenceNumber(userPublicKey);

    // Generate lightweight signer keypair
    const botKeypair = StellarBase.Keypair.random();
    console.log(`Generated Bot Public Key: ${botKeypair.publicKey()}`);
    console.log(`Generated Bot Secret Key: ${botKeypair.secret()}`); // Secure this

    // Build the transaction with updated thresholds and signer weights
    const transaction = new StellarBase.TransactionBuilder(
        new StellarBase.Account(userPublicKey, sequenceNumber),
        {
            fee: StellarBase.BASE_FEE,
            networkPassphrase: StellarBase.Networks.TESTNET,
        }
    )
        // Step 1: Set thresholds (low = 2, medium = 3, high = 5)
        .addOperation(StellarBase.Operation.setOptions({
            lowThreshold: 2,  // Bot can add trustlines
            medThreshold: 3,  // Bot can execute trades (DEX swaps)
            highThreshold: 5, // Bot CANNOT withdraw or remove signers
            masterWeight: 3,   // Ensure master has full control
        }))
        // Step 2: Add lightweight bot signer with weight 3
        .addOperation(StellarBase.Operation.setOptions({
            signer: {
                ed25519PublicKey: botKeypair.publicKey(),
                weight: 3, // Bot can add trustlines & trade, but not withdraw
            },
        }))
        .setTimeout(30)
        .build();

    // Return the XDR and bot's secret key
    return {
        xdr: transaction.toXDR(),
        botSecret: botKeypair.secret(),
    };
}

// Function to create a transaction for removing the lightweight signer
export async function createRemoveSignerTransaction(userPublicKey, signerPublicKey) {
    const sequenceNumber = await fetchSequenceNumber(userPublicKey);

    const transaction = new StellarBase.TransactionBuilder(
        new StellarBase.Account(userPublicKey, sequenceNumber),
        {
            fee: StellarBase.BASE_FEE,
            networkPassphrase: StellarBase.Networks.TESTNET,
        }
    )
        // Adjust thresholds to allow signer removal
        .addOperation(StellarBase.Operation.setOptions({
            lowThreshold: 1,
            medThreshold: 2,
            highThreshold: 2, // Ensures account remains usable
        }))
        // Remove the lightweight signer
        .addOperation(StellarBase.Operation.setOptions({
            signer: {
                ed25519PublicKey: signerPublicKey,
                weight: 0, // Remove signer by setting weight to 0
            },
        }))
        .setTimeout(30)
        .build();

    // Return the XDR
    return transaction.toXDR();
}

// Optional: Function to encrypt the bot's private key before saving to the database
export function encryptPrivateKey(secretKey) {
    const algorithm = 'aes-256-ctr';
    const key = process.env.ENCRYPTION_KEY; // 32-byte key from .env
    const iv = crypto.randomBytes(16);

    const cipher = crypto.createCipheriv(algorithm, key, iv);
    const encrypted = Buffer.concat([cipher.update(secretKey), cipher.final()]);

    return `${iv.toString('hex')}:${encrypted.toString('hex')}`;
}
