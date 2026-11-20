import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // En Vercel aún no hay motor de análisis en la nube: la subida de vídeos se desactiva
  // (se puede forzar con NEXT_PUBLIC_UPLOADS_ENABLED=true cuando esté el worker).
  env: {
    NEXT_PUBLIC_UPLOADS_ENABLED: process.env.NEXT_PUBLIC_UPLOADS_ENABLED ?? (process.env.VERCEL ? "false" : "true"),
  },
  // Los datos del partido de ejemplo se leen del disco en las rutas de la API.
  outputFileTracingIncludes: { "/api/**": ["./data/demo/**"], "/analisis/**": ["./data/demo/**"] },
  async headers() {
    return [{ source: "/:path*", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }];
  },
};

export default nextConfig;
