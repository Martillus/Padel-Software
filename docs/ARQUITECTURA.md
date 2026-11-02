# Arquitectura

## Visión general

```
 Entrenador (navegador / móvil)
        │  1. sube el vídeo directamente a R2 (URL firmada, no pasa por nuestro servidor)
        ▼
 ┌──────────────┐   2. crea "trabajo"   ┌──────────────────────┐
 │  Web Next.js │ ────────────────────▶ │ Supabase (Postgres,  │
 │  (Vercel UE) │ ◀──── estado/informe ─│ Auth, Storage meta)  │
 └──────────────┘                       └──────────┬───────────┘
        ▲                                          │ 3. cola de trabajos
        │ 6. aviso (email / notificación)          ▼
        │                               ┌──────────────────────┐
        └────────────────────────────── │ Worker GPU (Modal)   │
                                        │  = padel_engine      │ 4. lee vídeo de R2, analiza
                                        │                      │ 5. guarda JSON/PNG en R2 + BD
                                        └──────────┬───────────┘
                                                   │ solo métricas, sin nombres
                                                   ▼
                                           API de Claude (informe)
```

## Componentes

| Pieza | Tecnología | Por qué |
|---|---|---|
| Web | Next.js (TypeScript) | Estándar, rápido de desarrollar, buen soporte para SSR y subidas |
| Usuarios y BD | Supabase en región UE (Frankfurt) | Auth + Postgres + Row Level Security: cada entrenador solo ve sus datos |
| Vídeos | Cloudflare R2 con **jurisdicción UE** | Sin coste de descarga (egress), compatible con S3, datos en la UE |
| Cola | Tabla `jobs` en Postgres (al principio) | Cero piezas extra; migrar a una cola dedicada solo si hace falta |
| Análisis | `engine/` en Python sobre Modal (GPU por uso) | Pagas solo los segundos de GPU; arranque en frío ~10–30 s, aceptable para un proceso asíncrono |
| Informes | API de Claude | Calidad de redacción en español; solo recibe métricas |
| Pagos | Stripe Billing (fase 3) | Suscripciones, límites por plan, facturas con IVA |

## El motor (fase 1) por dentro

```
engine/padel_engine/
├── court.py            Geometría de la pista (10×20 m), homografía píxel→metros, zonas
├── calibration.py      Guardar/cargar calibración, herramienta de marcado, imagen de control
├── detection.py        Detectores intercambiables: ultralytics | torchvision | replay
├── tracking.py         Seguimiento J1..JN en metros (algoritmo húngaro + re-enganche)
├── ball.py             Bola y golpes candidatos (EXPERIMENTAL)
├── stats.py            Métricas por jugador y por pareja, mapa de calor
├── recommendations.py  Reglas → observaciones y ejercicios (explicables)
├── report.py           Informe con IA (o plantilla) y sustitución local de nombres
├── heatmap.py          PNGs de mapas de calor y recorridos
├── pipeline.py         Orquesta todo y escribe los resultados
├── synthetic.py        Vídeo sintético con verdad conocida (tests)
└── cli.py              Comando `padel-engine`
```

Principio de diseño: **cada etapa guarda su salida** (detecciones → trayectorias →
métricas → informe). Así se puede mejorar una etapa (p. ej. las reglas o el informe) y
recalcular los vídeos antiguos sin volver a pagar GPU.

El `analisis.json` lleva `version_esquema` para que la web sepa leer versiones antiguas.

## Modelo de datos previsto (fase 2, orientativo)

- `organizations` (academia/club) → `coaches` (entrenadores, usuarios de Supabase Auth)
- `students` (alumnos: alias, año de nacimiento opcional, `is_minor`, estado de consentimiento)
- `groups` y `group_members`
- `videos` (ruta en R2, fecha, pista, calibración usada, `delete_after`)
- `jobs` (estado: pendiente / procesando / terminado / error, coste estimado)
- `analyses` (JSON del motor, versión de esquema)
- `player_assignments` (J1 → alumno; lo hace el entrenador en la web)
- `student_metrics` (una fila por alumno y sesión → gráficas de evolución)
- `share_links` (token aleatorio, caducidad, revocable)
- `consent_records` (confirmación del entrenador, fecha, versión del texto)
- `audit_log`

## Fases

1. **Motor** (ahora): CLI local, vídeo → JSON + informe. ✔ primera versión
2. **Web mínima** (piloto gratuito 3–5 entrenadores): registro, alumnos, subida a R2,
   calibración en el navegador (arrastrar 4–6 marcadores), worker en Modal, informe,
   asignar J1–J4 a alumnos, enlace privado.
3. **Suscripciones**: Stripe, límites por plan, evolución histórica por alumno.
4. **Lanzamiento**: landing, textos legales revisados, DPA, primeros clientes de pago.
