# Motor de análisis (fase 1)

Recibe **un vídeo + la calibración de la pista** y devuelve:

| Fichero | Contenido |
|---|---|
| `analisis.json` | Métricas por jugador y por pareja, mapa de calor en celdas, golpes estimados, limitaciones, tiempos de cómputo |
| `informe.md` | Informe en español (con IA si hay `ANTHROPIC_API_KEY`; si no, plantilla) |
| `mapa_calor_J*.png` | Mapa de calor de cada jugador sobre la pista |
| `recorridos.png` | Recorridos de todos los jugadores |
| `calibracion_check.png` | Líneas de la pista proyectadas sobre el vídeo: **revísala siempre** |
| `trayectorias.json` | Posición (t, x, y) en metros de cada jugador, para la evolución y la web |
| `detecciones.json` | Detecciones en bruto: permiten recalcular sin volver a pagar GPU |
| `video_anotado.mp4` | (opcional) vídeo con cajas, etiquetas y minimapa |

## Cómo funciona (en sencillo)

1. **Calibración**: marcas 4–6 puntos de la pista en un fotograma (esquinas, postes de la
   red, líneas de saque). Con eso el programa sabe convertir píxeles en metros reales
   (eso es la *homografía*).
2. **Detección**: un modelo de visión (YOLOX, licencia Apache-2.0) encuentra a las personas
   y la bola en 10 fotogramas por segundo. Sin reconocimiento facial. Si la cámara se mueve
   o cambia de plano (repeticiones, primeros planos), el motor lo corrige o descarta esos
   fotogramas automáticamente.
3. **Seguimiento**: el punto de apoyo de cada jugador (los pies) se pasa a metros y se
   asigna a J1…J4 de forma estable. J1/J2 = campo cercano (izq./der.), J3/J4 = campo lejano.
4. **Métricas**: distancia, velocidad, tiempo en red/transición/fondo, sprints, pareja
   alineada/desalineada, mapa de calor, golpes estimados (experimental).
5. **Informe**: reglas deterministas proponen observaciones y ejercicios; el modelo de
   lenguaje los redacta. Solo recibe números y etiquetas J1…J4, nunca nombres ni imágenes.

## Usarlo con tus vídeos

Instalación (Python 3.11+):

```bash
pip install -e ".[dev]"
```

1) Calibrar (abre una ventana; clica cada punto que se pida o pulsa clic derecho si no se ve):

```bash
padel-engine calibrar mi_video.mp4 --salida mi_pista.json
```

Sin escritorio, exporta un fotograma con rejilla y escribe las coordenadas a mano
siguiendo `examples/calibracion_ejemplo.json`:

```bash
padel-engine calibrar mi_video.mp4 --salida mi_pista.json --solo-png
```

Si grabas siempre desde el mismo sitio de la misma pista, **reutiliza la calibración**.

2) Analizar (prueba primero con un trozo de 2 minutos):

```bash
padel-engine analizar mi_video.mp4 --calibracion mi_pista.json --salida resultados/prueba --desde 60 --hasta 180 --video-anotado
```

Opciones útiles: `--tipo-sesion entrenamiento`, `--jugadores 3`, `--nombres examples/nombres_ejemplo.json`,
`--sin-ia`, `--pesos yolox_s.onnx` (más rápido) o `--pesos yolox_l.onnx` (más preciso),
`--sin-estabilizar` (cámara totalmente fija), `--detector ultralytics` (solo para comparar, licencia AGPL).

Si el vídeo dura menos de 2 minutos de juego, el informe muestra las cifras pero no da
consejos: con tan poco tiempo no son fiables.

3) Regenerar solo el informe (sin GPU), p. ej. tras asignar nombres:

```bash
padel-engine informe resultados/prueba/analisis.json --nombres examples/nombres_ejemplo.json
```

## Tests

```bash
pytest
```

Usan un vídeo sintético con trayectorias conocidas: comprueban la calibración, que se
recuperan 4 jugadores con la etiqueta correcta, que la distancia recorrida coincide con
la real (±25 %) y que se detecta la pareja desalineada.

## Precisión esperada (sé realista)

| Métrica | Fiabilidad hoy | Comentario |
|---|---|---|
| Posición, zonas, mapa de calor | Buena | Depende sobre todo de la calibración y de que se vean los pies |
| Distancia y velocidad | Aceptable | ±10–20 %; los jugadores del fondo lejano tienen más error |
| Métricas de pareja | Buena | Solo necesitan posiciones |
| Cámara en mano / cambios de plano | Buena | Probado con una retransmisión grabada con el móvil |
| Identidad J1–J4 | Aceptable | Pueden intercambiarse si se cruzan pegados; en la web se corregirá a mano |
| Golpes (número, zona) | **Experimental** | La bola se detecta de forma intermitente |
| Tipo de golpe, errores no forzados | **No disponible** | Necesita un modelo propio entrenado con vídeos reales (ver `docs/HOJA_DE_RUTA.md`) |
