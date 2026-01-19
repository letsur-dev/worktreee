import type { NextConfig } from "next";

const apiUrl = process.env.API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // API 서버로 프록시
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: "/v1/:path*",
        destination: `${apiUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
