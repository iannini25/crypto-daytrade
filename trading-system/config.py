"""Configuração do sistema de PAPER TRADING (nenhuma chave de API, nenhuma ordem real).
Todos os valores monetários de risco são checados em R$ e em USDT.
"""
# ---------- conta (simulada) ----------
CAPITAL_INICIAL_BRL = 100.0
CUSTO_CAMBIO = 0.0044          # BRL->USDT: spread ~0,24% + taxa 0,20% no USDTBRL (cripto-estudo/14-bybit.md §3 e §5)
USDTBRL_FALLBACK = 5.0483      # usado só se a API falhar (valor de 06/10/2026 ~00:42 BRT)

# ---------- mercado ----------
PARES = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]   # ordem = prioridade quando só cabe 1 posição
TAXA = 0.001                   # 0,10% por lado (spot VIP0, maker = taker) — conferir "My Fee Rate" no app
SLIPPAGE = 0.0005              # 0,05% por lado (premissa modesta; backtest também testou 0,15%)
MIN_ORDEM_USDT = 5.0           # minOrderAmt spot (API instruments-info) — o programa relê da API a cada ciclo
FOLGA_MIN_ORDEM = 1.2          # posição mínima = 6 USDT, p/ ainda conseguir VENDER (>=5 USDT) depois de cair até o stop
SPREAD_MAX = 0.001             # 0,10%: acima disso, não entra

# ---------- janela de execução (BRT = UTC-3) ----------
JANELA_INICIO = (10, 0)        # 10:00 BRT
JANELA_FIM = (12, 30)          # 12:30 BRT

# ---------- regras de risco (Gestor de Risco) ----------
RISCO_ALVO_TRADE = 0.01        # ideal: 1% do capital por trade
RISCO_MAX_TRADE = 0.03         # teto ABSOLUTO (exceção de conta pequena: o mínimo de 6 USDT força ~2-3%)
MAX_POSICOES = 1               # com ~US$20 só cabe 1 posição mínima de forma sensata
PERDA_DIARIA_MAX = 0.03        # -3% do patrimônio no dia -> sem novas entradas até amanhã
PERDA_SEMANAL_MAX = 0.05       # -5% na semana (seg-dom) -> sem novas entradas até segunda
KILL_SWITCH_FRACAO = 0.90      # patrimônio <= 90% do capital inicial (R$90) -> PARA TUDO; só humano reativa
CUSTO_MAX_EM_R = 0.10          # custos ida+volta (taxas+slippage) <= 10% do risco (1R)
RR_MIN_POS_TAXAS = 2.0         # R:R mínimo do alvo de referência (3R) depois das taxas
MAX_IDADE_CANDLE_H = 26        # dado diário mais velho que isso -> sem sinal (falha segura)

# ---------- calendário macro (BRT). Atualizar toda semana (agente Pesquisador). ----------
# Fonte: cripto-estudo/13-noticias-e-movimentos.md (BLS/Fed). Sem NOVAS entradas nesses dias.
EVENTOS_BLOQUEIO = {
    "2026-10-14": "CPI EUA 09:30 BRT",
    "2026-10-28": "FOMC 15:00 BRT (coletiva 15:30)",
    "2026-10-29": "PIB 3T + PCE 09:30 BRT",
    "2026-11-06": "Payroll 10:30 BRT (após fim do horário de verão nos EUA)",
    "2026-11-10": "CPI EUA 10:30 BRT",
}
