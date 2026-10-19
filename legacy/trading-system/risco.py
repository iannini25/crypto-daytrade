"""Gestor de Risco: regras DURAS. Cada função devolve (ok: bool, motivo: str).
Nenhuma regra pode ser desligada pelo Agente de Sinais; só o humano muda config.py.
"""
import config as C
from fmt import br, pct


def custos_ida_volta():
    return 2 * (C.TAXA + C.SLIPPAGE)


def dimensionar(patrimonio_usdt, caixa_usdt, preco_entrada, stop_dist, min_ordem_usdt):
    """Tamanho pela regra de risco, respeitando o mínimo de ordem da Bybit.
    Devolve dict com nocional e risco, ou motivo de bloqueio."""
    stop_pct = stop_dist / preco_entrada
    risco_por_usdt = stop_pct + custos_ida_volta()          # perda por 1 USDT de posição se o stop for atingido
    alvo = patrimonio_usdt * C.RISCO_ALVO_TRADE / risco_por_usdt
    minimo = min_ordem_usdt * C.FOLGA_MIN_ORDEM
    nocional = max(alvo, minimo)
    nocional = min(nocional, caixa_usdt * 0.998)
    obs = None
    if alvo < minimo:
        obs = (f"tamanho ideal p/ risco de {pct(C.RISCO_ALVO_TRADE, 0)} seria {br(alvo)} USDT, abaixo do mínimo prático "
               f"de {br(minimo)} USDT (mínimo da Bybit {br(min_ordem_usdt, 0)} USDT + 20% de folga) → usando o mínimo")
    if nocional < minimo:
        return {"ok": False, "motivo": f"caixa insuficiente para a posição mínima de {br(minimo)} USDT"}
    risco = nocional * risco_por_usdt
    if risco > C.RISCO_MAX_TRADE * patrimonio_usdt:
        return {"ok": False, "motivo": (f"posição mínima de {br(nocional)} USDT com stop a {pct(stop_pct)} arriscaria "
                                        f"{pct(risco / patrimonio_usdt)} do capital (> teto de {pct(C.RISCO_MAX_TRADE, 0)})")}
    return {"ok": True, "nocional": nocional, "risco_usdt": risco, "risco_pct": risco / patrimonio_usdt,
            "stop_pct": stop_pct, "obs": obs}


def rr_pos_taxas(entrada, stop, alvo):
    f = C.TAXA + C.SLIPPAGE
    ganho = alvo * (1 - f) - entrada * (1 + C.TAXA)
    perda = entrada * (1 + C.TAXA) - stop * (1 - f)
    return ganho / perda if perda > 0 else float("nan")


def checar_custo_em_R(stop_pct):
    cr = custos_ida_volta() / stop_pct
    return cr <= C.CUSTO_MAX_EM_R, cr


def checar_limites(estado, patrimonio_usdt):
    """Kill switch e perdas diária/semanal. Devolve lista de (regra, ok, detalhe)."""
    out = []
    ini = estado["capital_inicial_usdt"]
    lim = C.KILL_SWITCH_FRACAO * ini
    out.append(("kill_switch", not estado["kill_switch"]["ativo"] and patrimonio_usdt > lim,
                f"patrimônio {br(patrimonio_usdt)} USDT vs gatilho {br(lim)} USDT ({pct(C.KILL_SWITCH_FRACAO, 0)} do inicial)"))
    rd = estado.get("ref_dia") or {}
    if rd.get("patrimonio_usdt"):
        var = patrimonio_usdt / rd["patrimonio_usdt"] - 1
        out.append(("perda_diaria", var > -C.PERDA_DIARIA_MAX, f"variação no dia {pct(var, 2)} (limite -{pct(C.PERDA_DIARIA_MAX, 0)})"))
    rs = estado.get("ref_semana") or {}
    if rs.get("patrimonio_usdt"):
        var = patrimonio_usdt / rs["patrimonio_usdt"] - 1
        out.append(("perda_semanal", var > -C.PERDA_SEMANAL_MAX, f"variação na semana {pct(var, 2)} (limite -{pct(C.PERDA_SEMANAL_MAX, 0)})"))
    return out
