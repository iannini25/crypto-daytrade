"""Backtest detalhado da estratégia escolhida (estrategia.py) executada às 10h BRT (13:00 UTC),
com stop de proteção intradiário (grade de 1h), dimensionamento por risco para conta de R$100,
mínimo de ordem da Bybit (5 USDT), walk-forward do parâmetro N e Monte Carlo.
Uso: python3 run_escolhida.py
"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import estrategia as E
from lib import load, resample, to_grid, run_position, metrics, sma as lsma

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
FEE, SLIP = 0.001, 0.0005
START = pd.Timestamp("2023-10-06", tz="UTC"); SPLIT = pd.Timestamp("2025-04-06", tz="UTC")
END = pd.Timestamp("2026-10-07", tz="UTC")
USDTBRL = 5.0483          # 14-bybit.md (06/10/2026 ~00:42 BRT); usado só para converter R$100 -> USDT
FX_COST = 0.0044
MIN_ORDER = 5.0           # minOrderAmt spot BTC/ETH/SOL (API instruments-info, 06/10/2026)
MIN_BUFFER = 1.2          # posição mínima 6 USDT para ainda conseguir vender após cair até o stop
EXEC_HOUR = 13            # 13:00 UTC = 10:00 BRT
out = {}


def simulate(h, d, atr_mult=E.ATR_MULT, use_stop=True, sizing="all_in", risk=0.02, risk_max=0.03,
             capital=100 / USDTBRL * (1 - FX_COST), sma_n=E.SMA_N, fee=FEE, slip=SLIP):
    """Simulação barra a barra (1h). Decisões só às 13:00 UTC com base no último diário fechado.
    sizing: 'all_in' (100% do saldo) ou 'risco' (risk do capital até o stop; respeita mínimo de ordem)."""
    dd = d.copy()
    dd["sma"] = lsma(dd["close"], sma_n); dd["atr"] = E.atr(dd)
    dd["reg"] = dd["close"] > dd["sma"]
    # valor do último diário FECHADO disponível em cada hora
    reg = to_grid(dd["reg"].astype(float), pd.Timedelta(days=1), h.index).fillna(0).values > 0
    atr_g = to_grid(dd["atr"], pd.Timedelta(days=1), h.index).values
    o, hi, lo, c = (h[k].values for k in ("open", "high", "low", "close"))
    hours = h.index.hour
    cash, qty, stop, entry, R_unit = capital, 0.0, 0.0, 0.0, 0.0
    eq = np.empty(len(h)); trades = []; skipped = 0
    for i in range(len(h)):
        t = h.index[i]
        if qty > 0 and use_stop and lo[i] <= stop:          # stop na corretora (24h)
            px = min(o[i], stop) * (1 - slip)
            cash += qty * px * (1 - fee)
            trades.append(dict(entry=ent_t, exit=t, why="stop", ret=(cash - ent_cash) / ent_cap,
                               pnl=cash - ent_cash, R_net=(cash - ent_cash) / (qty_e * R_unit), pos_frac=pos_frac))
            qty = 0.0
        if hours[i] == EXEC_HOUR and t >= START:           # rotina das 10h BRT, executa na abertura desta barra
            if qty > 0 and not reg[i]:
                px = o[i] * (1 - slip); cash += qty * px * (1 - fee)
                trades.append(dict(entry=ent_t, exit=t, why="regime", ret=(cash - ent_cash) / ent_cap,
                                   pnl=cash - ent_cash, R_net=(cash - ent_cash) / (qty_e * R_unit), pos_frac=pos_frac))
                qty = 0.0
            elif qty == 0 and reg[i] and np.isfinite(atr_g[i]):
                px = o[i] * (1 + slip)
                sd = atr_mult * atr_g[i]
                if sizing == "all_in":
                    notional = cash
                else:
                    notional = min(cash, cash * risk / (sd / px + 2 * (fee + slip)))
                    if notional < MIN_ORDER * MIN_BUFFER:
                        notional = MIN_ORDER * MIN_BUFFER
                        if notional * (sd / px + 2 * (fee + slip)) > risk_max * cash or notional > cash:
                            notional = 0; skipped += 1
                if notional > 0:
                    ent_cash, ent_cap, ent_t = cash, cash, t
                    qty = notional * (1 - fee) / px; qty_e = qty
                    cash -= notional
                    entry, R_unit, stop = px, sd, px - sd
                    pos_frac = notional / ent_cap
        eq[i] = cash + qty * c[i] * (1 - fee)
    if qty > 0:
        trades.append(dict(entry=ent_t, exit=h.index[-1], why="aberto", ret=(eq[-1] - ent_cash) / ent_cap,
                           pnl=eq[-1] - ent_cash, R_net=(eq[-1] - ent_cash) / (qty_e * R_unit), pos_frac=pos_frac))
    return pd.Series(eq, index=h.index) / capital, pd.DataFrame(trades), skipped


rows = []; all_trades = []
data = {}
for s in SYMS:
    h = load(s, "60m"); h = h[h.index < END]; d = resample(h, "1D")
    data[s] = (h, d)
    variants = {
        "ESCOLHIDA_SMA100_stop3ATR_allin": dict(),
        "var_stop2ATR_allin": dict(atr_mult=2.0),
        "var_sem_stop_allin": dict(use_stop=False),
        "ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100": dict(sizing="risco", risk=0.01),
    }
    for name, kw in variants.items():
        for lab, fee, slip in (("base", FEE, SLIP), ("estresse", FEE, 0.0015)):
            eq, tr, sk = simulate(h, d, fee=fee, slip=slip, **kw)
            for p, (a, b) in {"TOTAL": (START, END), "IS_1a_metade": (START, SPLIT), "OOS_2a_metade": (SPLIT, END)}.items():
                m = metrics(eq, tr, a, b)
                m.update(estrategia=name, par=s, periodo=p, custos=lab)
                if p == "TOTAL":
                    m["R$100_vira"] = 100 * (1 - FX_COST) * eq[eq.index < END].iloc[-1] * (1 - FX_COST)
                    m["dias_sinal_bloqueado_por_risco_min_ordem"] = sk
                    if len(tr):
                        m["pos_media_%cap"] = tr["pos_frac"].mean()
                        m["ganho_medio_R"] = tr.loc[tr.R_net > 0, "R_net"].mean()
                        m["perda_media_R"] = tr.loc[tr.R_net <= 0, "R_net"].mean()
                rows.append(m)
            if lab == "base" and name.startswith("ESCOLHIDA_SMA100"):
                tr["par"] = s; all_trades.append(tr)
                tr.to_csv(f"results/trades_ESCOLHIDA_{s}.csv", index=False)
                eq.resample("1D").last().to_csv(f"results/curva_ESCOLHIDA_{s}.csv")

res = pd.DataFrame(rows)
res.to_csv("results/metricas_escolhida.csv", index=False)

# ---------------- walk-forward do N da SMA (seleção trimestral por Sharpe dos 365 d anteriores) -------------
wf_rows = []
NS = [20, 50, 100, 150, 200]
for s in SYMS:
    h, d = data[s]
    eqN = {}
    for N in NS:
        sig = (d["close"] > lsma(d["close"], N)).astype(float)
        pos = to_grid(sig, pd.Timedelta(days=1), h.index, pd.Timedelta(hours=13)).fillna(0)
        eqN[N] = run_position(h["close"], pos, FEE + SLIP)["ret"]
    R = pd.DataFrame(eqN)
    dates = pd.date_range(START, END, freq="91D", tz="UTC")
    wf = pd.Series(0.0, index=R.index); chosen = []
    for a, b in zip(dates[:-1], list(dates[1:-1]) + [END]):
        tr = R[(R.index >= a - pd.Timedelta(days=365)) & (R.index < a)]
        dly = (1 + tr).resample("1D").prod() - 1
        best = (dly.mean() / dly.std()).idxmax()
        chosen.append(int(best))
        mask = (R.index >= a) & (R.index < b)
        wf[mask] = R.loc[mask, best]
    # nota: troca de N pode gerar um trade extra na virada do trimestre (custo ignorado: pequeno)
    eqwf = (1 + wf[wf.index >= START]).cumprod()
    eq100 = (1 + R.loc[R.index >= START, 100]).cumprod()
    for lab, e in (("walk_forward_N", eqwf), ("fixo_N100", eq100)):
        for p, (a, b) in {"TOTAL": (START, END), "OOS_2a_metade": (SPLIT, END)}.items():
            m = metrics(e, None, a, b); m.update(par=s, metodo=lab, periodo=p)
            if lab == "walk_forward_N": m["N_escolhidos"] = str(chosen)
            wf_rows.append(m)
pd.DataFrame(wf_rows).to_csv("results/walk_forward_sma.csv", index=False)

# ---------------- Monte Carlo (bootstrap de trades, 1 posição por vez) ----------------
# Supõe trades independentes (i.i.d.) — ignora regimes/sequências; é só para intuição de dispersão.
T = pd.concat(all_trades)
T = T[T.why != "aberto"]
rng = np.random.default_rng(42)
mc = {}
pools = {"pool_BTC": T[T.par == "BTCUSDT"]["R_net"].values, "pool_3pares": T["R_net"].values}
tpy = (T.par == "BTCUSDT").sum() / 3.0   # ~7 trades/ano com 1 posição (BTC)
for pool_name, Rs in pools.items():
    for label, risk_frac, years in (("risco_2.7pct_1ano", 0.027, 1), ("risco_2.7pct_3anos", 0.027, 3),
                                    ("risco_9pct_(~all-in_stop3ATR)_3anos", 0.09, 3)):
        n_tr = int(round(tpy * years))
        finals, mdds, hit500, hit90 = [], [], 0, 0
        for _ in range(20000):
            eqv = 100.0; peak = 100.0; mdd = 0; h5 = h9 = False
            for r in rng.choice(Rs, n_tr, replace=True):
                eqv *= 1 + r * risk_frac
                peak = max(peak, eqv); mdd = min(mdd, eqv / peak - 1)
                h5 |= eqv >= 500; h9 |= eqv <= 90
            finals.append(eqv); mdds.append(mdd); hit500 += h5; hit90 += h9
        f = np.array(finals)
        mc[f"{pool_name}|{label}"] = {"n_trades_simulados": n_tr, "mediana_final_R$": round(float(np.median(f)), 2),
                     "p5_final_R$": round(float(np.percentile(f, 5)), 2), "p95_final_R$": round(float(np.percentile(f, 95)), 2),
                     "prob_terminar_abaixo_R$100": round(float((f < 100).mean()), 3),
                     "prob_tocar_R$90_(kill_switch)": round(hit90 / 20000, 3),
                     "prob_chegar_R$500": round(hit500 / 20000, 3),
                     "maxDD_mediano": round(float(np.median(mdds)), 3), "maxDD_p5_pior": round(float(np.percentile(mdds, 5)), 3)}
    mc[f"{pool_name}|_amostra"] = {"n_trades_reais": int(len(Rs)), "acerto": round(float((Rs > 0).mean()), 3),
                      "expect_R": round(float(Rs.mean()), 3), "mediana_R": round(float(np.median(Rs)), 3),
                      "maior_ganho_R": round(float(Rs.max()), 2), "pior_R": round(float(Rs.min()), 2),
                      "expect_R_sem_maior_trade": round(float(np.sort(Rs)[:-1].mean()), 3)}
mc["_trades_por_ano_1_posicao"] = round(tpy, 1)
json.dump(mc, open("results/monte_carlo_escolhida.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps(mc, indent=1, ensure_ascii=False))
