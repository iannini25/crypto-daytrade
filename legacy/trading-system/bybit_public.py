"""Cliente mínimo da API PÚBLICA v5 da Bybit (sem chave). Endpoints usados:
GET /v5/market/kline, /v5/market/tickers, /v5/market/instruments-info (category=spot).
Limite documentado: 600 requisições / 5 s por IP — usamos poucas por ciclo.
"""
import json, time, urllib.request, urllib.parse
import pandas as pd

BASE = "https://api.bybit.com"


class ErroAPI(Exception):
    pass


def _get(path, params, tentativas=3):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    ult = None
    for t in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-trading-bernardo"})
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.load(r)
            if d.get("retCode") == 0:
                return d["result"]
            ult = f"retCode={d.get('retCode')} {d.get('retMsg')}"
        except Exception as e:  # rede, timeout, 403 etc.
            ult = str(e)
        time.sleep(1 + 2 * t)
    raise ErroAPI(f"{path} falhou: {ult}")


def klines(symbol, interval, limit=1000, apenas_fechados=True):
    """interval: '15','60','240','D'. Devolve DataFrame (índice = abertura UTC), só candles fechados."""
    lst = _get("/v5/market/kline", {"category": "spot", "symbol": symbol, "interval": interval, "limit": limit})["list"]
    df = pd.DataFrame(lst, columns=["ts", "open", "high", "low", "close", "volume", "turnover"])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    df = df.set_index("ts").astype(float).sort_index()
    if apenas_fechados:
        dur = {"D": pd.Timedelta(days=1), "W": pd.Timedelta(weeks=1)}.get(interval) or pd.Timedelta(minutes=int(interval))
        agora = pd.Timestamp.now(tz="UTC")
        df = df[df.index + dur <= agora]
    return df


def ticker(symbol):
    t = _get("/v5/market/tickers", {"category": "spot", "symbol": symbol})["list"][0]
    return {"last": float(t["lastPrice"]), "bid": float(t["bid1Price"]), "ask": float(t["ask1Price"]),
            "vol24h_usdt": float(t.get("turnover24h", 0) or 0)}


def regras_instrumento(symbol):
    i = _get("/v5/market/instruments-info", {"category": "spot", "symbol": symbol})["list"][0]
    lf = i["lotSizeFilter"]
    return {"status": i["status"], "min_ordem_usdt": float(lf["minOrderAmt"]),
            "base_precision": float(lf["basePrecision"]), "tick": float(i["priceFilter"]["tickSize"])}
