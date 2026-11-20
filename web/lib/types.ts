// Tipos del analisis.json que genera el motor (engine/, versión de esquema 0.1).

export type Zone = "red" | "transicion" | "fondo";

export interface Observation {
  tipo: "fortaleza" | "mejora" | "aviso";
  texto: string;
  ejercicio: string | null;
}

export interface PlayerStats {
  id: string;
  campo: "cerca" | "lejos";
  lado_habitual: "izquierda" | "derecha";
  tiempo_visible_s: number;
  tiempo_cortado_pct?: number;
  cobertura_pct: number;
  distancia_m: number;
  velocidad_media_en_movimiento_mps: number;
  velocidad_punta_mps: number;
  metros_por_minuto: number;
  zonas_pct: Record<Zone, number>;
  distancia_media_a_red_m: number;
  posicion_media: { x: number; y: number };
  sprints: { num: number; top: { inicio_s: number; fin_s: number; vel_max_mps: number }[] };
  golpes_estimados: { num: number; por_zona: Record<string, number>; fiabilidad: string };
  observaciones: Observation[];
  mapa_calor_celdas: number[][];
}

export interface PairStats {
  campo: "cerca" | "lejos";
  jugadores: [string, string];
  ambos_en_red_pct: number;
  ambos_en_fondo_pct: number;
  desalineados_pct: number;
  distancia_media_entre_ellos_m: number;
  observaciones: Observation[];
}

export interface PlayersPhoto {
  archivo: string;
  fotograma: number;
  ancho: number;
  alto: number;
  cajas: Record<string, [number, number, number, number]>;
}

export interface Analysis {
  version_esquema: string;
  video: { archivo: string; duracion_s: number; duracion_analizada_s: number };
  jugadores: PlayerStats[];
  parejas: PairStats[];
  limitaciones: string[];
  foto_jugadores?: PlayersPhoto | null;
  informe?: { archivo: string; generado_con_ia: boolean };
}

export type JobStatus = "esperando_video" | "en_cola" | "procesando" | "listo" | "error";

export interface JobPublic {
  id: string;
  status: JobStatus;
  createdAt: string;
  durationS: number | null;
  sessionType: "partido" | "entrenamiento";
  players: number;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  demo?: boolean;
}

export interface AnalysisResponse {
  job: JobPublic;
  analysis?: Analysis;
  reportMd?: string;
}

/** Calibración que envía la web al motor (mismo formato que engine/examples). */
export interface Calibration {
  frame_time_s: number;
  frame_size: [number, number];
  image_points: Record<string, [number, number]>;
}
