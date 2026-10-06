/**
 * Espelho legível de trading-system/config.py (06/10/2026).
 * A fonte de verdade do papel é o Python. Este arquivo só mostra os limites no painel.
 */
export const limits = [
  { regra: "Mercado", valor: "Bybit spot, long/flat", detalhe: "Sem derivativo, margem, short ou alavancagem desde a migração de 24/09/2026." },
  { regra: "Pares", valor: "BTCUSDT, ETHUSDT, SOLUSDT", detalhe: "Prioridade nessa ordem. Com ~R$100 cabe uma posição." },
  { regra: "Estratégia", valor: "SMA100 diária + stop 3×ATR14", detalhe: "Entrada na janela seguinte ao fechamento diário acima da média. Sem alvo fixo." },
  { regra: "Janela de entrada", valor: "10:00–12:30 BRT", detalhe: "Saída por regime só nessa janela. O stop é checado o dia todo." },
  { regra: "Taxa spot VIP0", valor: "0,10% + 0,10%", detalhe: "Maker = taker. O backtest ainda soma 0,05% de slippage por lado." },
  { regra: "Risco alvo", valor: "1% do patrimônio", detalhe: "O mínimo de 6 USDT em conta de R$100 empurra o BTC para cerca de 2,4%." },
  { regra: "Teto de risco", valor: "3% por trade", detalhe: "SOL costuma estourar o teto com o stop largo e fica bloqueado." },
  { regra: "Posições", valor: "no máximo 1", detalhe: "Sem reentrada no mesmo par no dia de um stop." },
  { regra: "Perda diária", valor: "−3%", detalhe: "Sem novas entradas até o dia seguinte." },
  { regra: "Perda semanal", valor: "−5%", detalhe: "Sem novas entradas até segunda." },
  { regra: "Kill switch", valor: "90% do capital inicial", detalhe: "Em R$100, para perto de R$90. Só um humano reativa." },
  { regra: "Calendário", valor: "sem CPI, FOMC, payroll, PCE", detalhe: "Nenhuma entrada nova nesses dias. A direção do dado não é palpite da mesa." },
  { regra: "Spread", valor: "≤ 0,10%", detalhe: "Acima disso, não entra." },
  { regra: "Custo em R", valor: "ida e volta ≤ 0,10R", detalhe: "R:R de referência (3R) depois das taxas precisa ser ≥ 2,0." },
] as const;
