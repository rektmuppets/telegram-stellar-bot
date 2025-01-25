// utils.js
export function logError(context, error) {
    const timestamp = new Date().toISOString();
    const message = typeof error === 'string' ? error : error.message || JSON.stringify(error);
    console.error(`❌ [${timestamp}] ${context}: ${message}`);
}
