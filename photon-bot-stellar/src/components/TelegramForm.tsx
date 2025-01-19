import React, { useState } from "react";

// Interface for props
interface TelegramFormProps {
  walletAddress: string | null;
  sessionTopic: string | null;
}

const TelegramForm: React.FC<TelegramFormProps> = ({ walletAddress, sessionTopic }) => {
  const [telegramId, setTelegramId] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    try {
      // Send data to the backend
      const response = await fetch("http://localhost:4000/link-wallet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegramID: telegramId,
          walletAddress,
          sessionTopic,
        }),
      });

      if (response.ok) {
        // Success message
        setStatusMessage("Telegram ID linked successfully!");
      } else {
        // Error message from backend
        setStatusMessage("Failed to link Telegram ID. Please try again.");
      }
    } catch (error) {
      console.error("Error linking Telegram ID:", error);
      setStatusMessage("An error occurred. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <p>Wallet Address: {walletAddress || "Not connected"}</p>
      <p>Session Topic: {sessionTopic || "No session"}</p>
      <label htmlFor="telegramId">Telegram ID:</label>
      <input
        id="telegramId"
        type="text"
        value={telegramId}
        onChange={(e) => setTelegramId(e.target.value)}
        placeholder="Enter your Telegram ID"
      />
      <button type="submit">Link Telegram ID</button>
      {statusMessage && <p>{statusMessage}</p>}
    </form>
  );
};

export default TelegramForm;
