import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // output: "standalone" solo para Docker; Vercel no lo necesita
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
