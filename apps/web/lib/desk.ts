import { connection } from "next/server";

export type Row = Record<string, unknown>;

export type DeskRead =
  | { configured: false }
  | { configured: true; rows: Row[]; error: string | null };

function origin(): URL | null {
  const raw = process.env.SUPABASE_URL?.trim().replace(/\/$/, "");
  const key = process.env.SUPABASE_ANON_KEY?.trim();
  if (!raw || !key) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:") return null;
    const host = url.hostname.toLowerCase();
    if (host === "localhost" || host.endsWith(".local") || host === "0.0.0.0") return null;
    return url;
  } catch {
    return null;
  }
}

/** Lê uma tabela via PostgREST. Sem chave, devolve configured: false. Não registra segredos. */
export async function readTable(table: string, query: string): Promise<DeskRead> {
  await connection();
  const url = origin();
  const key = process.env.SUPABASE_ANON_KEY?.trim();
  if (!url || !key) return { configured: false };
  if (!/^[a-z_]+$/.test(table)) return { configured: true, rows: [], error: "tabela_invalida" };

  let response: Response;
  try {
    response = await fetch(`${url.origin}/rest/v1/${table}?${query}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });
  } catch {
    return { configured: true, rows: [], error: "rede" };
  }

  if (!response.ok) {
    let code = `http_${response.status}`;
    try {
      const body = (await response.json()) as { code?: unknown };
      if (typeof body.code === "string") code = body.code;
    } catch {
      /* corpo vazio */
    }
    return { configured: true, rows: [], error: code };
  }

  const body: unknown = await response.json();
  if (!Array.isArray(body)) return { configured: true, rows: [], error: "resposta_inesperada" };
  return { configured: true, rows: body as Row[], error: null };
}

export function cell(row: Row, key: string): string {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString("pt-BR");
  if (typeof value === "boolean") return value ? "sim" : "não";
  return String(value);
}
