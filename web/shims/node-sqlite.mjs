// Stub for node:sqlite — not available in the Cloudflare Workers (workerd) runtime.
// Wrangler's esbuild alias in wrangler.toml points "node:sqlite" here so the build
// succeeds.  The sqlite-cache-store code path in undici is never executed at runtime.
export const DatabaseSync = undefined;
export default undefined;
