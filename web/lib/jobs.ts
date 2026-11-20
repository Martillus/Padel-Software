// Trabajos de análisis — MODO LOCAL (en tu ordenador).
//
// Cada análisis vive en .data/jobs/<id>/ (vídeo, calibración, resultados) y el motor de
// Python se lanza como un proceso aparte. Sirve para probar todo el recorrido sin cuentas
// en la nube.
//
// En producción esto se sustituye por (ver docs/ARQUITECTURA.md):
//   vídeo -> Cloudflare R2 (subida directa con URL firmada)
//   trabajo -> tabla `jobs` en Supabase
//   motor -> worker con GPU en Modal que lee de la cola
// La interfaz de este módulo (createJob, getJob, saveVideo...) es la que habrá que mantener.

import { spawn } from "node:child_process";
import { createWriteStream } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { Readable, Transform } from "node:stream";
import { pipeline } from "node:stream/promises";
import type { ReadableStream as WebReadableStream } from "node:stream/web";

import { MAX_VIDEO_MB } from "./config";
import type { Analysis, AnalysisResponse, Calibration, JobPublic } from "./types";

interface Job extends JobPublic {
  calibration: Calibration;
  email?: string;
  videoExt: string;
}

const DATA_DIR = process.env.PADEL_DATA_DIR ?? path.join(process.cwd(), ".data");
const JOBS_DIR = path.join(DATA_DIR, "jobs");
const DEMO_DIR = path.join(process.cwd(), "data", "demo");
const ID_RE = /^[a-f0-9-]{36}$/;

export const DEMO_ID = "demo";

export function isValidId(id: string): boolean {
  return id === DEMO_ID || ID_RE.test(id);
}

const jobDir = (id: string) => path.join(JOBS_DIR, id);

async function writeJob(job: Job): Promise<void> {
  const file = path.join(jobDir(job.id), "job.json");
  const tmp = `${file}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(job, null, 2), "utf-8");
  await fs.rename(tmp, file);
}

async function readJob(id: string): Promise<Job | null> {
  try {
    return JSON.parse(await fs.readFile(path.join(jobDir(id), "job.json"), "utf-8")) as Job;
  } catch {
    return null;
  }
}

function toPublic(job: Job): JobPublic {
  const { calibration: _c, email: _e, videoExt: _v, ...pub } = job;
  return pub;
}

export async function createJob(input: {
  calibration: Calibration;
  durationS: number | null;
  sessionType: "partido" | "entrenamiento";
  players: number;
  email?: string;
  videoExt: string;
}): Promise<JobPublic> {
  const id = crypto.randomUUID();
  await fs.mkdir(jobDir(id), { recursive: true });
  const job: Job = { id, status: "esperando_video", createdAt: new Date().toISOString(), ...input };
  await fs.writeFile(path.join(jobDir(id), "calibracion.json"), JSON.stringify(input.calibration, null, 2), "utf-8");
  await writeJob(job);
  return toPublic(job);
}

/** Guarda el vídeo según llega (sin cargarlo entero en memoria) y lanza el análisis. */
export async function saveVideoAndStart(id: string, body: WebReadableStream<Uint8Array>): Promise<JobPublic> {
  const job = await readJob(id);
  if (!job) throw new Error("No existe ese análisis.");
  if (job.status !== "esperando_video") throw new Error("Este análisis ya tiene vídeo.");
  const videoPath = path.join(jobDir(id), `video${job.videoExt}`);
  let bytes = 0;
  const limit = MAX_VIDEO_MB * 1024 * 1024;
  const counter = new Transform({
    transform(chunk: Buffer, _enc, cb) {
      bytes += chunk.length;
      cb(bytes > limit ? new Error(`El vídeo supera ${MAX_VIDEO_MB} MB.`) : null, chunk);
    },
  });
  try {
    await pipeline(Readable.fromWeb(body), counter, createWriteStream(videoPath));
  } catch (err) {
    await fs.rm(videoPath, { force: true });
    throw err;
  }
  if (bytes === 0) throw new Error("El vídeo está vacío.");
  job.status = "en_cola";
  await writeJob(job);
  void runEngine(job, videoPath);
  return toPublic(job);
}

/** Lanza el motor (engine/). PADEL_ENGINE_CMD permite indicar la ruta del ejecutable. */
async function runEngine(job: Job, videoPath: string): Promise<void> {
  const dir = jobDir(job.id);
  const cmd = process.env.PADEL_ENGINE_CMD ?? "padel-engine";
  const args = [
    "analizar",
    videoPath,
    "--calibracion",
    path.join(dir, "calibracion.json"),
    "--salida",
    path.join(dir, "resultado"),
    "--tipo-sesion",
    job.sessionType,
    "--jugadores",
    String(job.players),
  ];
  job.status = "procesando";
  job.startedAt = new Date().toISOString();
  await writeJob(job);
  const log = await fs.open(path.join(dir, "motor.log"), "w");
  await new Promise<void>((resolve) => {
    let child;
    try {
      child = spawn(cmd, args, { cwd: dir, env: process.env, stdio: ["ignore", log.fd, log.fd] });
    } catch (err) {
      job.status = "error";
      job.error = `No se pudo arrancar el motor (${cmd}): ${(err as Error).message}`;
      return resolve();
    }
    child.on("error", (err) => {
      job.status = "error";
      job.error = `No se pudo arrancar el motor (${cmd}). ¿Está instalado y en el PATH? Detalle: ${err.message}`;
      resolve();
    });
    child.on("close", (code) => {
      if (job.status !== "error") {
        job.status = code === 0 ? "listo" : "error";
        if (code !== 0) job.error = "El análisis ha fallado. Revisa motor.log en la carpeta del análisis.";
      }
      resolve();
    });
  });
  await log.close();
  job.finishedAt = new Date().toISOString();
  await writeJob(job);
}

export async function getAnalysis(id: string): Promise<AnalysisResponse | null> {
  if (id === DEMO_ID) {
    const analysis = JSON.parse(await fs.readFile(path.join(DEMO_DIR, "analisis.json"), "utf-8")) as Analysis;
    const reportMd = await fs.readFile(path.join(DEMO_DIR, "informe.md"), "utf-8");
    return {
      job: {
        id: DEMO_ID,
        status: "listo",
        createdAt: "2026-11-15T18:00:00.000Z",
        durationS: analysis.video.duracion_s,
        sessionType: "partido",
        players: analysis.jugadores.length,
        demo: true,
      },
      analysis,
      reportMd,
    };
  }
  const job = await readJob(id);
  if (!job) return null;
  const res: AnalysisResponse = { job: toPublic(job) };
  if (job.status === "listo") {
    const out = path.join(jobDir(id), "resultado");
    try {
      res.analysis = JSON.parse(await fs.readFile(path.join(out, "analisis.json"), "utf-8")) as Analysis;
      res.reportMd = await fs.readFile(path.join(out, "informe.md"), "utf-8").catch(() => undefined);
    } catch {
      res.job = { ...res.job, status: "error", error: "Faltan los resultados del análisis." };
    }
  }
  return res;
}

/** Ruta de la foto de los jugadores (para "toca tu figura"). */
export async function getPhotoPath(id: string): Promise<string | null> {
  if (id === DEMO_ID) return null;
  const p = path.join(jobDir(id), "resultado", "foto_jugadores.jpg");
  try {
    await fs.access(p);
    return p;
  } catch {
    return null;
  }
}
