# Decisiones técnicas, licencias y costes

Cada decisión indica si afecta a **💶 costes**, **⚖️ temas legales** o **📈 escalabilidad**.

## 1. Padex: lo usamos como referencia, no como dependencia ⚖️

Revisado (v0.1.0, repositorio `rondo-labs/Padex`):

- **Licencia GPL-3.0.** Usarlo solo en nuestros servidores no obliga a publicar código
  (la GPL se activa al *distribuir* software), pero si algún día entregamos software al
  cliente (app de escritorio, instalación en un club, SDK) estaríamos obligados a liberar
  el nuestro. Además depende de Ultralytics (AGPL, ver punto 2).
- **Pensado para vídeo de retransmisión**, no para móvil desde detrás de la pista.
- **Estado alfa** (versión 0.1.0, un único autor).
- Ideas útiles que sí tomamos *como concepto* (sin copiar código): calibración por
  puntos con nombre, TrackNet para la bola, clasificación de golpes por pose.

Decisión: motor propio, pequeño y bajo nuestro control. Revisaremos Padex de vez en
cuando para comparar resultados. ⚠️ No copiar fragmentos de su código en este repositorio.

## 2. Detector de personas: YOLO de Ultralytics para prototipar ⚖️💶

- Ultralytics es el más preciso y cómodo, pero su licencia es **AGPL-3.0**: en un SaaS la
  interpretación prudente es que obliga a ofrecer el código fuente del servicio a los
  usuarios, salvo que compres la **licencia Enterprise** de Ultralytics.
- Para el piloto gratuito es asumible. **Antes de cobrar** hay que elegir:
  1. Comprar la licencia de Ultralytics (pide presupuesto), o
  2. Cambiar a un detector con licencia permisiva (Apache/BSD): `torchvision` ya está
     implementado (BSD), u otros como RT-DETR/RF-DETR (Apache-2.0) entrenados por nosotros.
- El código está preparado: el detector se cambia con `--detector`, sin tocar lo demás.
- 👉 Punto para el abogado: confirmar la interpretación de la AGPL en nuestro caso.

## 3. Analizar 10 fotogramas por segundo 💶📈

Los móviles graban a 30–60 fps. Para posiciones y recorridos bastan 10 fps: **coste de
GPU 3–6 veces menor**. La bola necesitará más fps (o un modelo específico) en el futuro.

## 4. Calibración manual asistida en vez de automática 📈

Detectar las líneas automáticamente falla a menudo con cristales, reflejos, sombras y
redes. Marcar 4–6 puntos lleva ~15 s, es fiable y se reutiliza si el móvil se coloca en
el mismo sitio. La detección automática queda como mejora futura (sugerir los puntos y que
el entrenador solo confirme).

## 5. Sin reconocimiento facial: identidad por posición + asignación manual ⚖️

El motor etiqueta J1–J4 por campo y lado. El entrenador asigna cada etiqueta a un alumno
en la web. No se procesan rasgos faciales ni biométricos (el reconocimiento facial sería
un dato biométrico de categoría especial, art. 9 RGPD, con menores: descartado).

## 6. Informe: reglas + modelo de lenguaje ⚖️💶

- Reglas deterministas deciden *qué* decir (observaciones y ejercicios, explicables).
- El modelo de lenguaje decide *cómo* decirlo (redacción clara, tono positivo).
- Al modelo solo se envían números y etiquetas J1–J4. Nombres, edades y vídeo, nunca.
- Si no hay clave o falla, se genera un informe de plantilla: el servicio no se cae.
- Modelo por defecto: `claude-opus-5-5` con esfuerzo `medium`. Se cambia con
  `PADEL_LLM_MODEL` (p. ej. `claude-haiku-5-5`, unas 40 veces más barato) si en el piloto
  vemos que la calidad es suficiente.
- 👉 Punto para el abogado: Anthropic actúa como subencargado; revisar su DPA, la
  ubicación del procesamiento y la política de retención de datos de la API.

## 7. Costes estimados por vídeo 💶

Estimaciones a validar con vídeos reales (el motor guarda `tiempos.segundos_computo_por_minuto_video`
en cada análisis precisamente para medirlo):

| Concepto | Supuesto | Coste aprox. por vídeo de 60 min |
|---|---|---|
| GPU (Modal, GPU tipo L4/T4) | 36.000 fotogramas a 10 fps, ~6–12 min de GPU | 0,08–0,20 € |
| Informe (Claude Opus 5.5) | ~5.000 tokens entrada, ~3.000 salida | ~0,07 € |
| Informe (Claude Haiku 5.5) | igual | < 0,01 € |
| Almacenamiento R2 | vídeo 1080p de 1 h ≈ 3–6 GB; ~0,014 €/GB·mes | 0,04–0,08 €/mes **mientras se guarde** |
| **Total** | | **~0,15–0,35 €** + almacenamiento |

Conclusiones:
- Entra en el objetivo de 0,10–0,50 €/vídeo.
- **El almacenamiento es el coste que crece sin que se note**: borrar el vídeo original
  a los X días (configurable) y guardar solo resultados es bueno para costes *y* para el RGPD.
- Los precios de proveedores cambian: verifícalos al crear las cuentas.

## 8. Escalabilidad 📈

- El worker es sin estado: Modal arranca tantas GPUs como trabajos haya en cola.
- Un vídeo de 1 h tarda ~10 min en procesarse en GPU; el entrenador recibe aviso al terminar.
- Para vídeos largos se puede trocear en fragmentos y procesarlos en paralelo (mejora futura).
