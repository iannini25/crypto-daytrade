"""Registrador: estado da conta simulada + livro-razão (CSV) do paper trading."""
import csv, json, os
from datetime import datetime, timezone, timedelta

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper")
ESTADO = os.path.join(DIR, "estado.json")
TRADES = os.path.join(DIR, "trades.csv")
PATRIMONIO = os.path.join(DIR, "patrimonio.csv")
SINAIS = os.path.join(DIR, "sinais.log")
ULTIMO = os.path.join(DIR, "ultimo_ciclo.json")
BRT = timezone(timedelta(hours=-3))

CAMPOS_TRADES = ["id", "par", "aberta_em_brt", "fechada_em_brt", "entrada", "stop_inicial", "saida", "qty",
                 "nocional_usdt", "taxas_usdt", "pnl_usdt", "pnl_brl", "R", "motivo_saida", "motivo_entrada"]
CAMPOS_PAT = ["ts_brt", "patrimonio_usdt", "patrimonio_brl", "usdtbrl", "caixa_usdt", "valor_posicoes_usdt",
              "pnl_desde_inicio_pct", "kill_switch"]


def agora_brt():
    return datetime.now(BRT)


def fmt_brt(dt=None):
    return (dt or agora_brt()).astimezone(BRT).strftime("%d/%m/%Y %H:%M BRT")


def carregar():
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            return json.load(f)
    return None


def novo_estado(capital_brl, usdtbrl, custo_cambio):
    usdt = capital_brl / usdtbrl * (1 - custo_cambio)
    return {"criado_em_brt": fmt_brt(), "capital_inicial_brl": capital_brl, "usdtbrl_inicial": usdtbrl,
            "capital_inicial_usdt": round(usdt, 6), "caixa_usdt": usdt, "posicoes": {},
            "kill_switch": {"ativo": False, "motivo": None, "em_brt": None},
            "ref_dia": None, "ref_semana": None, "seq_trade": 0, "ultima_execucao_brt": None}


def salvar(estado):
    os.makedirs(DIR, exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ESTADO)


def _append(path, campos, linha):
    os.makedirs(DIR, exist_ok=True)
    novo = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        if novo:
            w.writeheader()
        w.writerow({k: linha.get(k, "") for k in campos})


def registrar_trade(linha):
    _append(TRADES, CAMPOS_TRADES, linha)


def registrar_patrimonio(linha):
    _append(PATRIMONIO, CAMPOS_PAT, linha)


def registrar_mensagem(texto):
    os.makedirs(DIR, exist_ok=True)
    with open(SINAIS, "a") as f:
        f.write(texto.rstrip() + "\n" + "-" * 60 + "\n")


def salvar_ultimo(d):
    os.makedirs(DIR, exist_ok=True)
    with open(ULTIMO, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False, default=str)


def ler_trades():
    if not os.path.exists(TRADES):
        return []
    with open(TRADES) as f:
        return list(csv.DictReader(f))
