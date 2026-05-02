/** @type {import('next').NextConfig} */
//
// BACKEND_URL controls where the /api/* proxy points. Set in:
//  - dev:  .env.local with `BACKEND_URL=http://127.0.0.1:8000`
//  - prod: passed via the Tauri sidecar launcher
// Defaults to localhost:8000 to match the sidecar uvicorn binding.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
