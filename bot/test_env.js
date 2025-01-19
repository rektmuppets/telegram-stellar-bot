import fs from 'fs';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the current directory of the script
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Resolve the path to the .env file in the project root
const envPath = path.resolve(__dirname, '../.env');

console.log(`Checking .env file existence at: ${envPath}`);

if (!fs.existsSync(envPath)) {
  console.error('❌ .env file not found at the specified path.');
} else {
  console.log('✅ .env file found.');
  
  console.log('Loading environment variables from project root...');
  dotenv.config({ path: envPath });

  console.log('Loaded variables:', {
    PROJECT_ID: process.env.PROJECT_ID,
    PORT: process.env.PORT,
  });
}
