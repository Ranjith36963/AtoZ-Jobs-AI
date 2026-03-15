import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Turbopack is enabled via --turbopack flag in dev script
  // Security: sanitize server component inputs (CVE-2025-66478)
  serverExternalPackages: [],
  // Prevent undici's sqlite-cache-store from pulling in node:sqlite
  // (not available in Cloudflare Workers' workerd runtime)
  turbopack: {
    resolveAlias: {
      'node:sqlite': './shims/empty.ts',
    },
  },
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.resolve.alias['node:sqlite'] = false;
    }
    return config;
  },
};

export { nextConfig as default };
