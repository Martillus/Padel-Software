# Web para el cliente (Next.js)

Todo el recorrido del jugador:

| Página | Qué hace |
|---|---|
| `/` | Portada: qué es, cómo funciona, qué verás, cómo grabar, precio y preguntas frecuentes |
| `/subir` | Asistente en 5 pasos: consejos → elegir vídeo → **marcar la pista** → detalles → enviar |
| `/analisis/[id]` | Resultado: "¿Quién eres?" (toca tu figura), tu informe, mapa de calor, logros, parejas, imagen para compartir y **chat con el entrenador IA** |
| `/analisis/demo` | Partido de ejemplo (datos simulados, sin vídeos de nadie) |
| `/mis-partidos` | Tus análisis, guardados en el dispositivo (sin cuentas) |
| `/privacidad`, `/condiciones` | Borradores, pendientes de revisión legal |

## Probarlo en tu ordenador

Necesitas **Node.js 20 o superior** (https://nodejs.org, versión LTS). En una terminal, dentro de la carpeta `web`:

```bash
npm install
```

```bash
npm run dev
```

Abre http://localhost:3000. La portada, el ejemplo y el chat (en modo demostración) funcionan ya.

### Para analizar vídeos de verdad desde la web

La web lanza el motor de Python (`engine/`) en tu ordenador. Tienes que tener el motor instalado
(ver `engine/README.md`) y decirle a la web dónde está:

1. Copia `.env.example` como `.env.local`.
2. Pon en `PADEL_ENGINE_CMD` la ruta del motor. En Windows suele ser
   `C:\...\Padel-Software\engine\.venv\Scripts\padel-engine.exe`.
3. Reinicia `npm run dev`.

Los vídeos y resultados se guardan en `web/.data/` (nunca se suben a git). Sin tarjeta gráfica,
el análisis tarda unos 4 minutos por cada minuto de vídeo.

### Para activar el chat con Claude

Pon tu clave en `ANTHROPIC_API_KEY` dentro de `.env.local` y reinicia. Al modelo solo se le envían
las estadísticas del partido y las etiquetas J1–J4: nunca el vídeo ni nombres. Cada pregunta cuesta
céntimos; hay un máximo de preguntas por partido (`CHAT_MAX_USER_MESSAGES` en `lib/config.ts`).

## Dónde cambiar cosas

- Nombre (provisional), precio y límites: `lib/config.ts`
- Colores y estilos: `app/globals.css`
- Textos de la portada: `app/page.tsx`
- Instrucciones del entrenador IA: `app/api/chat/route.ts`

## Qué falta para producción

Este modo local guarda todo en disco y ejecuta el motor en la misma máquina. Para publicar la web:

| Pieza | Ahora (local) | Producción |
|---|---|---|
| Vídeo | Se sube a la web y se guarda en disco | Subida directa a Cloudflare R2 (UE) con URL firmada |
| Trabajos | Archivos en `.data/` | Tabla `jobs` en Supabase |
| Motor | Proceso en tu ordenador | Worker con GPU en Modal |
| Pago | Modo de pruebas (no cobra) | Stripe Checkout antes de crear el análisis |
| Aviso por email | No | Email al terminar |

El código que habría que cambiar está concentrado en `lib/jobs.ts` y en el paso "Enviar" de
`components/upload/UploadWizard.tsx`.
