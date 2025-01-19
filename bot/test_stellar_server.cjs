const fetch = require('node-fetch');

const horizonUrl = 'https://horizon.stellar.org/ledgers?limit=1&order=desc';
async function testHorizonDirect() {
  try {
    const response = await fetch(horizonUrl);
    const data = await response.json();
    console.log('Latest ledger:', data._embedded.records[0]);
  } catch (error) {
    console.error('Error querying Horizon directly:', error);
  }
}

testHorizonDirect();
