import type { AppKitNetwork } from '@reown/appkit/networks';

export const projectId = import.meta.env.VITE_PROJECT_ID || "bfdee2a88917a9e26b82aef708214be7"; // ✅ Default project ID
export const networks: AppKitNetwork[] = [
  {
    id: 'stellar:testnet',
    name: 'Stellar Testnet',
    chainNamespace: 'stellar',  // ✅ Fix: Required for AppKitNetwork type
    caipNetworkId: 'stellar:testnet',  // ✅ Fix: Required for AppKitNetwork type
    nativeCurrency: {
      name: 'Stellar Lumens',
      symbol: 'XLM',
      decimals: 7,
    },
    rpcUrls: {
      default: {
        http: ['https://horizon-testnet.stellar.org'],
      },
    },
    blockExplorers: {
      default: {
        name: 'Stellar Expert',
        url: 'https://stellar.expert/explorer/testnet/',
      },
    },
    testnet: true,
  } as unknown as AppKitNetwork,  // ✅ Force TypeScript to accept this as valid
];
