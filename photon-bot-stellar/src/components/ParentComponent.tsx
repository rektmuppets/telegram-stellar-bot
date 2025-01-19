import React, { useState } from "react";
import WalletConnectButton from "./WalletConnectButton";
import TelegramForm from "./TelegramForm";

const ParentComponent: React.FC = () => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [sessionTopic, setSessionTopic] = useState<string | null>(null);

  const handleWalletConnect = (address: string, topic: string) => {
    setWalletAddress(address);
    setSessionTopic(topic);
    console.log("Wallet Address and Session Topic updated in ParentComponent:");
    console.log("Wallet Address:", address);
    console.log("Session Topic:", topic);
  };

  return (
    <div>
      <h1>Connect Wallet and Link Telegram</h1>
      {/* WalletConnectButton handles wallet connection */}
      <WalletConnectButton onConnect={handleWalletConnect} />

      {/* TelegramForm uses the walletAddress and sessionTopic */}
      <TelegramForm walletAddress={walletAddress} sessionTopic={sessionTopic} />
    </div>
  );
};

export default ParentComponent;
