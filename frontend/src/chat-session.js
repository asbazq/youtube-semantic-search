// getRandomValues is available on HTTP LAN deployments as well as HTTPS.
export function createChatSessionId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
}
