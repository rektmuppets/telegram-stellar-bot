import pkg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pkg;

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
});

export const db = pool;

export async function saveWalletLink(username, walletAddress, telegramID) {
    const query = `
        INSERT INTO users (username, wallet_address, telegram_id)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id) DO UPDATE
        SET wallet_address = EXCLUDED.wallet_address
        RETURNING *;
    `;
    const values = [username, walletAddress, telegramID];
    const result = await db.query(query, values);
    return result.rows[0];
}

export async function addUser(username, walletAddress, telegramID, referralCode) {
    const query = `
        INSERT INTO users (username, wallet_address, telegram_id, referral_code)
        VALUES ($1, $2, $3, $4)
        RETURNING *;
    `;
    const values = [username, walletAddress, telegramID, referralCode];
    const result = await db.query(query, values);
    return result.rows[0];
}

export async function getUserByUsername(username) {
    const query = `SELECT * FROM users WHERE username = $1;`;
    const result = await db.query(query, [username]);
    return result.rows[0];
}

export async function getUserByTelegramID(telegramID) {
    const query = `SELECT * FROM users WHERE telegram_id = $1;`;
    const result = await db.query(query, [telegramID]);
    return result.rows[0];
}
