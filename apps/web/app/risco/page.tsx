import type { Metadata } from "next";
import { Suspense } from "react";
import { DeskTable } from "@/components/DeskTable";
import { readTable } from "@/lib/desk";
import { limits } from "@/lib/limits";

export const metadata: Metadata = { title: "Risco" };

async function KillSwitchBody() {
  const read = await readTable(
    "equity_snapshots",
    "select=ts,equity_usdt,equity_brl,kill_switch&order=ts.desc&limit=1",
  );
  return (
    <DeskTable
      read={read}
      columns={[
        { key: "ts", label: "Quando" },
        { key: "equity_usdt", label: "Patrimônio USDT" },
        { key: "equity_brl", label: "Patrimônio BRL" },
        { key: "kill_switch", label: "Kill switch" },
      ]}
      empty="Ainda não há snapshot de patrimônio. O gatilho continua valendo no código: 90% do capital inicial."
    />
  );
}

export default function RiskPage() {
  return (
    <>
      <h1>Limites de risco</h1>
      <p>
        Estas regras estão em <code>trading-system/config.py</code> e <code>risco.py</code>. Nenhum agente afrouxa
        um item. Se o Risco rejeita, a ideia morre.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Regra</th>
              <th scope="col">Valor</th>
              <th scope="col">Nota</th>
            </tr>
          </thead>
          <tbody>
            {limits.map((item) => (
              <tr key={item.regra}>
                <th scope="row">{item.regra}</th>
                <td>{item.valor}</td>
                <td>{item.detalhe}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2>Último snapshot</h2>
      <Suspense fallback={<p className="note">Lendo o patrimônio…</p>}>
        <KillSwitchBody />
      </Suspense>
      <p className="warn">Reativar o kill switch é só com o humano: <code>python3 run_signal.py --reset-kill-switch &quot;motivo&quot;</code></p>
    </>
  );
}
