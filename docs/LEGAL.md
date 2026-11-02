# Requisitos legales y de privacidad — BORRADOR

> ⚠️ **Este documento no es asesoramiento legal.** Es un borrador técnico para preparar la
> reunión con el abogado. Los puntos marcados con **[REVISIÓN ABOGADO]** requieren su
> validación antes del lanzamiento.

## 1. Roles

- **Responsable del tratamiento**: el entrenador, club o academia (decide grabar y para qué).
- **Encargado del tratamiento**: nosotros (tratamos los vídeos por cuenta del entrenador).
- **Subencargados**: Supabase (BD y autenticación), Cloudflare (R2), Modal (GPU),
  Anthropic (redacción del informe, solo métricas), Vercel (web), Stripe (pagos — en este
  caso Stripe es responsable independiente de los datos de pago).
- **[REVISIÓN ABOGADO]** Contrato de encargo (art. 28 RGPD) que el entrenador acepta al
  registrarse, con anexo de subencargados y de medidas de seguridad.
- **[REVISIÓN ABOGADO]** Comprobar DPAs, ubicación de datos y transferencias
  internacionales (cláusulas contractuales tipo / Marco de Privacidad de Datos UE-EE. UU.)
  de cada subencargado, en especial Modal, Anthropic y Vercel.

## 2. Menores e imagen

- LOPDGDD art. 7: menores de 14 años → consentimiento de padres o tutores.
- LO 1/1982: derecho a la propia imagen; el consentimiento de menores lo prestan sus
  representantes (o ellos mismos si tienen madurez suficiente) y se puede revocar.
- Implementación prevista:
  - Casilla obligatoria antes de cada subida: "Confirmo que dispongo del consentimiento
    de los jugadores que aparecen o, si son menores de 14 años, de sus padres o tutores".
    Se guarda fecha, usuario, versión del texto e IP (`consent_records`).
  - Campo "menor de edad" por alumno; si lo es, los enlaces compartidos caducan antes
    y el informe usa un tono adaptado.
  - **[REVISIÓN ABOGADO]** Plantilla de consentimiento para padres que ofreceremos a los
    entrenadores (descargable).
  - **[REVISIÓN ABOGADO]** ¿Qué pasa con terceros que aparecen en el vídeo (público,
    pistas vecinas)? Recomendación técnica: encuadre limitado a la pista y posibilidad
    futura de difuminar zonas fuera de la pista.

## 3. Medidas técnicas (privacidad desde el diseño)

| Requisito | Cómo se cumple |
|---|---|
| Sin reconocimiento facial | El motor solo detecta "persona" y "bola"; identidad por posición + asignación manual |
| Datos en la UE | Supabase (Frankfurt), R2 con jurisdicción UE, Modal en región UE **[verificar disponibilidad]** |
| Cifrado | En tránsito (TLS) y en reposo (R2 y Postgres cifran por defecto) |
| Vídeos privados | Bucket privado; acceso solo con URLs firmadas de corta duración |
| Aislamiento entre clientes | Row Level Security en Supabase por organización |
| Borrado automático | `delete_after` por vídeo (por defecto, p. ej., 30 días, configurable); los resultados se conservan hasta que el entrenador los borre |
| Minimización hacia la IA | Al modelo de lenguaje solo van métricas y etiquetas J1–J4 (ya implementado en `engine/padel_engine/report.py`) |
| No entrenar modelos sin permiso | Por defecto **ningún** vídeo se usa para entrenar. Opción explícita, separada y revocable por el responsable (y con consentimiento de los afectados). **[REVISIÓN ABOGADO]** base jurídica y texto |
| Enlaces compartidos | Token aleatorio largo, caducidad, revocables, sin indexar (`noindex`) |
| Derechos ARSOPL | Exportar y borrar todos los datos de un alumno desde la web |
| Registro de actividades | Mantener el registro del art. 30 como encargado |

## 4. Ley europea de IA (Reglamento (UE) 2024/1689)

- Uso previsto: análisis deportivo para entrenadores → **no es de alto riesgo**
  (no es biometría, ni educación reglada con evaluación decisoria, ni empleo).
  **[REVISIÓN ABOGADO]** confirmar, sobre todo si se usa en escuelas o federaciones.
- Transparencia: cada informe indica que se ha generado con IA y que las cifras son
  estimaciones a revisar por el entrenador (ya implementado en el informe).
- No usar el sistema para inferir emociones ni para categorización biométrica (prohibido
  o de alto riesgo según el caso).

## 5. Documentos a preparar para el lanzamiento

1. Política de privacidad (web) **[REVISIÓN ABOGADO]**
2. Términos y condiciones del servicio **[REVISIÓN ABOGADO]**
3. Contrato de encargo del tratamiento + anexo de subencargados **[REVISIÓN ABOGADO]**
4. Plantilla de consentimiento para padres/tutores **[REVISIÓN ABOGADO]**
5. Política de cookies (si se usan cookies no técnicas)
6. Evaluación de impacto (EIPD): **[REVISIÓN ABOGADO]** probablemente recomendable por
   tratar imágenes de menores a cierta escala, aunque no sea obligatoria.
7. Aviso de transparencia sobre el uso de IA.
