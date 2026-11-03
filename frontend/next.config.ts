import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-hosted Docker image (M5-01) copies the standalone server.
  output: "standalone",
};

export default nextConfig;
