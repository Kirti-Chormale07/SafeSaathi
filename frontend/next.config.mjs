/** Next.js config: proxies /api/* to the FastAPI backend (no CORS needed). */
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8010";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
