// Empty module shim for node:sqlite (not available in Cloudflare Workers' workerd runtime).
// Used by turbopack resolveAlias to prevent undici's sqlite-cache-store from pulling in node:sqlite.
export {};
