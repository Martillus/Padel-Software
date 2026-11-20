// Configuración general de la web. Cambia aquí el nombre, el precio y los textos clave.

/** Nombre PROVISIONAL del producto: elige el definitivo (y comprueba que la marca está libre). */
export const APP_NAME = "PádelVisión";
export const APP_TAGLINE = "Sube tu partido. La IA te dice cómo has jugado.";

/** Precio por análisis en euros (orientativo; ver docs/DECISIONES.md, costes). */
export const PRICE_EUR = 4.99;

/** Límites de subida. */
export const MAX_VIDEO_MB = 4096;
export const MIN_RECOMMENDED_SECONDS = 120;
export const MAX_VIDEO_SECONDS = 2 * 60 * 60;

/** Mensajes de chat permitidos por análisis (controla el gasto en IA). */
export const CHAT_MAX_USER_MESSAGES = 20;

export function formatPrice(eur: number): string {
  return eur.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
}
