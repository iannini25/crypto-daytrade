#!/usr/bin/env python3
"""UM ciclo do sistema de PAPER TRADING (sem chave de API, sem ordem real).

  python3 run_signal.py                  # ciclo normal (respeita a janela 10:00-12:30 BRT)
  python3 run_signal.py --dry-run        # calcula e mostra, mas NÃO grava nada
  python3 run_signal.py --ignorar-janela --dry-run   # teste fora da janela (não grava)
  python3 run_signal.py --status         # só mostra a conta simulada
  python3 run_signal.py --reset-kill-switch "motivo"   # SÓ O HUMANO: reativa após revisão

Passos: 1) marca a mercado as posições simuladas (stop atingido?)  2) checa kill switch e limites
3) saída por regime (diário fechou abaixo da SMA100)  4) novas entradas, se todas as regras passarem
5) grava livro-razão e imprime mensagem em pt-BR (sinal, saída ou "SEM SINAL" com o motivo).
"""
import argparse, sys
from datetime import timedelta
import pandas as pd

import config as C
import estrategia as E
import risco as R
import ledger as L
import bybit_public as B


from fmt import br, pct


def na_janela(dt):
    m = dt.hour * 60 + dt.minute
    return C.JANELA_INICIO[0] * 60 + C.JANELA_INICIO[1] <= m <= C.JANELA_FIM[0] * 60 + C.JANELA_FIM[1]


def usdtbrl():
    try:
        return B.ticker("USDTBRL")["last"], "Bybit USDTBRL ao vivo"
    except Exception:
        return C.USDTBRL_FALLBACK, "valor fixo de reserva (API falhou)"


def fechar(estado, par, preco_bruto, motivo, quando, fx, msgs, acoes):
    p = estado["posicoes"].pop(par)
    px = preco_bruto * (1 - C.SLIPPAGE)
    receita = p["qty"] * px * (1 - C.TAXA)
    taxas = p["taxa_entrada_usdt"] + p["qty"] * px * C.TAXA
    pnl = receita - p["nocional_usdt"]
    Rm = pnl / p["risco_usdt"] if p["risco_usdt"] else float("nan")
    estado["caixa_usdt"] += receita
    L.registrar_trade({"id": p["id"], "par": par, "aberta_em_brt": p["aberta_em_brt"], "fechada_em_brt": L.fmt_brt(quando),
                       "entrada": p["entrada"], "stop_inicial": p["stop"], "saida": round(px, 8), "qty": p["qty"],
                       "nocional_usdt": round(p["nocional_usdt"], 6), "taxas_usdt": round(taxas, 6),
                       "pnl_usdt": round(pnl, 6), "pnl_brl": round(pnl * fx, 4), "R": round(Rm, 3),
                       "motivo_saida": motivo, "motivo_entrada": p.get("motivo", "")})
    if motivo.startswith("stop"):
        estado.setdefault("ultimo_stop", {})[par] = L.agora_brt().strftime("%Y-%m-%d")
    icone = "🛑" if motivo.startswith("stop") or motivo.startswith("kill") else "🔻"
    msgs.append(
        f"{icone} SAÍDA (PAPER) — VENDER {par} (spot)\n"
        f"Quando: {L.fmt_brt(quando)} | Motivo: {motivo}\n"
        f"Entrada: {br(p['entrada'], 2)} → Saída: {br(px, 2)} (com slippage) | Qtd: {p['qty']:.8f}\n"
        f"Resultado líquido: {br(pnl, 4)} USDT ≈ R$ {br(pnl * fx, 2)} ({br(Rm, 2)}R) | taxas pagas {br(taxas, 4)} USDT\n"
        f"⚠️ PAPER TRADING — nenhuma ordem real foi enviada.")
    acoes.append({"tipo": "saida", "par": par, "motivo": motivo, "pnl_usdt": pnl, "R": Rm})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ignorar-janela", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--reset-kill-switch", metavar="MOTIVO")
    a = ap.parse_args()

    agora = L.agora_brt()
    agora_utc = pd.Timestamp.now(tz="UTC")
    fx, fx_fonte = usdtbrl()
    estado = L.carregar()
    if estado is None:
        estado = L.novo_estado(C.CAPITAL_INICIAL_BRL, fx, C.CUSTO_CAMBIO)
        print(f"Conta simulada criada: R$ {br(C.CAPITAL_INICIAL_BRL)} → {br(estado['capital_inicial_usdt'], 4)} USDT "
              f"(USDTBRL {br(fx, 4)}, custo de câmbio {pct(C.CUSTO_CAMBIO, 2)}).")

    if a.reset_kill_switch:
        estado["kill_switch"] = {"ativo": False, "motivo": f"reativado por humano: {a.reset_kill_switch}", "em_brt": L.fmt_brt()}
        L.salvar(estado); print("Kill switch reativado pelo humano. Motivo registrado."); return

    msgs, acoes, razoes, checklist_glob = [], [], {}, []
    precos, avaliacoes, regras = {}, {}, {}
    erros = []

    # ---------- dados de mercado (públicos) ----------
    for par in C.PARES:
        try:
            d = B.klines(par, "D", limit=300)
            precos[par] = B.ticker(par)
            regras[par] = B.regras_instrumento(par)
            av = E.avaliar(d)
            av["idade_h"] = (agora_utc - (d.index[-1] + pd.Timedelta(days=1))).total_seconds() / 3600
            avaliacoes[par] = av
        except Exception as e:
            erros.append(f"{par}: {e}")

    # ---------- 1) marcação a mercado das posições abertas (stop atingido?) ----------
    for par in list(estado["posicoes"].keys()):
        p = estado["posicoes"][par]
        try:
            m15 = B.klines(par, "15", limit=1000)   # ~10 dias de candles de 15m fechados
        except Exception as e:
            erros.append(f"{par} (15m): {e}"); continue
        ini_pos = pd.Timestamp(p["aberta_em_utc"]).ceil("15min")   # só candles inteiros DEPOIS da entrada
        desde = pd.Timestamp(p["ultimo_check_utc"]).floor("15min")
        m15 = m15[(m15.index >= ini_pos) & (m15.index + pd.Timedelta(minutes=15) > desde)]
        hit = None
        for ts, row in m15.iterrows():
            if row["low"] <= p["stop"]:
                hit = (ts, min(row["open"], p["stop"])); break   # gap abaixo do stop: executa na abertura (pior)
        if hit is None and par in precos and precos[par]["last"] <= p["stop"]:
            hit = (agora_utc, precos[par]["last"])
        if hit:
            fechar(estado, par, hit[1], f"stop atingido em {br(p['stop'], 2)}", hit[0].tz_convert(L.BRT) if hasattr(hit[0], 'tz_convert') else agora, fx, msgs, acoes)
        else:
            p["ultimo_check_utc"] = str(agora_utc)

    def patrimonio():
        v = sum(p["qty"] * precos.get(s, {"bid": p["entrada"]})["bid"] * (1 - C.TAXA) for s, p in estado["posicoes"].items())
        return estado["caixa_usdt"] + v, v

    pat, vpos = patrimonio()
    # referências diária/semanal (definidas no 1º ciclo do dia/semana)
    hoje = agora.strftime("%Y-%m-%d"); semana = agora.strftime("%G-W%V")
    if not estado.get("ref_dia") or estado["ref_dia"]["data"] != hoje:
        estado["ref_dia"] = {"data": hoje, "patrimonio_usdt": pat}
    if not estado.get("ref_semana") or estado["ref_semana"]["semana"] != semana:
        estado["ref_semana"] = {"semana": semana, "patrimonio_usdt": pat}

    # ---------- 2) kill switch e limites ----------
    limites = R.checar_limites(estado, pat)
    ks_ok = [x for x in limites if x[0] == "kill_switch"][0][1]
    if not ks_ok and not estado["kill_switch"]["ativo"]:
        estado["kill_switch"] = {"ativo": True, "motivo": "patrimônio caiu para <= 90% do capital inicial", "em_brt": L.fmt_brt()}
        for par in list(estado["posicoes"].keys()):
            fechar(estado, par, precos[par]["bid"], "kill switch (-10% do capital inicial)", agora, fx, msgs, acoes)
        msgs.append("🚨 KILL SWITCH ATIVADO — sistema PARADO. Nenhuma entrada nova até revisão humana "
                    "(python3 run_signal.py --reset-kill-switch \"motivo\").")
        pat, vpos = patrimonio()
    bloqueio_limites = [f"{n}: {det}" for n, ok, det in limites if not ok]

    janela_ok = na_janela(agora) or a.ignorar_janela
    evento = C.EVENTOS_BLOQUEIO.get(hoje)

    # ---------- 3) saída por regime ----------
    for par in list(estado["posicoes"].keys()):
        av = avaliacoes.get(par)
        if av and not av["regime_alta"]:
            if janela_ok:
                fechar(estado, par, precos[par]["bid"],
                       f"regime virou: fechamento diário {br(av['fechamento'], 2)} < SMA{E.SMA_N} {br(av['sma'], 2)}",
                       agora, fx, msgs, acoes)
            else:
                razoes[par] = "saída por regime PENDENTE — será executada na próxima janela 10:00–12:30 BRT"
    pat, vpos = patrimonio()

    # ---------- 4) entradas ----------
    for par in C.PARES:
        if par in estado["posicoes"]:
            p = estado["posicoes"][par]
            razoes.setdefault(par, f"posição simulada aberta desde {p['aberta_em_brt']} (stop {br(p['stop'], 2)}); regime segue de alta")
            continue
        av = avaliacoes.get(par)
        if av is None:
            razoes[par] = "sem dados (falha na API) — falha segura, nada a fazer"; continue
        if not av["regime_alta"]:
            razoes[par] = (f"regime de BAIXA: fechamento diário {br(av['fechamento'], 2)} abaixo da SMA{E.SMA_N} "
                           f"{br(av['sma'], 2)} ({pct(av['dist_sma_pct'])}) → ficar em USDT"); continue
        tk, rg = precos[par], regras[par]
        entrada = tk["ask"] * (1 + C.SLIPPAGE)
        stop = entrada - av["stop_dist"]
        alvo_ref = entrada + E.ALVO_REF_R * av["stop_dist"]
        spread = (tk["ask"] - tk["bid"]) / ((tk["ask"] + tk["bid"]) / 2)
        dim = R.dimensionar(pat, estado["caixa_usdt"], entrada, av["stop_dist"], rg["min_ordem_usdt"])
        custo_ok, custo_R = R.checar_custo_em_R(av["stop_dist"] / entrada)
        rr = R.rr_pos_taxas(entrada, stop, alvo_ref)
        checks = [
            ("dado diário fresco", av["idade_h"] <= C.MAX_IDADE_CANDLE_H, f"último candle fechou há {br(av['idade_h'], 1)} h"),
            ("instrumento negociando", rg["status"] == "Trading", rg["status"]),
            ("janela 10:00–12:30 BRT", janela_ok, "teste fora da janela (--ignorar-janela)" if a.ignorar_janela and not na_janela(agora) else L.fmt_brt(agora)),
            ("sem CPI/FOMC/payroll hoje", evento is None, evento or "nenhum evento no calendário"),
            ("kill switch inativo", not estado["kill_switch"]["ativo"] and ks_ok, f"gatilho R$ {br(C.KILL_SWITCH_FRACAO * C.CAPITAL_INICIAL_BRL)}"),
            ("perdas dia/semana no limite", not bloqueio_limites, "; ".join(bloqueio_limites) or "ok"),
            ("sem stop neste par hoje", estado.get("ultimo_stop", {}).get(par) != hoje, "esfriamento: não reentra no mesmo dia após stop"),
            ("vaga de posição", len(estado["posicoes"]) < C.MAX_POSICOES, f"{len(estado['posicoes'])}/{C.MAX_POSICOES} abertas"),
            ("spread ≤ 0,10%", spread <= C.SPREAD_MAX, pct(spread, 3)),
            (f"mínimo de ordem {br(rg['min_ordem_usdt'], 0)} USDT e risco ≤ {pct(C.RISCO_MAX_TRADE, 0)}", dim["ok"], dim.get("motivo") or "ok"),
            ("custo ≤ 0,10R", custo_ok, f"{br(custo_R, 3)}R"),
            (f"R:R de referência após taxas ≥ {br(C.RR_MIN_POS_TAXAS, 1)}", rr >= C.RR_MIN_POS_TAXAS, br(rr, 2)),
        ]
        falhas = [f"{n} ({det})" for n, ok, det in checks if not ok]
        if falhas:
            razoes[par] = "regime de ALTA, mas entrada BLOQUEADA: " + "; ".join(falhas); continue
        # ---- abre posição simulada ----
        noc = dim["nocional"]; qty = noc * (1 - C.TAXA) / entrada
        estado["seq_trade"] += 1
        tid = f"P{estado['seq_trade']:04d}"
        motivo = (f"fechamento diário {br(av['fechamento'], 2)} > SMA{E.SMA_N} {br(av['sma'], 2)} ({pct(av['dist_sma_pct'])}); "
                  f"ATR14 diário {br(av['atr'], 2)}")
        estado["posicoes"][par] = {"id": tid, "qty": qty, "entrada": round(entrada, 8), "stop": round(stop, 8),
                                   "nocional_usdt": noc, "taxa_entrada_usdt": noc * C.TAXA, "risco_usdt": dim["risco_usdt"],
                                   "aberta_em_brt": L.fmt_brt(agora), "aberta_em_utc": str(agora_utc),
                                   "ultimo_check_utc": str(agora_utc), "motivo": motivo}
        estado["caixa_usdt"] -= noc
        cl = " ".join(f"[✓] {n}" for n, ok, det in checks)
        msgs.append(
            f"📈 SINAL (PAPER) — COMPRA {par} (spot, long)\n"
            f"Data/hora: {L.fmt_brt(agora)} | ID {tid}\n"
            f"Estratégia: tendência diária SMA{E.SMA_N} + stop {br(E.ATR_MULT, 0)}×ATR14 (evidência 🟢 trend following; backtest próprio positivo após taxas, ver backtests/RESULTADOS.md)\n"
            f"Entrada: ordem LIMITE ~{br(tk['ask'], 2)} USDT (simulada a {br(entrada, 2)} c/ slippage)\n"
            f"Stop: {br(stop, 2)} ({pct(-dim['stop_pct'])}) → ordem SL na corretora, válida 24h\n"
            f"Alvo: SEM alvo fixo — sai quando o diário fechar abaixo da SMA{E.SMA_N} (hoje {br(av['sma'], 2)}). "
            f"Referência {br(E.ALVO_REF_R, 0)}R = {br(alvo_ref, 2)}\n"
            f"Tamanho: {br(noc, 2)} USDT ({qty:.8f} {par[:-4]}) = {pct(noc / pat)} do patrimônio\n"
            f"Risco até o stop (c/ taxas e slippage): {br(dim['risco_usdt'], 4)} USDT ≈ R$ {br(dim['risco_usdt'] * fx, 2)} "
            f"({pct(dim['risco_pct'])} do capital)\n"
            f"R:R de referência após taxas: {br(rr, 2)} | custo ida+volta {pct(R.custos_ida_volta(), 2)} = {br(custo_R, 3)}R\n"
            f"Motivo: {motivo}\n"
            + (f"Obs.: {dim['obs']}\n" if dim.get("obs") else "")
            + f"Checklist: {cl}\n"
            f"⚠️ PAPER TRADING — nenhuma ordem real foi enviada.")
        acoes.append({"tipo": "entrada", "par": par, "id": tid, "entrada": entrada, "stop": stop, "nocional": noc,
                      "risco_usdt": dim["risco_usdt"]})
        razoes[par] = f"ENTRADA simulada {tid}"

    pat, vpos = patrimonio()
    ini = estado["capital_inicial_usdt"]
    status = (f"Conta simulada: patrimônio {br(pat, 4)} USDT ≈ R$ {br(pat * fx, 2)} "
              f"({pct(pat / ini - 1, 2)} desde o início; USDTBRL {br(fx, 4)} — {fx_fonte}) | caixa {br(estado['caixa_usdt'], 4)} USDT | "
              f"posições {len(estado['posicoes'])} | kill switch {'ATIVO' if estado['kill_switch']['ativo'] else 'inativo'} "
              f"(gatilho {br(C.KILL_SWITCH_FRACAO * ini, 2)} USDT)")

    cab = f"=== Ciclo paper trading — {L.fmt_brt(agora)} {'(DRY-RUN, nada gravado)' if a.dry_run else ''}==="
    linhas = [cab]
    if a.status:
        linhas.append(status); print("\n".join(linhas)); return
    if msgs:
        linhas += msgs
    else:
        linhas.append("SEM SINAL.")
    linhas.append("Por par:")
    for par in C.PARES:
        av = avaliacoes.get(par)
        extra = f" [preço {br(precos[par]['last'], 2)}]" if par in precos else ""
        linhas.append(f"  • {par}{extra}: {razoes.get(par, '—')}")
    if not na_janela(agora) and not a.ignorar_janela:
        linhas.append("  (Fora da janela 10:00–12:30 BRT: entradas e saídas por regime só acontecem dentro dela; "
                      "o stop é checado em todo ciclo.)")
    if erros:
        linhas.append("Erros de dados (falha segura): " + " | ".join(erros))
    linhas.append(status)
    texto = "\n".join(linhas)
    print(texto)

    if not a.dry_run:
        estado["ultima_execucao_brt"] = L.fmt_brt(agora)
        L.salvar(estado)
        L.registrar_patrimonio({"ts_brt": L.fmt_brt(agora), "patrimonio_usdt": round(pat, 6), "patrimonio_brl": round(pat * fx, 4),
                                "usdtbrl": fx, "caixa_usdt": round(estado["caixa_usdt"], 6), "valor_posicoes_usdt": round(vpos, 6),
                                "pnl_desde_inicio_pct": round(pat / ini - 1, 6), "kill_switch": estado["kill_switch"]["ativo"]})
        L.registrar_mensagem(texto)
        L.salvar_ultimo({"ts_brt": L.fmt_brt(agora), "acoes": acoes, "razoes": razoes, "avaliacoes": avaliacoes,
                         "patrimonio_usdt": pat, "patrimonio_brl": pat * fx, "erros": erros})


if __name__ == "__main__":
    main()
