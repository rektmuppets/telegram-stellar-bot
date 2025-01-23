import React, { useState, useEffect } from "react";
import WalletConnectButton from "./WalletConnectButton";
import TelegramForm from "./TelegramForm";

const ParentComponent: React.FC = () => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [sessionTopic, setSessionTopic] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(true);

  useEffect(() => {
    const fetchSessionDetails = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/sessions`);
        if (!response.ok) {
          if (response.status === 404) {
            console.log("No active sessions found.");
          } else {
            throw new Error("Failed to fetch session details.");
          }
          return;
        }

        const { sessions } = await response.json();
        const [firstSession] = sessions || [];

        if (firstSession?.publicKeys?.length) {
          setWalletAddress(firstSession.publicKeys[0]); // Stellar wallet address
          setSessionTopic(firstSession.topic); // WalletConnect session topic
          setIsPolling(false); // Stop polling once a session is found
        }
      } catch (error) {
        console.error("Error fetching session details:", error);
      }
    };

    if (isPolling) {
      const interval = setInterval(fetchSessionDetails, 5000); // Poll every 5 seconds
      fetchSessionDetails(); // Initial fetch
      return () => clearInterval(interval); // Cleanup on unmount
    }
  }, [isPolling]);

  return (
    <div>
      <h1>Connect Wallet and Link Telegram</h1>
      {!walletAddress || !sessionTopic ? (
        <>
          <p>Please connect your wallet.</p>
          <WalletConnectButton onConnect={() => setIsPolling(true)} />
        </>
      ) : (
        <TelegramForm walletAddress={walletAddress} sessionTopic={sessionTopic} />
      )}
    </div>
  );
};

export default ParentComponent;
