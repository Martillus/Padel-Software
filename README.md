# Padel Software — análisis de vídeo de pádel con IA para entrenadores

SaaS para entrenadores y academias de pádel: suben un vídeo grabado con el móvil, la IA
lo analiza y genera un informe por alumno y su evolución en el tiempo.

> Estado: motor de análisis funcionando y **web del cliente** (subir vídeo, marcar la pista, ver el
> análisis y chatear con la IA) funcionando en modo local. Falta conectar pagos y la nube.

## Estructura del repositorio

```
.
├── web/                    # Web del cliente (Next.js): portada, subida, análisis y chat con Claude
├── engine/                 # Motor de análisis en Python (este es el corazón)
│   ├── padel_engine/       #   código: pista, detección, seguimiento, métricas, informe
│   ├── tests/              #   pruebas automáticas (vídeo sintético con verdad conocida)
│   └── examples/           #   calibración y nombres de ejemplo
├── docs/
│   ├── ARQUITECTURA.md     # visión técnica completa y fases
│   ├── DECISIONES.md       # decisiones técnicas, licencias y costes
│   ├── GRABACION.md        # guía para entrenadores: cómo grabar el vídeo
│   ├── LEGAL.md            # requisitos RGPD/menores (BORRADOR para el abogado)
│   └── HOJA_DE_RUTA.md     # siguientes pasos y precisión esperada
├── .env.example            # variables de entorno necesarias (sin valores)
└── (más adelante) worker/  supabase/   # nube: worker con GPU y base de datos
```

## Probar el motor en 2 minutos

```bash
cd engine
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

```bash
padel-engine sintetico --salida datos/sintetico
```

```bash
padel-engine analizar datos/sintetico/sintetico.mp4 --calibracion datos/sintetico/calibracion.json --detector replay --detecciones datos/sintetico/detecciones.json --salida resultados/sintetico --video-anotado
```

Con un vídeo real tuyo: ver [engine/README.md](engine/README.md).

## Probar la web

Ver [web/README.md](web/README.md). En resumen, con Node.js instalado:

```bash
cd web
npm install
npm run dev
```

Y abre http://localhost:3000.
