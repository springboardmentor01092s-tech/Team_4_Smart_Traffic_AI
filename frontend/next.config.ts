import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    // Prevent excessive worker thread allocation
    cpus: 2,
  },
};

export default nextConfig;

