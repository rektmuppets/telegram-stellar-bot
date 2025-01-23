import React, { useState } from "react";

interface TelegramFormProps {
  walletAddress: string | null;
  sessionTopic: string | null;
}

const TelegramForm: React.FC<TelegramFormProps> = ({ walletAddress, sessionTopic }) => {
  const [telegramId, setTelegramId] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!walletAddress || !sessionTopic) {
      setStatusMessage("Please connect your wallet first.");
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/link-wallet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegramID: telegramId,
          walletAddress,
          sessionTopic,
        }),
      });

      if (response.ok) {
        setStatusMessage("Telegram ID linked successfully!");
      } else {
        setStatusMessage("Failed to link Telegram ID. Please try again.");
      }
    } catch (error) {
      console.error("Error linking Telegram ID:", error);
      setStatusMessage("An error occurred. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {!walletAddress || !sessionTopic ? (
        <p>Please connect your wallet before linking your Telegram ID.</p>
      ) : (
        <>
          <p>Wallet Address: {walletAddress}</p>
          <p>Session Topic: {sessionTopic}</p>
          <label htmlFor="telegramId">Telegram ID:</label>
          <input
            id="telegramId"
            type="text"
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            placeholder="Enter your Telegram ID"
          />
          <button type="submit">Link Telegram ID</button>
        </>
      )}
      {statusMessage && <p>{statusMessage}</p>}
    </form>
  );
};

export default TelegramForm;
