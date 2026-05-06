/** @type {import('next').NextConfig} */
//
// BACKEND_URL — points at the BacktestStation FastAPI (default :8000).
// SIDECAR_URL — points at research_sidecar's HTTP API (default :9000).
//
// Both are localhost on the dev box and on the production server (the
// sidecar lives co-located with BacktestStation per SIMPLIFY_PLAN.md).
// On the server, Tailscale binding happens at the uvicorn host level —
// these proxies still hit 127.0.0.1.
//
// Set in:
//   dev:  .env.local with `BACKEND_URL=http://127.0.0.1:8000`
//                    and `SIDECAR_URL=http://127.0.0.1:9000`
//   prod: passed via the service launcher / NSSM env block.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const SIDECAR_URL = process.env.SIDECAR_URL || "http://localhost:9000";

const nextConfig = {
  async rewrites() {
    return [
      // Sidecar (research) — must come BEFORE the catch-all /api/:path*
      // so /api/sidecar/* doesn't get sent to the BacktestStation backend.
      {
        source: "/api/sidecar/:path*",
        destination: `${SIDECAR_URL}/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
