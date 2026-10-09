import type { Metadata } from "next";
import { Suspense } from "react";
import { DeskTable } from "@/components/DeskTable";
import { readTable } from "@/lib/desk";

export const metadata: Metadata = { title: "Posição" };

const columns = [
  { key: "id", label: "ID" },
  { key: "symbol", label: "Par" },
  { key: "qty", label: "Qtd" },
  { key: "entry_price", label: "Entrada" },
  { key: "stop_price", label: "Stop" },
  { key: "notional_usdt", label: "Nocional USDT" },
  { key: "opened_at", label: "Aberta em" },
];

async function PositionBody() {
  const read = await readTable(
    "paper_trades",
    "select=id,symbol,qty,entry_price,stop_price,notional_usdt,opened_at&status=eq.open&order=opened_at.desc&limit=5",
  );
  return (
    <DeskTable
      read={read}
      columns={columns}
      empty="Nenhuma posição aberta no Supabase. O teto da mesa é uma posição por vez."
    />
  );
}

export default function PositionPage() {
  return (
    <>
      <h1>Posição aberta</h1>
      <p>Spot long. O stop é a entrada menos 3×ATR14 do diário. Sem alvo fixo: a saída de regime espera o fechamento abaixo da SMA100.</p>
      <Suspense fallback={<p className="note">Lendo a posição…</p>}>
        <PositionBody />
      </Suspense>
    </>
  );
}
