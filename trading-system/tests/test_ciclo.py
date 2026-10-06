"""Teste offline do ciclo: simula stop atingido, saída por regime e kill switch com dados falsos.
Uso: python3 tests/test_ciclo.py   (não acessa a internet, não toca no paper/ real)"""
import os, sys, tempfile, io, contextlib
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ledger as L, bybit_public as B, run_signal as RS, config as C

tmp = tempfile.mkdtemp()
L.DIR = tmp; L.ESTADO = f"{tmp}/estado.json"; L.TRADES = f"{tmp}/trades.csv"; L.PATRIMONIO = f"{tmp}/patrimonio.csv"
L.SINAIS = f"{tmp}/sinais.log"; L.ULTIMO = f"{tmp}/ultimo.json"
C.PARES = ["BTCUSDT"]
now = pd.Timestamp.now(tz="UTC")
CEN = {"tendencia": "alta", "low15": 100000.0, "last": 100000.0}

def fake_klines(sym, interval, limit=1000, apenas_fechados=True):
    if interval == "D":
        idx = pd.date_range(end=now.floor("D") - pd.Timedelta(days=1), periods=300, freq="D", tz="UTC")
        base = np.linspace(60000, 100000, 300) if CEN["tendencia"] == "alta" else np.r_[np.linspace(60000, 110000, 299), 60000]
        return pd.DataFrame({"open": base, "high": base * 1.01, "low": base * 0.99, "close": base, "volume": 1, "turnover": 1}, index=idx)
    idx = pd.date_range(end=now.floor("15min") - pd.Timedelta(minutes=15), periods=50, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": 100000.0, "high": 100500.0, "low": 99800.0, "close": 100000.0, "volume": 1, "turnover": 1}, index=idx)
    df.iloc[-2, df.columns.get_loc("low")] = CEN["low15"]
    return df

B.klines = fake_klines
B.ticker = lambda s: {"last": CEN["last"], "bid": CEN["last"] - 1, "ask": CEN["last"] + 1, "vol24h_usdt": 1} if s != "USDTBRL" else {"last": 5.0, "bid": 5.0, "ask": 5.0}
B.regras_instrumento = lambda s: {"status": "Trading", "min_ordem_usdt": 5.0, "base_precision": 1e-6, "tick": 0.1}

def ciclo(*args):
    sys.argv = ["run_signal.py", "--ignorar-janela", *args]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        RS.main()
    return out.getvalue()


def test_ciclo_offline():
    """Stop, saída por regime e kill switch com dados falsos (sem rede, sem paper/ real)."""
    o = ciclo(); assert "COMPRA BTCUSDT" in o, o
    st = L.carregar(); stop = st["posicoes"]["BTCUSDT"]["stop"]
    # força o check a considerar candles antigos: entrada "há 1 dia"
    st["posicoes"]["BTCUSDT"]["aberta_em_utc"] = str(now - pd.Timedelta(days=1)); st["posicoes"]["BTCUSDT"]["ultimo_check_utc"] = str(now - pd.Timedelta(days=1))
    L.salvar(st)
    CEN["low15"] = stop - 500
    o = ciclo(); assert "stop atingido" in o, o
    tr = L.ler_trades(); assert tr and float(tr[-1]["R"]) < -0.9, tr
    CEN["low15"] = 99800.0
    assert "COMPRA" not in o.split("stop atingido")[1], o
    st = L.carregar(); st["ultimo_stop"] = {}; L.salvar(st)
    o = ciclo(); assert "COMPRA BTCUSDT" in o, o; CEN["tendencia"] = "baixa"
    o = ciclo(); assert "regime virou" in o, o
    # kill switch: caixa artificialmente reduzido
    st = L.carregar(); st["caixa_usdt"] = st["capital_inicial_usdt"] * 0.85; L.salvar(st)
    o = ciclo(); assert "KILL SWITCH ATIVADO" in o, o
    CEN["tendencia"] = "alta"
    o = ciclo(); assert "COMPRA" not in o and "kill switch inativo (" in o, o


if __name__ == "__main__":
    test_ciclo_offline()
    print("Todos os testes passaram. Arquivos temporários em", tmp)
