import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  devIndicators: false as any,
};

export default nextConfig;
