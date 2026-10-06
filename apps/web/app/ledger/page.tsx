import type { Metadata } from "next";
import { Suspense } from "react";
import { DeskTable } from "@/components/DeskTable";
import { readTable } from "@/lib/desk";

export const metadata: Metadata = { title: "Livro-razão" };

const columns = [
  { key: "id", label: "ID" },
  { key: "symbol", label: "Par" },
  { key: "status", label: "Estado" },
  { key: "entry_price", label: "Entrada" },
  { key: "exit_price", label: "Saída" },
  { key: "pnl_usdt", label: "PnL USDT" },
  { key: "r_multiple", label: "R" },
  { key: "exit_reason", label: "Motivo" },
];

async function LedgerBody() {
  const read = await readTable(
    "paper_trades",
    "select=id,symbol,status,entry_price,exit_price,pnl_usdt,r_multiple,exit_reason,opened_at&order=opened_at.desc&limit=50",
  );
  return (
    <DeskTable
      read={read}
      columns={columns}
      empty="Nenhum trade de paper no Supabase. O registrador local continua em trading-system/paper/, fora do git."
    />
  );
}

export default function LedgerPage() {
  return (
    <>
      <h1>Livro-razão</h1>
      <p>Histórico simulado. Números daqui não são ordem executada na corretora.</p>
      <Suspense fallback={<p className="note">Lendo o livro…</p>}>
        <LedgerBody />
      </Suspense>
    </>
  );
}
