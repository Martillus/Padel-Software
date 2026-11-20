import type { MetadataRoute } from "next";

// Versión de prueba: que ningún buscador la indexe.
export default function robots(): MetadataRoute.Robots {
  return { rules: [{ userAgent: "*", disallow: "/" }] };
}
