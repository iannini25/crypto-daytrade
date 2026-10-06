"""Backtests honestos de estratégias spot long/flat simples (poucos parâmetros, escolhidos A PRIORI
pela literatura/prática comum, NÃO otimizados nos dados). Dados: Bybit spot (API v5 pública).
Uso: python3 run_backtests.py   -> grava results/*.csv e results/RESULTADOS.md
"""
import json
import numpy as np
import pandas as pd
from lib import *

SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
FEE, SLIP = 0.001, 0.0005
COST = FEE + SLIP                 # 0,15% por lado (cenário base)
COST_STRESS = FEE + 0.0015        # 0,25% por lado (estresse)
START = pd.Timestamp("2023-10-06", tz="UTC")
SPLIT = pd.Timestamp("2025-04-06", tz="UTC")   # 18 meses "in-sample" / 18 meses "out-of-sample"
END = pd.Timestamp("2026-10-07", tz="UTC")
FX_COST = 0.0044   # ida OU volta BRL<->USDT: spread ~0,24% + taxa 0,20% (14-bybit.md §3/§5)
PERIODS = {"TOTAL": (START, END), "IS_1a_metade": (START, SPLIT), "OOS_2a_metade": (SPLIT, END)}
D1, H4 = pd.Timedelta(days=1), pd.Timedelta(hours=4)

rows, eqs = [], {}


def record(name, sym, eq, trades, expo, cost_label="base", extra=None):
    for p, (a, b) in PERIODS.items():
        m = metrics(eq, trades, a, b, exposure=expo)
        m.update({"estrategia": name, "par": sym, "periodo": p, "custos": cost_label})
        if extra:
            m.update(extra)
        if p == "TOTAL":
            m["R$100_vira"] = 100 * (1 - FX_COST) ** 2 * (1 + m["retorno_total"])
        rows.append(m)
    if cost_label == "base":
        eqs[(name, sym)] = eq


def pos_strategy(name, sym, h, pos, costs=(("base", COST), ("estresse", COST_STRESS), ("sem_custo", 0.0))):
    for lab, c in costs:
        res = run_position(h["close"], pos, c)
        tr = trades_from_position(res)
        record(name, sym, res["eq"], tr, res["pos"], lab)


def donchian_state(d4):
    hh = d4["high"].shift(1).rolling(20).max()
    ll = d4["low"].shift(1).rolling(10).min()
    volok = d4["volume"] > 1.5 * sma(d4["volume"], 20).shift(1)
    ent = (d4["close"] > hh) & volok
    ex = d4["close"] < ll
    st, out = 0, []
    for e, x in zip(ent.values, ex.values):
        if st == 0 and e:
            st = 1
        elif st == 1 and x:
            st = 0
        out.append(st)
    return pd.Series(out, index=d4.index, dtype=float)


for sym in SYMS:
    h = load(sym, "60m")
    h = h[h.index < END]
    d = resample(h, "1D"); d4 = resample(h, "4h")
    grid = h.index

    # Benchmark: comprar e segurar
    pos_strategy("BH_comprar_segurar", sym, h, pd.Series(np.where(grid >= START - H, 1.0, 0.0), index=grid))

    # D1: tendência diária — fechamento acima da SMA(N)
    for N in (50, 100, 200):
        sig = (d["close"] > sma(d["close"], N)).astype(float)
        for lab, delay in (("exec_21hBRT", pd.Timedelta(0)), ("exec_10hBRT", pd.Timedelta(hours=13))):
            if N != 100 and lab != "exec_21hBRT":
                continue
            pos = to_grid(sig, D1, grid, delay).where(grid >= START - H, 0)
            pos_strategy(f"D_SMA{N}_{lab}", sym, h, pos)

    # D2: momentum de série temporal (retorno de L dias > 0)
    for L in (14, 28, 56):
        sig = (d["close"].pct_change(L) > 0).astype(float)
        for lab, delay in (("exec_21hBRT", pd.Timedelta(0)), ("exec_10hBRT", pd.Timedelta(hours=13))):
            if L != 28 and lab != "exec_21hBRT":
                continue
            pos = to_grid(sig, D1, grid, delay).where(grid >= START - H, 0)
            pos_strategy(f"D_TSMOM{L}_{lab}", sym, h, pos)

    # D3: SMA100 + alvo de volatilidade 40% a.a. (peso em degraus de 25% p/ limitar giro)
    vol = d["close"].pct_change().rolling(30).std() * np.sqrt(365)
    w = (0.40 / vol).clip(0, 1)
    w = (np.floor(w * 4) / 4).where(d["close"] > sma(d["close"], 100), 0.0)
    pos = to_grid(w, D1, grid).where(grid >= START - H, 0)
    pos_strategy("D_SMA100_voltarget40", sym, h, pos)

    # H4a: rompimento Donchian 20 (4h) com filtro de volume 1,5x; saída na mínima de 10
    pos = to_grid(donchian_state(d4), H4, grid).where(grid >= START - H, 0)
    pos_strategy("H4_Donchian20_vol", sym, h, pos)

    # H4b: 4h acima da EMA50(4h) E diário acima da SMA100
    s4 = (d4["close"] > ema(d4["close"], 50)).astype(float)
    sd = (d["close"] > sma(d["close"], 100)).astype(float)
    pos = (to_grid(s4, H4, grid) * to_grid(sd, D1, grid)).where(grid >= START - H, 0)
    pos_strategy("H4_EMA50_filtroD_SMA100", sym, h, pos)

    # H1: reversão à média dentro de tendência (Bollinger 20,2 em 1h; 4h acima da EMA50)
    bb_mid = sma(h["close"], 20); bb_lo = bb_mid - 2 * h["close"].rolling(20).std()
    up4 = to_grid((d4["close"] > ema(d4["close"], 50)).astype(float), H4, grid).fillna(0) > 0
    ent = (h["close"] < bb_lo) & up4 & (grid >= START)
    for lab, fee, slip in (("base", FEE, SLIP), ("estresse", FEE, 0.0015), ("sem_custo", 0, 0)):
        tr, eq = run_events(h, ent, 2 * atr(h, 14), target_R=None, max_bars=48,
                            exit_sig=h["close"] > bb_mid, fee=fee, slip=slip)
        record("H1_reversao_BB_em_tendencia", sym, eq, tr, None, lab)

    # ---------- 15m: entradas na janela 10h-12h30 BRT com filtros de 1h e 4h ----------
    m = load(sym, "15m")
    m = m[m.index < END]
    g15 = m.index
    h1 = resample(m, "1h"); h4 = resample(m, "4h")
    f1 = to_grid((h1["close"] > ema(h1["close"], 50)).astype(float), H, g15).fillna(0) > 0
    f4 = to_grid((h4["close"] > ema(h4["close"], 50)).astype(float), H4, g15).fillna(0) > 0
    atr1h = to_grid(atr(h1, 14), H, g15)
    hhmm = g15.hour * 60 + g15.minute
    janela = (hhmm >= 13 * 60) & (hhmm <= 15 * 60 + 15)   # candles que FECHAM entre 13:15 e 15:30 UTC = 10:15-12:30 BRT
    base = f1 & f4 & janela & (g15 >= START)
    brk = (m["close"] > m["high"].shift(1).rolling(16).max()) & (m["volume"] > 1.5 * sma(m["volume"], 20).shift(1))
    e21 = ema(m["close"], 21)
    pb = (m["low"] <= e21) & (m["close"] > e21) & (m["close"] > m["open"])
    variants = {
        "M15_rompimento_stop1xATR1h_2R": (base & brk, atr1h, 2.0),
        "M15_rompimento_stop1.5xATR15m_2R": (base & brk, 1.5 * atr(m, 14), 2.0),
        "M15_pullbackEMA21_stop1xATR1h_2R": (base & pb, atr1h, 2.0),
    }
    for name, (ent, sdist, R) in variants.items():
        for lab, fee, slip in (("base", FEE, SLIP), ("estresse", FEE, 0.0015), ("sem_custo", 0, 0)):
            tr, eq = run_events(m, ent, sdist, target_R=R, max_bars=32, fee=fee, slip=slip, one_per_day=True)
            record(name, sym, eq, tr, None, lab)
            if lab == "base":
                tr.to_csv(f"results/trades_{name}_{sym}.csv", index=False)

res = pd.DataFrame(rows)
cols = ["estrategia", "par", "periodo", "custos", "CAGR", "retorno_total", "maxDD", "sharpe_diario", "n_trades",
        "acerto", "media_trade", "profit_factor", "expect_R", "exposicao", "R$100_vira"]
res = res[[c for c in cols if c in res.columns]]
res.to_csv("results/metricas_todas.csv", index=False)

# ---------- carteira 1/3 em cada par (sem rebalancear) ----------
port_rows = []
for name in sorted({k[0] for k in eqs}):
    if all((name, s) in eqs for s in SYMS):
        df = pd.concat([eqs[(name, s)] for s in SYMS], axis=1).dropna()
        for p, (a, b) in PERIODS.items():
            sl = df[(df.index >= a) & (df.index < b)]
            prev = df[df.index < a]
            basev = prev.iloc[-1] if len(prev) else sl.iloc[0]
            pe = (sl / basev).mean(axis=1)
            mm = metrics(pe, None, a, b)
            mm.update({"estrategia": name, "par": "CARTEIRA_1/3", "periodo": p, "custos": "base"})
            if p == "TOTAL":
                mm["R$100_vira"] = 100 * (1 - FX_COST) ** 2 * (1 + mm["retorno_total"])
            port_rows.append(mm)
port = pd.DataFrame(port_rows)
port.to_csv("results/metricas_carteira.csv", index=False)

# salva curvas diárias (base) para Monte Carlo
curves = pd.DataFrame({f"{k[0]}|{k[1]}": v.resample("1D").last() for k, v in eqs.items()})
curves.to_csv("results/curvas_diarias_base.csv")
print("ok", len(res), "linhas")
