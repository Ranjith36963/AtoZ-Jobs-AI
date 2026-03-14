import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Turbopack is enabled via --turbopack flag in dev script
  // Security: sanitize server component inputs (CVE-2025-66478)
  serverExternalPackages: [],
};

export { nextConfig as default };
