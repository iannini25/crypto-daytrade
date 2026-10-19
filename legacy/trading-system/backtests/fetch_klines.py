"""Baixa candles spot da Bybit (API v5 pública GET /v5/market/kline, category=spot, sem chave) e salva CSV.
Uso: python3 fetch_klines.py [ANOS] [INTERVALO]   (padrão: 3 anos, 15 min)
Busca em janelas de 1000 candles em paralelo (8 threads; bem abaixo do limite de 600 req/5 s por IP).
"""
import csv, json, sys, time, urllib.request, os
from concurrent.futures import ThreadPoolExecutor
BASE = "https://api.bybit.com/v5/market/kline"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def get(params):
    url = BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    for tent in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-research"})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
            if d.get("retCode") == 0:
                return d["result"]["list"]
            print("retCode", d.get("retCode"), d.get("retMsg"), flush=True)
        except Exception as e:
            print("erro", e, flush=True)
        time.sleep(1 + tent * 2)
    raise RuntimeError("falha " + url)

def fetch(symbol, years, interval="15"):
    step = int(interval) * 60 * 1000
    end = (int(time.time() * 1000) // step) * step
    start = end - int(years * 365.25 * 86400 * 1000)
    windows = []
    s = start
    while s < end:
        e = min(s + 999 * step, end)
        windows.append((s, e)); s = e + step
    rows = {}
    with ThreadPoolExecutor(8) as ex:
        for lst in ex.map(lambda w: get({"category": "spot", "symbol": symbol, "interval": interval,
                                          "start": w[0], "end": w[1], "limit": 1000}), windows):
            for k in lst:
                rows[int(k[0])] = k
    ts = sorted(rows)
    path = os.path.join(DIR, f"{symbol}_{interval}m.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ts", "open", "high", "low", "close", "volume", "turnover"])
        for t in ts:
            w.writerow(rows[t][:7])
    print(symbol, len(ts), "candles", time.strftime("%Y-%m-%d", time.gmtime(ts[0] / 1000)), "->",
          time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts[-1] / 1000)), "UTC", path, flush=True)

if __name__ == "__main__":
    os.makedirs(DIR, exist_ok=True)
    yrs = float(sys.argv[1]) if len(sys.argv) > 1 else 3
    itv = sys.argv[2] if len(sys.argv) > 2 else "15"
    for s in SYMBOLS:
        fetch(s, yrs, itv)
