import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export", // Enable static export
  images: {
    unoptimized: true, // Disable image optimization for static export
  },
};

export default nextConfig;
