import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Início",
};

export default function HomePage() {
  return (
    <>
      <h1>Conta simulada, regras no código</h1>
      <p className="lead">
        Este painel ainda não opera. Ele mostra o livro de paper, a posição aberta, o último sinal e os
        limites de risco quando o Supabase estiver ligado. Até lá, as páginas ficam vazias de propósito.
      </p>
      <p className="banner">
        Fase atual: paper trading. Bybit para residente no Brasil é só spot desde 24/09/2026. O sinal sai de{" "}
        <code>trading-system/run_signal.py</code>. Um humano responde sim ou não. Ninguém envia ordem sozinho.
      </p>
      <div className="grid">
        <Link className="card" href="/ledger">
          <strong>Livro-razão</strong>
          <span>Trades simulados gravados em paper_trades.</span>
        </Link>
        <Link className="card" href="/posicao">
          <strong>Posição aberta</strong>
          <span>No máximo uma. Stop de 3×ATR.</span>
        </Link>
        <Link className="card" href="/sinal">
          <strong>Último sinal</strong>
          <span>SMA100 diária, janela 10:00–12:30 BRT.</span>
        </Link>
        <Link className="card" href="/risco">
          <strong>Limites</strong>
          <span>Kill switch em 90% do capital inicial. O Risco pode vetar.</span>
        </Link>
      </div>
      <h2>O que este repositório não faz</h2>
      <ul>
        <li>Não guarda chave de API, seed ou senha.</li>
        <li>Não promete retorno. O backtest de R$100 no BTC virou cerca de R$148 em 3 anos, com drawdown de −13,7% — e isso já passou.</li>
        <li>Não opera 15 minutos, reversão, ABCD, grade ou alavancagem. Essas famílias perderam para a taxa no teste próprio.</li>
      </ul>
    </>
  );
}
