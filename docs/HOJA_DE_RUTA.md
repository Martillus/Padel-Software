# Hoja de ruta

## Fase 1 — Motor (en curso)

Hecho:
- [x] Calibración por puntos y homografía píxel → metros, con imagen de control
- [x] Detección de personas/bola con detectores intercambiables (YOLO, torchvision, replay)
- [x] Seguimiento J1–J4 en metros con nombres estables por posición
- [x] Métricas: distancia, velocidades, zonas (red/transición/fondo), sprints, pareja
- [x] Mapas de calor y recorridos en PNG
- [x] Informe en español con IA (solo métricas) y respaldo de plantilla
- [x] Vídeo sintético con verdad conocida y tests automáticos

Siguiente (necesita tus vídeos reales):
- [ ] Grabar 5–10 vídeos propios siguiendo `docs/GRABACION.md` (partido y entrenamiento)
- [ ] Ejecutar el motor con ellos, revisar `calibracion_check.png` y `video_anotado.mp4`
- [ ] Ajustar umbrales (zonas, velocidades, reglas de ejercicios) con 1–2 entrenadores
- [ ] Medir `segundos_computo_por_minuto_video` en GPU para cerrar el coste real
- [ ] Empaquetar el motor como función de Modal (inicio de la fase 2)

## Bola y golpes (la parte difícil, en paralelo a la fase 2)

1. **Anotar datos**: marcar la bola en ~3.000–5.000 fotogramas de nuestros vídeos
   (herramienta tipo CVAT/Label Studio). Solo con vídeos cuyos responsables hayan dado
   permiso explícito para entrenar modelos (ver `docs/LEGAL.md`).
2. **Modelo de bola** tipo TrackNet (usa 3 fotogramas seguidos para ver la bola borrosa).
3. **Botes y golpes** a partir de la trayectoria de la bola.
4. **Tipo de golpe** (derecha, revés, volea, bandeja, víbora, remate, globo...) con la
   pose del jugador (esqueleto, sin rasgos faciales) + trayectoria. Requiere varios miles
   de golpes etiquetados. Objetivo realista inicial: 4–5 categorías amplias con >80 % de
   acierto, y ampliar después.
5. **Errores repetidos** (bola a la red, fuera, etc.): necesita bola fiable + reglas del
   punto. Es lo último en llegar.

Mientras tanto, el producto aporta valor con lo fiable: posiciones, zonas, pareja,
recorridos, evolución en el tiempo y recomendaciones.

## Fase 2 — Web mínima (piloto gratuito)

Cuentas que tendrás que crear (te diré el momento exacto):
- Supabase (proyecto en región **Frankfurt**)
- Cloudflare (R2 con **jurisdicción UE**)
- Modal (worker GPU)
- Vercel (web; revisar región de las funciones)
- Anthropic (clave de API)
Las variables necesarias están en `.env.example`.
