# **Photon Bot for Stellar**

Photon Bot for Stellar is a dApp that combines the power of Stellar blockchain with Telegram automation. It enables users to connect their Stellar wallets, link them to their Telegram accounts, and automate trades using a lightweight signer and WalletConnect.

---

## **Features**
### **Frontend**
- **WalletConnect Integration (Placeholder)**:
  - Users can connect their Stellar wallets via a WalletConnect QR code.
  - A mock implementation is currently used for development purposes.
  
- **Telegram Linking**:
  - Users can link their Telegram accounts to their wallet addresses.
  - A form is available to capture the Telegram username or ID.

- **User-Friendly UI**:
  - Simple interface with clear sections for wallet connection and Telegram linking.

### **Backend (Planned/Mocked)**
- **Session Management**:
  - Backend handles WalletConnect sessions and relays session data to the Telegram bot.
  - Uses Node.js with potential lightweight session storage like Redis.

- **Secure User Mapping**:
  - Plans to encrypt Telegram IDs before storing them in the database for enhanced security.

### **Telegram Bot**
- Automates trading using Stellar's SEP-30 lightweight signer.
- Associates wallet addresses with Telegram users to enable secure and seamless transactions.

---

## **Tech Stack**
### **Frontend**
- **Next.js**: Framework for the static frontend.
- **Typescript**: Ensures type safety across the codebase.
- **Reown AppKit**: For WalletConnect integration (planned).
- **CSS Styling**: Custom styles without using heavy frameworks like Tailwind (optional for future).

### **Backend**
- **Node.js**: Handles WalletConnect sessions and acts as a bridge between the frontend and Telegram bot.
- **Redis (Optional)**: Temporary session storage for real-time processing.

### **Database (Planned)**
- **PostgreSQL/MySQL**: To store user mappings securely (wallet address ↔ Telegram ID).

### **Telegram Bot**
- **Python**: Automates trading using Stellar’s SEP-30 lightweight signer.

---

## **Setup and Installation**

### **1. Clone the Repository**
```bash
git clone https://github.com/<your-username>/photon-bot-stellar.git
cd photon-bot-stellar
