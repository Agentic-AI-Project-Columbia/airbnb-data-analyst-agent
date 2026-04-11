import type { NextConfig } from "next";

const backendUrl = new URL(
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
);
const artifactPattern = new URL("/artifacts/**", backendUrl);

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [artifactPattern],
  },
};

export default nextConfig;
