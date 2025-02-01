import StellarSdk from "stellar-sdk";

export const sendStellarTransaction = async (publicKey: string, secretKey: string, destination: string, amount: string) => {
  try {
    const server = new StellarSdk.Server("https://horizon-testnet.stellar.org");

    const account = await server.loadAccount(publicKey);
    const transaction = new StellarSdk.TransactionBuilder(account, {
      fee: StellarSdk.BASE_FEE,
      networkPassphrase: StellarSdk.Networks.TESTNET
    })
    .addOperation(StellarSdk.Operation.payment({
      destination,
      asset: StellarSdk.Asset.native(),
      amount
    }))
    .setTimeout(30)
    .build();

    transaction.sign(StellarSdk.Keypair.fromSecret(secretKey));
    const response = await server.submitTransaction(transaction);
    
    console.log("Transaction Successful:", response);
    return response;
  } catch (error) {
    console.error("Transaction Failed:", error);
    throw error;
  }
};
