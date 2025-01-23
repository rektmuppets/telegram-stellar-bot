import React, { useState, useEffect } from "react";
import WalletConnectButton from "./WalletConnectButton";
import TelegramForm from "./TelegramForm";

const ParentComponent: React.FC = () => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [sessionTopic, setSessionTopic] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSessionDetails = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/sessions`);
        if (!response.ok) {
          if (response.status === 404) {
            setSessionError("No active sessions found. Please connect your wallet.");
          } else {
            throw new Error("Failed to fetch session details.");
          }
          return;
        }

        const { sessions } = await response.json();
        if (!sessions || sessions.length === 0) {
          setSessionError("No active sessions found. Please connect your wallet.");
          return;
        }

        const [firstSession] = sessions;

        // Ensure session data has publicKeys and topic
        if (firstSession && firstSession.publicKeys?.length > 0) {
          setWalletAddress(firstSession.publicKeys[0]); // Stellar wallet address
          setSessionTopic(firstSession.topic); // WalletConnect session topic
        } else {
          setSessionError("Session data is incomplete. Please reconnect your wallet.");
        }
      } catch (error) {
        console.error("Error fetching session details:", error);
        setSessionError("An error occurred while retrieving session details.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchSessionDetails();
  }, []);

  const handleWalletConnect = (address: string, topic: string) => {
    setWalletAddress(address);
    setSessionTopic(topic);
    setSessionError(null); // Clear any previous errors
  };

  return (
    <div>
      <h1>Connect Wallet and Link Telegram</h1>
      {isLoading ? (
        <p>Loading session details...</p>
      ) : sessionError ? (
        <div>
          <p>{sessionError}</p>
          <WalletConnectButton onConnect={handleWalletConnect} />
        </div>
      ) : (
        <>
          <WalletConnectButton onConnect={handleWalletConnect} />
          <TelegramForm walletAddress={walletAddress} sessionTopic={sessionTopic} />
        </>
      )}
    </div>
  );
};

export default ParentComponent;
