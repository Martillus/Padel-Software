// "Mis partidos": sin cuentas, guardamos en este dispositivo la lista de análisis.
// Puede fallar (modo privado, almacenamiento bloqueado): por eso todo va en try/catch.

export interface HistoryItem {
  id: string;
  createdAt: string;
  title: string;
}

const KEY = "padel:historial";

export function readHistory(): HistoryItem[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    const items = raw ? (JSON.parse(raw) as HistoryItem[]) : [];
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

export function addToHistory(item: HistoryItem): void {
  try {
    const items = readHistory().filter((i) => i.id !== item.id);
    window.localStorage.setItem(KEY, JSON.stringify([item, ...items].slice(0, 50)));
  } catch {
    /* sin almacenamiento: no pasa nada, el enlace sigue funcionando */
  }
}

export function removeFromHistory(id: string): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(readHistory().filter((i) => i.id !== id)));
  } catch {
    /* ignorar */
  }
}
