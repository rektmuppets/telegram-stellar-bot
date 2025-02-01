import { useDisconnect, useAppKit } from '@reown/appkit/react';

export const ActionButtonList = () => {
    const { disconnect } = useDisconnect();
    const { open } = useAppKit();

    const handleDisconnect = async () => {
      try {
        await disconnect();
      } catch (error) {
        console.error("Failed to disconnect:", error);
      }
    };

  return (
    <div>
        <button onClick={() => open()}>Open</button>
        <button onClick={handleDisconnect}>Disconnect</button>
    </div>
  );
};
