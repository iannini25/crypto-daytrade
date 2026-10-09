# Trading algorítmico — resumo do que ficou de pé

**Data do teste:** candles Bybit spot de 06/10/2023 a 06/10/2026. Parâmetros escritos antes de olhar o resultado. Custo base: taxa 0,10% + slippage 0,05% por lado.

> Backtest mostra o que uma regra fixa **teria** feito num período que já passou. **Não é recomendação de investimento** e não é previsão. Números completos: [`trading-system/backtests/results/RESULTADOS.md`](../trading-system/backtests/results/RESULTADOS.md). Não reescreva esses CSVs à mão.

## O que o teste próprio separou

Famílias **diárias** de tendência (SMA 50/100/200 e momentum de 14/28/56 dias) ficaram positivas depois dos custos nos três pares e nas duas metades da amostra (corte em 06/04/2025). Raramente bateram o buy-and-hold em retorno. Em geral cortaram a pior queda.

Famílias de **15 minutos** (rompimento e pullback) e a **reversão à média em 1h** ficaram negativas depois da taxa, nos três pares, dentro e fora da amostra. Sem custo, ficaram perto de zero. Por isso saíram da mesa.

Escolher o período da média a cada trimestre (walk-forward) **não melhorou** o N fixo em 100. No SOL fora da amostra, piorou (−7,9% contra +9,4% ao ano). A média fica em 100.

## A regra que o paper usa

- Regime: último diário **fechado** acima da SMA(100). Candle diário UTC, fecha 21:00 BRT.
- Entrada: só na janela **10:00–12:30 BRT** do dia seguinte, se o risco deixar.
- Stop: entrada − **3 × ATR(14)** diário. Vale o dia todo.
- Saída de regime: diário fechou abaixo da SMA100 → vende na janela seguinte. Sem alvo fixo.
- Spot, long ou flat. Prioridade BTCUSDT, depois ETH, depois SOL. **Uma posição.**
- Conta de R$100: risco-alvo 1%, mas o mínimo de 6 USDT manda. Teto absoluto **3%**. O que passar do teto não entra.

Variante com 100% do capital existe no relatório só como comparação. A conta pequena **não** opera all-in.

## Conta de R$100 (variante `ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100`)

| Par | Período | CAGR | Pior queda | Trades | Acerto | R$100 vira | Dias bloqueados |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 3 anos | +14,2% | −13,7% | 19 | 42% | R$148 | 12 |
| BTCUSDT | 2ª metade | +2,4% | −6,8% | 9 | 44% | — | — |
| ETHUSDT | 3 anos | +6,5% | −21,8% | 8 | 25% | R$120 | 309 |
| SOLUSDT | 3 anos | +5,1% | −4,5% | 1 | 100% | R$115 | 527 |

SOL quase não opera: o stop largo faz a posição mínima passar de 3% do capital. Um trade só não é evidência.

Monte Carlo (bootstrap, 20 mil caminhos, ~7 trades/ano, risco ~2,7% no BTC, 3 anos): mediana **R$137**; cerca de **9%** de chance de tocar R$90; cerca de **0,2%** de chegar a R$500. Com risco de ~9% (perto do all-in) a chance de tocar R$90 sobe para ~48%. O kill switch existe para não aceitar esse caminho.

Expectativa do BTC na amostra de 21 trades: +0,74R, e **+0,14R se tirar o melhor trade**. Amostra curta.

## O que a mesa recusa mesmo se "parecer óbvio"

- Grade e DCA como vantagem estatística. Grade acumula na queda e vende cedo na alta. DCA é forma de aportar.
- Alvo de volatilidade fino com R$100: o ajuste cai no mínimo de ordem. Fica para uma conta maior.
- Otimizar parâmetro depois de ver o resultado.
- Operar com dado velho, API falhando ou spread acima de 0,10%. Falha segura = sem sinal.
