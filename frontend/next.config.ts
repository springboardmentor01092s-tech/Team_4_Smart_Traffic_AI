import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // Prevent excessive worker thread allocation
    cpus: 2,
  },
};

export default nextConfig;
