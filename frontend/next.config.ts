import type { NextConfig } from "next";

console.log("---------------------------------");
console.log("Loading next.config.ts");
console.log("API_URL env var:", process.env.API_URL);
console.log("---------------------------------");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const isProd = process.env.NODE_ENV === "production";
    const fallbackUrl = isProd ? "http://backend:37453/api/:path*" : "http://127.0.0.1:37453/api/:path*";
    const apiUrl = process.env.API_URL || fallbackUrl;
    console.log("Rewrite destination:", apiUrl);
    return [
      {
        source: "/api/:path*",
        destination: apiUrl,
      },
    ];
  },
};

export default nextConfig;