"""Biblioteca de backtest (spot, long/flat, sem alavancagem) — dados públicos da Bybit.
Convenções:
- Índices em UTC = horário de ABERTURA do candle. BRT = UTC-3 (sem horário de verão).
- Sinal calculado no FECHAMENTO do candle; execução no candle seguinte (sem look-ahead).
- Custo por lado = taxa (0,10% spot VIP0) + slippage (padrão 0,05%).
"""
import os
import numpy as np
import pandas as pd

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
H = pd.Timedelta(hours=1)


def load(symbol, tf="60m"):
    df = pd.read_csv(os.path.join(DIR, f"{symbol}_{tf}.csv"))
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").astype(float).sort_index()
    df = df.iloc[:-1]  # último candle está incompleto
    return df


def resample(df, rule):
    o = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "turnover": "sum"})
    return o.dropna()


# ---------------- indicadores ----------------
def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def to_grid(sig, tf, grid_index, delay=pd.Timedelta(0)):
    """Leva um sinal (indexado pela abertura do candle de duração tf) para a grade base:
    o valor passa a valer no candle-base que abre em (abertura + tf + delay)."""
    s = pd.Series(sig.values, index=sig.index + tf + delay)
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(grid_index, method="ffill")


# ---------------- motor 1: posição alvo (0..1) na grade de 1h ----------------
def run_position(close, pos, cost_side):
    """close: série de fechamento da grade base; pos: posição alvo (0..1) válida em cada barra.
    Retorna DataFrame com retorno da barra, custo, equity (começa em 1)."""
    pos = pos.fillna(0).clip(0, 1)
    r = close.pct_change().fillna(0)
    turn = pos.diff().abs().fillna(pos.iloc[0])
    cost = turn * cost_side
    ret = pos * r - cost
    eq = (1 + ret).cumprod()
    return pd.DataFrame({"r": r, "pos": pos, "cost": cost, "ret": ret, "eq": eq})


def trades_from_position(res):
    """Segmentos contínuos com pos>0 = trades. Retorno do trade inclui custos de entrada e saída."""
    pos = res["pos"].values
    ret = res["ret"].values
    idx = res.index
    out = []
    i, n = 0, len(pos)
    while i < n:
        if pos[i] > 0:
            j = i
            g = 1.0 + ret[i]  # inclui custo de entrada (está na barra i)
            j = i + 1
            while j < n and pos[j] > 0:
                g *= 1 + ret[j]
                j += 1
            if j < n:  # barra de saída carrega o custo de saída
                g *= 1 + ret[j]
            out.append({"entry": idx[i], "exit": idx[j] if j < n else idx[-1], "ret": g - 1,
                        "bars": j - i, "open": j >= n})
            i = j
        else:
            i += 1
    return pd.DataFrame(out)


# ---------------- motor 2: eventos com stop/alvo (barra a barra) ----------------
def run_events(df, entry_sig, stop_dist, target_R=None, max_bars=None, exit_sig=None,
               fee=0.001, slip=0.0005, one_per_day=False):
    """df: OHLC da grade base. entry_sig: bool no FECHAMENTO da barra -> entra na abertura seguinte.
    stop_dist: distância do stop em preço (calculada no fechamento do sinal).
    Se stop e alvo caem na mesma barra, assume STOP primeiro (conservador).
    Gap abaixo do stop: executa na abertura (pior). Saída por exit_sig/tempo: fechamento da barra.
    Retorna (trades, equity mark-to-market com 100% do capital por trade)."""
    o, h, l, c = (df[k].values for k in ("open", "high", "low", "close"))
    es = entry_sig.reindex(df.index).fillna(False).values.astype(bool)
    sd = stop_dist.reindex(df.index).values
    xs = exit_sig.reindex(df.index).fillna(False).values.astype(bool) if exit_sig is not None else None
    days = df.index.floor("D")
    n = len(df)
    eq = np.ones(n)
    cash = 1.0
    in_pos = False
    trades = []
    last_day = None
    pending = False
    for i in range(n):
        if pending and not in_pos:
            pending = False
            entry = o[i] * (1 + slip)
            qty = cash * (1 - fee) / entry
            stop = entry - sd_sig
            tgt = entry + target_R * sd_sig if target_R else None
            ent_i, in_pos = i, True
            ent_cash = cash
        if in_pos:
            exit_px = None; why = None
            if l[i] <= stop:
                exit_px = min(o[i], stop) * (1 - slip); why = "stop"
            elif tgt is not None and h[i] >= tgt:
                exit_px = max(o[i], tgt); why = "alvo"  # alvo = ordem limite (sem slippage)
            elif xs is not None and xs[i]:
                exit_px = c[i] * (1 - slip); why = "saida_sinal"
            elif max_bars and i - ent_i + 1 >= max_bars:
                exit_px = c[i] * (1 - slip); why = "tempo"
            if exit_px is not None:
                cash = qty * exit_px * (1 - fee)
                R_unit = sd_sig
                trades.append({"entry": df.index[ent_i], "exit": df.index[i], "entry_px": entry,
                               "exit_px": exit_px, "stop_dist_pct": R_unit / entry, "why": why,
                               "ret": cash / ent_cash - 1,
                               "R_net": (cash / ent_cash - 1) * entry / R_unit,
                               "bars": i - ent_i + 1})
                in_pos = False
                eq[i] = cash
            else:
                eq[i] = qty * c[i] * (1 - fee)  # marcação a mercado já líquida da taxa de saída
        else:
            eq[i] = cash
        if not in_pos and not pending and es[i] and np.isfinite(sd[i]) and sd[i] > 0 and i + 1 < n:
            if one_per_day and last_day == days[i]:
                continue
            pending = True
            sd_sig = sd[i]
            last_day = days[i]
    return pd.DataFrame(trades), pd.Series(eq, index=df.index)


# ---------------- métricas ----------------
def metrics(eq, trades, start, end, bars_per_year=None, exposure=None):
    e = eq[(eq.index >= start) & (eq.index < end)]
    if len(e) < 2:
        return {}
    # base no valor imediatamente anterior ao início (se houver)
    prev = eq[eq.index < start]
    base = prev.iloc[-1] if len(prev) else e.iloc[0]
    e = e / base
    years = (e.index[-1] - e.index[0]).total_seconds() / (365.25 * 86400)
    cagr = e.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    dd = (e / e.cummax().clip(lower=1.0) - 1).min()
    d = e.resample("1D").last().pct_change().dropna()
    sharpe = d.mean() / d.std() * np.sqrt(365) if d.std() > 0 else np.nan
    m = {"retorno_total": e.iloc[-1] - 1, "CAGR": cagr, "maxDD": dd, "sharpe_diario": sharpe}
    if trades is not None and len(trades):
        t = trades[(trades["entry"] >= start) & (trades["entry"] < end)]
        m["n_trades"] = len(t)
        if len(t):
            m["acerto"] = (t["ret"] > 0).mean()
            m["media_trade"] = t["ret"].mean()
            gw = t.loc[t["ret"] > 0, "ret"].sum(); gl = -t.loc[t["ret"] <= 0, "ret"].sum()
            m["profit_factor"] = gw / gl if gl > 0 else np.inf
            if "R_net" in t:
                m["expect_R"] = t["R_net"].mean()
    else:
        m["n_trades"] = 0
    if exposure is not None:
        x = exposure[(exposure.index >= start) & (exposure.index < end)]
        m["exposicao"] = (x > 0).mean()
    return m
