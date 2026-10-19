"""Estratégia escolhida (compartilhada entre backtest e protótipo de paper trading).

TENDÊNCIA DIÁRIA + STOP DE PROTEÇÃO (spot, long/flat):
- Regime: fechamento DIÁRIO (candle UTC, fecha às 21:00 BRT) acima da SMA(100) diária -> pode estar comprado.
- Entrada: na rotina da manhã (10:00-12:30 BRT) seguinte ao fechamento que confirmou o regime.
- Stop de proteção: entrada - 3 x ATR(14) diário (ordem de stop na corretora, vale 24h).
- Saída: fechamento diário abaixo da SMA(100) -> vende na rotina seguinte; ou stop atingido.
- Sem alvo fixo (seguidor de tendência vive dos poucos ganhos grandes); "alvo de referência" 3R só informativo.
Parâmetros fixados A PRIORI (SMA100 e 3xATR são valores redondos usuais), não otimizados.
"""
import numpy as np
import pandas as pd

SMA_N = 100
ATR_N = 14
ATR_MULT = 3.0
ALVO_REF_R = 3.0


def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def atr(df, n=ATR_N):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def indicadores_diarios(d):
    """d: OHLCV diário (candles FECHADOS), índice = abertura UTC. Acrescenta sma, atr, regime."""
    d = d.copy()
    d["sma"] = sma(d["close"], SMA_N)
    d["atr"] = atr(d, ATR_N)
    d["regime_alta"] = d["close"] > d["sma"]
    return d


def avaliar(d):
    """Lê o ÚLTIMO candle diário fechado e devolve o estado da estratégia."""
    d = indicadores_diarios(d)
    u = d.iloc[-1]
    return {
        "data_candle_utc": str(d.index[-1].date()),
        "fechamento": float(u["close"]),
        "sma": float(u["sma"]),
        "atr": float(u["atr"]),
        "regime_alta": bool(u["regime_alta"]),
        "dist_sma_pct": float(u["close"] / u["sma"] - 1),
        "stop_dist": float(ATR_MULT * u["atr"]),
    }
