import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for system tray deployment
  output: "export",

  // Output to 'out' directory (default for static export)
  // Will be copied to backend/frontend_dist after build
  distDir: "out",

  // Disable image optimization (not supported in static export)
  images: {
    unoptimized: true,
  },

  // Trailing slashes for static file serving
  trailingSlash: true,
};

export default nextConfig;