import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production Docker image small (see
  // docker/frontend/Dockerfile's `runner` stage) — it bundles only the
  // traced dependency subset instead of the full node_modules tree.
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
