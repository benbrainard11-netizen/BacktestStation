/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so the bundle can be served from a Tauri webview.
  // Rewrites in `next dev` still apply, but production output is HTML/JS only.
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
