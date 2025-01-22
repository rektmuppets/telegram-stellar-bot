import { useState } from "react";
import Image from 'next/image';

interface WalletConnectButtonProps {
  onConnect: (address: string, topic: string) => void;
}

const WalletConnectButton: React.FC<WalletConnectButtonProps> = ({ 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onConnect 
}) => {
  const [qrCode, setQrCode] = useState<string | null>(null); // State for storing the QR code
  const [statusMessage, setStatusMessage] = useState<string>("");

  const handleConnect = async () => {
    try {
      setStatusMessage("Connecting to WalletConnect...");
      // Fetch the WalletConnect QR Code data from the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/connect-wallet`);
      if (!response.ok) {
        throw new Error("Failed to fetch WalletConnect data.");
      }
      const data = await response.json();

      if (data.qrCode) {
        setQrCode(data.qrCode); // Set the QR code state
        setStatusMessage("WalletConnect session started. Scan the QR code below.");
      } else {
        throw new Error("No QR code data received from the backend.");
      }
    } catch (error) {
      setStatusMessage("Failed to connect wallet.");
      console.error("Error connecting wallet:", error);
    }
  };

  return (
    <div>
      <button onClick={handleConnect}>Connect Wallet</button>
      <p>{statusMessage}</p>
      {qrCode && <Image src={qrCode} alt="WalletConnect QR Code" width={400} height={400} />}
    </div>
  );
};

export default WalletConnectButton;