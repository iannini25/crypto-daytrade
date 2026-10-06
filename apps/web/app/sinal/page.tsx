import type { Metadata } from "next";
import { Suspense } from "react";
import { DeskTable } from "@/components/DeskTable";
import { readTable } from "@/lib/desk";

export const metadata: Metadata = { title: "Sinal" };

const columns = [
  { key: "created_at", label: "Quando" },
  { key: "symbol", label: "Par" },
  { key: "side", label: "Lado" },
  { key: "regime_alta", label: "Regime de alta" },
  { key: "close_price", label: "Fechamento" },
  { key: "sma100", label: "SMA100" },
  { key: "atr14", label: "ATR14" },
  { key: "blocked", label: "Bloqueado" },
  { key: "block_reason", label: "Motivo" },
];

async function SignalBody() {
  const read = await readTable(
    "signals",
    "select=created_at,symbol,side,regime_alta,close_price,sma100,atr14,blocked,block_reason&order=created_at.desc&limit=8",
  );
  return (
    <DeskTable
      read={read}
      columns={columns}
      empty="Nenhum sinal gravado. Na maioria dos dias a resposta correta é SEM SINAL."
    />
  );
}

export default function SignalPage() {
  return (
    <>
      <h1>Último sinal</h1>
      <p>
        A regra congelada é o fechamento diário contra a SMA100, executada só entre 10:00 e 12:30 BRT. O agente
        não inventa outro gatilho.
      </p>
      <Suspense fallback={<p className="note">Lendo os sinais…</p>}>
        <SignalBody />
      </Suspense>
    </>
  );
}
