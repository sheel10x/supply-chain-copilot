import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  devIndicators: false as any,
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
