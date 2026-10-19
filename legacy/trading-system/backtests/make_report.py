"""Gera results/RESULTADOS.md a partir dos CSV/JSON dos backtests."""
import json
import pandas as pd

r = pd.read_csv("results/metricas_todas.csv")
p = pd.read_csv("results/metricas_carteira.csv")
e = pd.read_csv("results/metricas_escolhida.csv")
w = pd.read_csv("results/walk_forward_sma.csv")
mc = json.load(open("results/monte_carlo_escolhida.json"))


def f(x, kind):
    if pd.isna(x):
        return "—"
    if kind == "pct":
        return f"{100 * x:+.1f}%".replace(".", ",")
    if kind == "pct0":
        return f"{100 * x:.0f}%"
    if kind == "R":
        return f"{x:+.2f}R".replace(".", ",")
    if kind == "num":
        return f"{x:.2f}".replace(".", ",")
    if kind == "int":
        return f"{int(x)}"
    if kind == "brl":
        return f"R$ {x:.0f}"
    return str(x)


def tabela(df, cols):
    head = "| " + " | ".join(c[1] for c in cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = ""
    for _, row in df.iterrows():
        body += "| " + " | ".join(f(row[c[0]], c[2]) if c[2] else str(row[c[0]]) for c in cols) + " |\n"
    return head + body


out = ["# Resultados dos backtests (gerado por make_report.py)\n",
       "Dados: Bybit spot, API v5 pública `/v5/market/kline` (15m: 06/10/2023–06/10/2026; 1h: 06/10/2021–06/10/2026, "
       "usado para aquecer indicadores). Avaliação: **06/10/2023 → 06/10/2026**. \"IS\" = 06/10/2023–05/04/2025, "
       "\"OOS\" = 06/04/2025–06/10/2026. Os parâmetros foram fixados **antes** de olhar os resultados (nenhum foi otimizado), então a "
       "2ª metade funciona como teste fora da amostra. Custos base: **0,10% de taxa + 0,05% de slippage por lado** (0,30% ida e volta); "
       "estresse: 0,10% + 0,15%. Posição = 100% do capital quando comprado (comparável ao buy-and-hold), salvo indicação. "
       "\"R$100 vira\" desconta ~0,44% de câmbio na entrada e na saída (BRL↔USDT) e ignora a variação do dólar.\n"]

cols = [("estrategia", "Estratégia", None), ("par", "Par", None), ("CAGR", "CAGR", "pct"), ("maxDD", "Máx. DD", "pct"),
        ("sharpe_diario", "Sharpe", "num"), ("n_trades", "Trades", "int"), ("acerto", "Acerto", "pct0"),
        ("media_trade", "Média/trade", "pct"), ("expect_R", "Expect. (R)", "R"), ("profit_factor", "PF", "num"),
        ("exposicao", "Tempo comprado", "pct0"), ("R$100_vira", "R$100 vira", "brl")]
b = r[(r.custos == "base") & (r.periodo == "TOTAL")]
out.append("## 1. Período total (3 anos), custos base\n")
out.append(tabela(b, cols))
out.append("\n## 2. Fora da amostra (2ª metade: 06/04/2025–06/10/2026), custos base\n")
o = r[(r.custos == "base") & (r.periodo == "OOS_2a_metade")]
out.append(tabela(o, [c for c in cols if c[0] not in ("R$100_vira",)]))
out.append("\n## 3. Sensibilidade a custos (CAGR do período total)\n")
pv = r[r.periodo == "TOTAL"].pivot_table(index=["estrategia", "par"], columns="custos", values="CAGR").reset_index()
out.append(tabela(pv, [("estrategia", "Estratégia", None), ("par", "Par", None), ("sem_custo", "Sem custo", "pct"),
                       ("base", "Base 0,15%/lado", "pct"), ("estresse", "Estresse 0,25%/lado", "pct")]))
out.append("\n## 4. Carteira 1/3 em cada par (BTC/ETH/SOL), custos base\n")
out.append(tabela(p, [("estrategia", "Estratégia", None), ("periodo", "Período", None), ("CAGR", "CAGR", "pct"),
                      ("maxDD", "Máx. DD", "pct"), ("sharpe_diario", "Sharpe", "num"), ("R$100_vira", "R$100 vira", "brl")]))
out.append("\n## 5. Estratégia escolhida (execução 10h BRT, stop 3×ATR na corretora, grade de 1h)\n")
out.append("`ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100` = o que uma conta de **R$100** faria de verdade: risco-alvo 1%, mas "
           "posição mínima de 6 USDT (mínimo da Bybit 5 USDT + folga) e teto de 3% de risco; o resto fica em USDT. "
           "`dias_bloqueados` = dias em que o sinal existia mas a regra de risco impediu a entrada (stop largo demais para o mínimo de ordem).\n")
e2 = e[e.custos == "base"].copy()
out.append(tabela(e2, [("estrategia", "Variante", None), ("par", "Par", None), ("periodo", "Período", None), ("CAGR", "CAGR", "pct"),
                       ("maxDD", "Máx. DD", "pct"), ("n_trades", "Trades", "int"), ("acerto", "Acerto", "pct0"),
                       ("expect_R", "Expect. (R)", "R"), ("R$100_vira", "R$100 vira", "brl"),
                       ("dias_sinal_bloqueado_por_risco_min_ordem", "Dias bloqueados", "int")]))
out.append("\n## 6. Walk-forward: escolher o N da SMA (20/50/100/150/200) a cada trimestre pelo Sharpe dos 12 meses anteriores\n")
out.append(tabela(w, [("par", "Par", None), ("metodo", "Método", None), ("periodo", "Período", None), ("CAGR", "CAGR", "pct"),
                      ("maxDD", "Máx. DD", "pct"), ("sharpe_diario", "Sharpe", "num"), ("N_escolhidos", "N escolhidos", None)]))
out.append("\n## 7. Monte Carlo (bootstrap de trades da estratégia escolhida; 20 mil caminhos; 1 posição por vez, ~7 trades/ano)\n")
out.append("Supõe trades independentes; ignora regimes. Serve para intuição de dispersão, não como previsão.\n\n```json\n"
           + json.dumps(mc, indent=1, ensure_ascii=False) + "\n```\n")
open("results/RESULTADOS.md", "w").write("\n".join(out))
print("ok")
