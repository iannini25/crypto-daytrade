# Resultados dos backtests (gerado por make_report.py)

Dados: Bybit spot, API v5 pública `/v5/market/kline` (15m: 06/10/2023–06/10/2026; 1h: 06/10/2021–06/10/2026, usado para aquecer indicadores). Avaliação: **06/10/2023 → 06/10/2026**. "IS" = 06/10/2023–05/04/2025, "OOS" = 06/04/2025–06/10/2026. Os parâmetros foram fixados **antes** de olhar os resultados (nenhum foi otimizado), então a 2ª metade funciona como teste fora da amostra. Custos base: **0,10% de taxa + 0,05% de slippage por lado** (0,30% ida e volta); estresse: 0,10% + 0,15%. Posição = 100% do capital quando comprado (comparável ao buy-and-hold), salvo indicação. "R$100 vira" desconta ~0,44% de câmbio na entrada e na saída (BRL↔USDT) e ignora a variação do dólar.

## 1. Período total (3 anos), custos base

| Estratégia | Par | CAGR | Máx. DD | Sharpe | Trades | Acerto | Média/trade | Expect. (R) | PF | Tempo comprado | R$100 vira |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BH_comprar_segurar | BTCUSDT | +46,5% | -53,7% | 1,03 | 0 | — | — | — | — | 100% | R$ 312 |
| D_SMA50_exec_21hBRT | BTCUSDT | +49,8% | -28,5% | 1,33 | 33 | 24% | +3,2% | — | 2,77 | 60% | R$ 333 |
| D_SMA100_exec_21hBRT | BTCUSDT | +41,9% | -37,6% | 1,20 | 22 | 18% | +7,0% | — | 4,38 | 59% | R$ 284 |
| D_SMA100_exec_10hBRT | BTCUSDT | +45,8% | -34,2% | 1,28 | 22 | 45% | +7,4% | — | 4,95 | 59% | R$ 308 |
| D_SMA200_exec_21hBRT | BTCUSDT | +39,8% | -34,5% | 1,09 | 15 | 33% | +9,1% | — | 6,59 | 62% | R$ 271 |
| D_TSMOM14_exec_21hBRT | BTCUSDT | +42,3% | -31,3% | 1,21 | 71 | 34% | +2,0% | — | 2,20 | 57% | R$ 286 |
| D_TSMOM28_exec_21hBRT | BTCUSDT | +32,1% | -37,5% | 0,96 | 52 | 37% | +1,2% | — | 1,61 | 59% | R$ 229 |
| D_TSMOM28_exec_10hBRT | BTCUSDT | +41,5% | -32,8% | 1,16 | 52 | 42% | +1,5% | — | 1,94 | 59% | R$ 281 |
| D_TSMOM56_exec_21hBRT | BTCUSDT | +35,7% | -45,9% | 1,06 | 33 | 27% | +4,0% | — | 2,57 | 59% | R$ 248 |
| D_SMA100_voltarget40 | BTCUSDT | +34,6% | -26,8% | 1,24 | 22 | 23% | +5,5% | — | 4,19 | 59% | R$ 242 |
| H4_Donchian20_vol | BTCUSDT | +11,1% | -38,6% | 0,50 | 73 | 38% | +0,6% | — | 1,35 | 32% | R$ 136 |
| H4_EMA50_filtroD_SMA100 | BTCUSDT | +18,2% | -37,4% | 0,72 | 155 | 26% | +0,4% | — | 1,46 | 39% | R$ 164 |
| H1_reversao_BB_em_tendencia | BTCUSDT | -29,5% | -66,6% | -2,18 | 348 | 49% | -0,3% | -0,26R | 0,59 | — | R$ 35 |
| M15_rompimento_stop1xATR1h_2R | BTCUSDT | -16,6% | -44,7% | -2,54 | 203 | 30% | -0,3% | -0,59R | 0,50 | — | R$ 58 |
| M15_rompimento_stop1.5xATR15m_2R | BTCUSDT | -17,2% | -44,2% | -3,21 | 203 | 28% | -0,3% | -0,81R | 0,42 | — | R$ 56 |
| M15_pullbackEMA21_stop1xATR1h_2R | BTCUSDT | -25,7% | -59,8% | -3,21 | 344 | 33% | -0,3% | -0,44R | 0,50 | — | R$ 41 |
| BH_comprar_segurar | ETHUSDT | +19,0% | -69,2% | 0,58 | 0 | — | — | — | — | 100% | R$ 167 |
| D_SMA50_exec_21hBRT | ETHUSDT | +62,6% | -38,8% | 1,30 | 23 | 35% | +8,3% | — | 4,03 | 53% | R$ 426 |
| D_SMA100_exec_21hBRT | ETHUSDT | +34,4% | -46,7% | 0,89 | 23 | 17% | +5,8% | — | 3,00 | 52% | R$ 241 |
| D_SMA100_exec_10hBRT | ETHUSDT | +23,7% | -59,0% | 0,70 | 23 | 26% | +4,5% | — | 2,23 | 52% | R$ 188 |
| D_SMA200_exec_21hBRT | ETHUSDT | +29,7% | -40,0% | 0,80 | 12 | 33% | +8,4% | — | 5,90 | 49% | R$ 216 |
| D_TSMOM14_exec_21hBRT | ETHUSDT | +24,3% | -46,8% | 0,69 | 68 | 35% | +1,7% | — | 1,63 | 51% | R$ 190 |
| D_TSMOM28_exec_21hBRT | ETHUSDT | +29,5% | -46,7% | 0,81 | 46 | 37% | +2,4% | — | 1,91 | 52% | R$ 215 |
| D_TSMOM28_exec_10hBRT | ETHUSDT | +26,9% | -51,6% | 0,76 | 46 | 41% | +2,3% | — | 1,84 | 52% | R$ 203 |
| D_TSMOM56_exec_21hBRT | ETHUSDT | +62,5% | -41,5% | 1,29 | 24 | 42% | +7,6% | — | 4,58 | 55% | R$ 426 |
| D_SMA100_voltarget40 | ETHUSDT | +25,1% | -33,6% | 0,98 | 23 | 17% | +4,2% | — | 2,96 | 52% | R$ 194 |
| H4_Donchian20_vol | ETHUSDT | +20,5% | -49,2% | 0,68 | 74 | 32% | +1,2% | — | 1,47 | 34% | R$ 173 |
| H4_EMA50_filtroD_SMA100 | ETHUSDT | +5,0% | -46,5% | 0,31 | 160 | 16% | +0,3% | — | 1,21 | 33% | R$ 115 |
| H1_reversao_BB_em_tendencia | ETHUSDT | -26,9% | -65,5% | -1,63 | 318 | 53% | -0,3% | -0,18R | 0,67 | — | R$ 39 |
| M15_rompimento_stop1xATR1h_2R | ETHUSDT | -12,0% | -32,0% | -1,44 | 164 | 35% | -0,2% | -0,32R | 0,65 | — | R$ 68 |
| M15_rompimento_stop1.5xATR15m_2R | ETHUSDT | -13,0% | -34,1% | -1,86 | 164 | 34% | -0,2% | -0,43R | 0,58 | — | R$ 65 |
| M15_pullbackEMA21_stop1xATR1h_2R | ETHUSDT | -32,3% | -69,0% | -3,38 | 305 | 29% | -0,4% | -0,44R | 0,47 | — | R$ 31 |
| BH_comprar_segurar | SOLUSDT | +74,3% | -78,7% | 1,07 | 0 | — | — | — | — | 100% | R$ 526 |
| D_SMA50_exec_21hBRT | SOLUSDT | +68,2% | -61,4% | 1,13 | 31 | 23% | +2,1% | — | 1,49 | 56% | R$ 472 |
| D_SMA100_exec_21hBRT | SOLUSDT | +59,4% | -71,1% | 1,04 | 31 | 19% | +14,3% | — | 5,39 | 52% | R$ 402 |
| D_SMA100_exec_10hBRT | SOLUSDT | +61,0% | -69,3% | 1,05 | 31 | 23% | +14,5% | — | 5,38 | 52% | R$ 414 |
| D_SMA200_exec_21hBRT | SOLUSDT | +74,6% | -60,6% | 1,16 | 13 | 23% | +0,3% | — | 1,06 | 54% | R$ 528 |
| D_TSMOM14_exec_21hBRT | SOLUSDT | +75,2% | -48,9% | 1,21 | 63 | 51% | +4,3% | — | 2,74 | 54% | R$ 534 |
| D_TSMOM28_exec_21hBRT | SOLUSDT | +79,0% | -57,9% | 1,24 | 38 | 34% | +1,8% | — | 1,59 | 57% | R$ 570 |
| D_TSMOM28_exec_10hBRT | SOLUSDT | +79,0% | -65,1% | 1,23 | 38 | 32% | +1,8% | — | 1,55 | 57% | R$ 569 |
| D_TSMOM56_exec_21hBRT | SOLUSDT | +66,0% | -74,0% | 1,12 | 43 | 35% | +10,0% | — | 4,04 | 56% | R$ 454 |
| D_SMA100_voltarget40 | SOLUSDT | +28,8% | -33,1% | 1,13 | 31 | 19% | +3,9% | — | 3,84 | 52% | R$ 212 |
| H4_Donchian20_vol | SOLUSDT | +46,4% | -52,9% | 1,01 | 76 | 45% | +2,1% | — | 1,81 | 30% | R$ 311 |
| H4_EMA50_filtroD_SMA100 | SOLUSDT | +29,2% | -64,2% | 0,72 | 162 | 21% | +1,0% | — | 1,58 | 35% | R$ 214 |
| H1_reversao_BB_em_tendencia | SOLUSDT | -25,3% | -67,3% | -1,17 | 298 | 54% | -0,3% | -0,14R | 0,77 | — | R$ 41 |
| M15_rompimento_stop1xATR1h_2R | SOLUSDT | -16,0% | -46,9% | -1,45 | 155 | 32% | -0,3% | -0,32R | 0,64 | — | R$ 59 |
| M15_rompimento_stop1.5xATR15m_2R | SOLUSDT | -11,1% | -34,6% | -1,15 | 155 | 34% | -0,2% | -0,30R | 0,70 | — | R$ 70 |
| M15_pullbackEMA21_stop1xATR1h_2R | SOLUSDT | -28,5% | -65,8% | -1,83 | 301 | 32% | -0,3% | -0,30R | 0,65 | — | R$ 36 |


## 2. Fora da amostra (2ª metade: 06/04/2025–06/10/2026), custos base

| Estratégia | Par | CAGR | Máx. DD | Sharpe | Trades | Acerto | Média/trade | Expect. (R) | PF | Tempo comprado |
|---|---|---|---|---|---|---|---|---|---|---|
| BH_comprar_segurar | BTCUSDT | +2,1% | -53,7% | 0,36 | 0 | — | — | — | — | 100% |
| D_SMA50_exec_21hBRT | BTCUSDT | +21,2% | -27,6% | 0,86 | 20 | 25% | +1,8% | — | 2,18 | 55% |
| D_SMA100_exec_21hBRT | BTCUSDT | +14,7% | -25,5% | 0,71 | 9 | 22% | +2,7% | — | 2,47 | 44% |
| D_SMA100_exec_10hBRT | BTCUSDT | +14,0% | -23,2% | 0,69 | 9 | 44% | +2,6% | — | 2,53 | 44% |
| D_SMA200_exec_21hBRT | BTCUSDT | +20,5% | -21,3% | 0,91 | 5 | 40% | +6,3% | — | 6,04 | 43% |
| D_TSMOM14_exec_21hBRT | BTCUSDT | +17,2% | -24,4% | 0,72 | 37 | 30% | +0,8% | — | 1,56 | 54% |
| D_TSMOM28_exec_21hBRT | BTCUSDT | +11,2% | -26,1% | 0,53 | 30 | 43% | +0,7% | — | 1,47 | 56% |
| D_TSMOM28_exec_10hBRT | BTCUSDT | +16,3% | -25,8% | 0,70 | 30 | 43% | +0,9% | — | 1,72 | 56% |
| D_TSMOM56_exec_21hBRT | BTCUSDT | +12,2% | -33,3% | 0,57 | 15 | 40% | +1,6% | — | 1,82 | 50% |
| D_SMA100_voltarget40 | BTCUSDT | +11,3% | -25,5% | 0,60 | 9 | 22% | +2,2% | — | 2,17 | 44% |
| H4_Donchian20_vol | BTCUSDT | +1,3% | -29,2% | 0,17 | 36 | 44% | +0,2% | — | 1,10 | 29% |
| H4_EMA50_filtroD_SMA100 | BTCUSDT | +4,4% | -19,9% | 0,31 | 55 | 33% | +0,2% | — | 1,19 | 30% |
| H1_reversao_BB_em_tendencia | BTCUSDT | -26,5% | -39,3% | -2,65 | 152 | 49% | -0,3% | -0,26R | 0,51 | — |
| M15_rompimento_stop1xATR1h_2R | BTCUSDT | -21,6% | -32,2% | -4,30 | 98 | 26% | -0,4% | -0,77R | 0,29 | — |
| M15_rompimento_stop1.5xATR15m_2R | BTCUSDT | -22,1% | -32,4% | -4,96 | 98 | 21% | -0,4% | -1,06R | 0,24 | — |
| M15_pullbackEMA21_stop1xATR1h_2R | BTCUSDT | -22,6% | -33,4% | -3,52 | 152 | 34% | -0,2% | -0,50R | 0,46 | — |
| BH_comprar_segurar | ETHUSDT | +31,2% | -69,2% | 0,86 | 0 | — | — | — | — | 100% |
| D_SMA50_exec_21hBRT | ETHUSDT | +95,4% | -32,1% | 1,64 | 9 | 44% | +14,4% | — | 6,77 | 55% |
| D_SMA100_exec_21hBRT | ETHUSDT | +55,4% | -40,3% | 1,23 | 9 | 22% | +10,3% | — | 4,84 | 45% |
| D_SMA100_exec_10hBRT | ETHUSDT | +55,6% | -36,6% | 1,24 | 9 | 22% | +9,9% | — | 5,70 | 45% |
| D_SMA200_exec_21hBRT | ETHUSDT | +22,6% | -40,0% | 0,73 | 7 | 29% | +5,2% | — | 3,58 | 33% |
| D_TSMOM14_exec_21hBRT | ETHUSDT | +41,2% | -46,8% | 0,94 | 38 | 42% | +2,1% | — | 1,80 | 54% |
| D_TSMOM28_exec_21hBRT | ETHUSDT | +40,9% | -41,6% | 0,99 | 24 | 33% | +2,9% | — | 2,25 | 55% |
| D_TSMOM28_exec_10hBRT | ETHUSDT | +40,7% | -41,8% | 0,98 | 24 | 42% | +2,9% | — | 2,22 | 55% |
| D_TSMOM56_exec_21hBRT | ETHUSDT | +80,0% | -24,2% | 1,56 | 11 | 55% | +10,0% | — | 6,67 | 51% |
| D_SMA100_voltarget40 | ETHUSDT | +28,5% | -27,0% | 1,13 | 9 | 22% | +5,2% | — | 3,68 | 45% |
| H4_Donchian20_vol | ETHUSDT | +37,5% | -37,3% | 0,98 | 43 | 35% | +1,5% | — | 1,69 | 35% |
| H4_EMA50_filtroD_SMA100 | ETHUSDT | +8,0% | -43,2% | 0,39 | 78 | 17% | +0,3% | — | 1,27 | 29% |
| H1_reversao_BB_em_tendencia | ETHUSDT | -36,2% | -55,2% | -2,49 | 154 | 49% | -0,4% | -0,24R | 0,56 | — |
| M15_rompimento_stop1xATR1h_2R | ETHUSDT | -14,3% | -27,0% | -1,74 | 87 | 33% | -0,3% | -0,40R | 0,60 | — |
| M15_rompimento_stop1.5xATR15m_2R | ETHUSDT | -15,4% | -24,5% | -2,21 | 87 | 32% | -0,3% | -0,48R | 0,53 | — |
| M15_pullbackEMA21_stop1xATR1h_2R | ETHUSDT | -38,4% | -51,9% | -4,46 | 147 | 24% | -0,5% | -0,56R | 0,35 | — |
| BH_comprar_segurar | SOLUSDT | -0,0% | -75,8% | 0,47 | 0 | — | — | — | — | 100% |
| D_SMA50_exec_21hBRT | SOLUSDT | +3,9% | -61,4% | 0,31 | 19 | 21% | +1,2% | — | 1,33 | 50% |
| D_SMA100_exec_21hBRT | SOLUSDT | +14,3% | -37,2% | 0,52 | 12 | 25% | +2,9% | — | 1,83 | 38% |
| D_SMA100_exec_10hBRT | SOLUSDT | +9,4% | -36,2% | 0,42 | 12 | 33% | +2,2% | — | 1,57 | 38% |
| D_SMA200_exec_21hBRT | SOLUSDT | +17,1% | -34,8% | 0,59 | 4 | 25% | +7,6% | — | 3,99 | 29% |
| D_TSMOM14_exec_21hBRT | SOLUSDT | +13,9% | -48,8% | 0,52 | 32 | 50% | +0,9% | — | 1,43 | 51% |
| D_TSMOM28_exec_21hBRT | SOLUSDT | -8,4% | -53,9% | 0,01 | 23 | 30% | -0,2% | — | 0,94 | 52% |
| D_TSMOM28_exec_10hBRT | SOLUSDT | -7,3% | -54,1% | 0,04 | 23 | 30% | -0,1% | — | 0,97 | 52% |
| D_TSMOM56_exec_21hBRT | SOLUSDT | +10,0% | -50,7% | 0,44 | 20 | 35% | +1,6% | — | 1,61 | 49% |
| D_SMA100_voltarget40 | SOLUSDT | +9,7% | -21,5% | 0,51 | 12 | 25% | +1,7% | — | 1,86 | 38% |
| H4_Donchian20_vol | SOLUSDT | +2,4% | -42,5% | 0,24 | 41 | 39% | +0,3% | — | 1,14 | 31% |
| H4_EMA50_filtroD_SMA100 | SOLUSDT | +10,0% | -30,3% | 0,45 | 59 | 24% | +0,4% | — | 1,31 | 25% |
| H1_reversao_BB_em_tendencia | SOLUSDT | -14,8% | -40,0% | -0,95 | 136 | 57% | -0,2% | -0,09R | 0,81 | — |
| M15_rompimento_stop1xATR1h_2R | SOLUSDT | -24,7% | -40,6% | -2,81 | 86 | 27% | -0,5% | -0,51R | 0,44 | — |
| M15_rompimento_stop1.5xATR15m_2R | SOLUSDT | -20,2% | -31,6% | -2,64 | 86 | 26% | -0,4% | -0,59R | 0,46 | — |
| M15_pullbackEMA21_stop1xATR1h_2R | SOLUSDT | -31,9% | -45,7% | -3,06 | 145 | 28% | -0,4% | -0,45R | 0,50 | — |


## 3. Sensibilidade a custos (CAGR do período total)

| Estratégia | Par | Sem custo | Base 0,15%/lado | Estresse 0,25%/lado |
|---|---|---|---|---|
| BH_comprar_segurar | BTCUSDT | +46,5% | +46,5% | +46,5% |
| BH_comprar_segurar | ETHUSDT | +19,0% | +19,0% | +19,0% |
| BH_comprar_segurar | SOLUSDT | +74,3% | +74,3% | +74,3% |
| D_SMA100_exec_10hBRT | BTCUSDT | +49,0% | +45,8% | +43,8% |
| D_SMA100_exec_10hBRT | ETHUSDT | +26,5% | +23,7% | +21,9% |
| D_SMA100_exec_10hBRT | SOLUSDT | +66,0% | +61,0% | +57,7% |
| D_SMA100_exec_21hBRT | BTCUSDT | +45,0% | +41,9% | +39,9% |
| D_SMA100_exec_21hBRT | ETHUSDT | +37,5% | +34,4% | +32,4% |
| D_SMA100_exec_21hBRT | SOLUSDT | +64,4% | +59,4% | +56,1% |
| D_SMA100_voltarget40 | BTCUSDT | +37,6% | +34,6% | +32,6% |
| D_SMA100_voltarget40 | ETHUSDT | +27,7% | +25,1% | +23,5% |
| D_SMA100_voltarget40 | SOLUSDT | +30,9% | +28,8% | +27,4% |
| D_SMA200_exec_21hBRT | BTCUSDT | +41,8% | +39,8% | +38,4% |
| D_SMA200_exec_21hBRT | ETHUSDT | +31,2% | +29,7% | +28,7% |
| D_SMA200_exec_21hBRT | SOLUSDT | +76,9% | +74,6% | +73,1% |
| D_SMA50_exec_21hBRT | BTCUSDT | +54,8% | +49,8% | +46,5% |
| D_SMA50_exec_21hBRT | ETHUSDT | +66,4% | +62,6% | +60,1% |
| D_SMA50_exec_21hBRT | SOLUSDT | +73,5% | +68,2% | +64,8% |
| D_TSMOM14_exec_21hBRT | BTCUSDT | +52,8% | +42,3% | +35,6% |
| D_TSMOM14_exec_21hBRT | ETHUSDT | +33,1% | +24,3% | +18,8% |
| D_TSMOM14_exec_21hBRT | SOLUSDT | +86,6% | +75,2% | +68,0% |
| D_TSMOM28_exec_10hBRT | BTCUSDT | +49,0% | +41,5% | +36,6% |
| D_TSMOM28_exec_10hBRT | ETHUSDT | +32,9% | +26,9% | +23,1% |
| D_TSMOM28_exec_10hBRT | SOLUSDT | +85,9% | +79,0% | +74,5% |
| D_TSMOM28_exec_21hBRT | BTCUSDT | +39,2% | +32,1% | +27,6% |
| D_TSMOM28_exec_21hBRT | ETHUSDT | +35,6% | +29,5% | +25,6% |
| D_TSMOM28_exec_21hBRT | SOLUSDT | +86,0% | +79,0% | +74,6% |
| D_TSMOM56_exec_21hBRT | BTCUSDT | +40,2% | +35,7% | +32,8% |
| D_TSMOM56_exec_21hBRT | ETHUSDT | +66,4% | +62,5% | +60,0% |
| D_TSMOM56_exec_21hBRT | SOLUSDT | +73,2% | +66,0% | +61,3% |
| H1_reversao_BB_em_tendencia | BTCUSDT | -0,6% | -29,5% | -45,6% |
| H1_reversao_BB_em_tendencia | ETHUSDT | +2,7% | -26,9% | -41,0% |
| H1_reversao_BB_em_tendencia | SOLUSDT | -1,5% | -25,3% | -39,8% |
| H4_Donchian20_vol | BTCUSDT | +19,6% | +11,1% | +5,8% |
| H4_Donchian20_vol | ETHUSDT | +29,7% | +20,5% | +14,7% |
| H4_Donchian20_vol | SOLUSDT | +58,0% | +46,4% | +39,2% |
| H4_EMA50_filtroD_SMA100 | BTCUSDT | +37,9% | +18,2% | +6,6% |
| H4_EMA50_filtroD_SMA100 | ETHUSDT | +23,2% | +5,0% | -5,6% |
| H4_EMA50_filtroD_SMA100 | SOLUSDT | +51,9% | +29,2% | +15,9% |
| M15_pullbackEMA21_stop1xATR1h_2R | BTCUSDT | +1,0% | -25,7% | -43,4% |
| M15_pullbackEMA21_stop1xATR1h_2R | ETHUSDT | -7,5% | -32,3% | -42,2% |
| M15_pullbackEMA21_stop1xATR1h_2R | SOLUSDT | -7,3% | -28,5% | -38,9% |
| M15_rompimento_stop1.5xATR15m_2R | BTCUSDT | -0,1% | -17,2% | -26,2% |
| M15_rompimento_stop1.5xATR15m_2R | ETHUSDT | +0,7% | -13,0% | -24,5% |
| M15_rompimento_stop1.5xATR15m_2R | SOLUSDT | +0,7% | -11,1% | -18,1% |
| M15_rompimento_stop1xATR1h_2R | BTCUSDT | +1,0% | -16,6% | -27,4% |
| M15_rompimento_stop1xATR1h_2R | ETHUSDT | +2,4% | -12,0% | -20,5% |
| M15_rompimento_stop1xATR1h_2R | SOLUSDT | -4,5% | -16,0% | -22,6% |


## 4. Carteira 1/3 em cada par (BTC/ETH/SOL), custos base

| Estratégia | Período | CAGR | Máx. DD | Sharpe | R$100 vira |
|---|---|---|---|---|---|
| BH_comprar_segurar | TOTAL | +49,7% | -68,3% | 0,93 | R$ 333 |
| BH_comprar_segurar | IS_1a_metade | +114,4% | -50,9% | 1,41 | — |
| BH_comprar_segurar | OOS_2a_metade | +11,5% | -66,0% | 0,60 | — |
| D_SMA100_exec_10hBRT | TOTAL | +44,9% | -49,6% | 1,05 | R$ 302 |
| D_SMA100_exec_10hBRT | IS_1a_metade | +78,3% | -48,7% | 1,34 | — |
| D_SMA100_exec_10hBRT | OOS_2a_metade | +27,2% | -29,5% | 0,89 | — |
| D_SMA100_exec_21hBRT | TOTAL | +45,8% | -51,2% | 1,07 | R$ 308 |
| D_SMA100_exec_21hBRT | IS_1a_metade | +73,7% | -51,2% | 1,30 | — |
| D_SMA100_exec_21hBRT | OOS_2a_metade | +28,9% | -30,2% | 0,92 | — |
| D_SMA100_voltarget40 | TOTAL | +29,5% | -22,4% | 1,28 | R$ 216 |
| D_SMA100_voltarget40 | IS_1a_metade | +45,6% | -22,4% | 1,71 | — |
| D_SMA100_voltarget40 | OOS_2a_metade | +16,7% | -22,2% | 0,85 | — |
| D_SMA200_exec_21hBRT | TOTAL | +50,3% | -47,0% | 1,08 | R$ 337 |
| D_SMA200_exec_21hBRT | IS_1a_metade | +89,8% | -47,0% | 1,37 | — |
| D_SMA200_exec_21hBRT | OOS_2a_metade | +20,1% | -30,4% | 0,74 | — |
| D_SMA50_exec_21hBRT | TOTAL | +60,4% | -44,2% | 1,27 | R$ 409 |
| D_SMA50_exec_21hBRT | IS_1a_metade | +101,1% | -44,2% | 1,60 | — |
| D_SMA50_exec_21hBRT | OOS_2a_metade | +42,9% | -32,7% | 1,15 | — |
| D_TSMOM14_exec_21hBRT | TOTAL | +50,0% | -38,2% | 1,16 | R$ 335 |
| D_TSMOM14_exec_21hBRT | IS_1a_metade | +89,1% | -34,4% | 1,55 | — |
| D_TSMOM14_exec_21hBRT | OOS_2a_metade | +24,4% | -36,4% | 0,78 | — |
| D_TSMOM28_exec_10hBRT | TOTAL | +52,1% | -49,1% | 1,14 | R$ 349 |
| D_TSMOM28_exec_10hBRT | IS_1a_metade | +121,0% | -37,8% | 1,73 | — |
| D_TSMOM28_exec_10hBRT | OOS_2a_metade | +17,4% | -33,3% | 0,65 | — |
| D_TSMOM28_exec_21hBRT | TOTAL | +50,3% | -41,6% | 1,11 | R$ 336 |
| D_TSMOM28_exec_21hBRT | IS_1a_metade | +119,9% | -40,5% | 1,73 | — |
| D_TSMOM28_exec_21hBRT | OOS_2a_metade | +15,5% | -34,7% | 0,59 | — |
| D_TSMOM56_exec_21hBRT | TOTAL | +55,9% | -55,9% | 1,20 | R$ 376 |
| D_TSMOM56_exec_21hBRT | IS_1a_metade | +89,8% | -55,9% | 1,46 | — |
| D_TSMOM56_exec_21hBRT | OOS_2a_metade | +36,0% | -28,9% | 1,05 | — |
| H1_reversao_BB_em_tendencia | TOTAL | -27,2% | -64,8% | -2,20 | R$ 38 |
| H1_reversao_BB_em_tendencia | IS_1a_metade | -27,5% | -43,7% | -1,96 | — |
| H1_reversao_BB_em_tendencia | OOS_2a_metade | -25,6% | -42,5% | -2,51 | — |
| H4_Donchian20_vol | TOTAL | +27,8% | -38,7% | 0,90 | R$ 207 |
| H4_Donchian20_vol | IS_1a_metade | +49,0% | -29,0% | 1,26 | — |
| H4_Donchian20_vol | OOS_2a_metade | +14,4% | -32,4% | 0,60 | — |
| H4_EMA50_filtroD_SMA100 | TOTAL | +18,1% | -44,5% | 0,66 | R$ 163 |
| H4_EMA50_filtroD_SMA100 | IS_1a_metade | +29,7% | -44,4% | 0,84 | — |
| H4_EMA50_filtroD_SMA100 | OOS_2a_metade | +7,5% | -29,0% | 0,41 | — |
| M15_pullbackEMA21_stop1xATR1h_2R | TOTAL | -28,7% | -64,0% | -3,73 | R$ 36 |
| M15_pullbackEMA21_stop1xATR1h_2R | IS_1a_metade | -26,3% | -37,6% | -2,86 | — |
| M15_pullbackEMA21_stop1xATR1h_2R | OOS_2a_metade | -30,8% | -42,7% | -5,21 | — |
| M15_rompimento_stop1.5xATR15m_2R | TOTAL | -13,7% | -36,4% | -2,85 | R$ 64 |
| M15_rompimento_stop1.5xATR15m_2R | IS_1a_metade | -7,8% | -12,2% | -1,47 | — |
| M15_rompimento_stop1.5xATR15m_2R | OOS_2a_metade | -19,2% | -28,0% | -4,52 | — |
| M15_rompimento_stop1xATR1h_2R | TOTAL | -14,8% | -40,3% | -2,64 | R$ 61 |
| M15_rompimento_stop1xATR1h_2R | IS_1a_metade | -9,0% | -16,0% | -1,46 | — |
| M15_rompimento_stop1xATR1h_2R | OOS_2a_metade | -20,2% | -30,9% | -4,00 | — |


## 5. Estratégia escolhida (execução 10h BRT, stop 3×ATR na corretora, grade de 1h)

`ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100` = o que uma conta de **R$100** faria de verdade: risco-alvo 1%, mas posição mínima de 6 USDT (mínimo da Bybit 5 USDT + folga) e teto de 3% de risco; o resto fica em USDT. `dias_bloqueados` = dias em que o sinal existia mas a regra de risco impediu a entrada (stop largo demais para o mínimo de ordem).

| Variante | Par | Período | CAGR | Máx. DD | Trades | Acerto | Expect. (R) | R$100 vira | Dias bloqueados |
|---|---|---|---|---|---|---|---|---|---|
| ESCOLHIDA_SMA100_stop3ATR_allin | BTCUSDT | TOTAL | +42,9% | -34,2% | 22 | 45% | +0,84R | R$ 290 | 0 |
| ESCOLHIDA_SMA100_stop3ATR_allin | BTCUSDT | IS_1a_metade | +86,5% | -34,2% | 13 | 46% | +1,26R | — | — |
| ESCOLHIDA_SMA100_stop3ATR_allin | BTCUSDT | OOS_2a_metade | +9,5% | -27,6% | 9 | 44% | +0,24R | — | — |
| var_stop2ATR_allin | BTCUSDT | TOTAL | +44,8% | -34,8% | 22 | 45% | +1,30R | R$ 301 | 0 |
| var_stop2ATR_allin | BTCUSDT | IS_1a_metade | +85,3% | -34,8% | 13 | 46% | +1,87R | — | — |
| var_stop2ATR_allin | BTCUSDT | OOS_2a_metade | +13,2% | -24,0% | 9 | 44% | +0,46R | — | — |
| var_sem_stop_allin | BTCUSDT | TOTAL | +45,8% | -34,2% | 22 | 45% | +0,88R | R$ 307 | 0 |
| var_sem_stop_allin | BTCUSDT | IS_1a_metade | +86,5% | -34,2% | 13 | 46% | +1,26R | — | — |
| var_sem_stop_allin | BTCUSDT | OOS_2a_metade | +14,0% | -23,2% | 9 | 44% | +0,34R | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | BTCUSDT | TOTAL | +14,2% | -13,7% | 19 | 42% | +0,99R | R$ 148 | 12 |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | BTCUSDT | IS_1a_metade | +27,2% | -13,7% | 10 | 40% | +1,66R | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | BTCUSDT | OOS_2a_metade | +2,4% | -6,8% | 9 | 44% | +0,24R | — | — |
| ESCOLHIDA_SMA100_stop3ATR_allin | ETHUSDT | TOTAL | +22,6% | -60,0% | 24 | 29% | +0,51R | R$ 183 | 0 |
| ESCOLHIDA_SMA100_stop3ATR_allin | ETHUSDT | IS_1a_metade | -3,3% | -56,9% | 15 | 33% | +0,26R | — | — |
| ESCOLHIDA_SMA100_stop3ATR_allin | ETHUSDT | OOS_2a_metade | +55,5% | -36,6% | 9 | 22% | +0,92R | — | — |
| var_stop2ATR_allin | ETHUSDT | TOTAL | +17,2% | -63,3% | 26 | 23% | +0,56R | R$ 160 | 0 |
| var_stop2ATR_allin | ETHUSDT | IS_1a_metade | -6,0% | -58,7% | 16 | 25% | +0,33R | — | — |
| var_stop2ATR_allin | ETHUSDT | OOS_2a_metade | +46,2% | -38,3% | 10 | 20% | +0,94R | — | — |
| var_sem_stop_allin | ETHUSDT | TOTAL | +23,7% | -59,0% | 23 | 26% | +0,54R | R$ 188 | 0 |
| var_sem_stop_allin | ETHUSDT | IS_1a_metade | -1,7% | -55,8% | 14 | 29% | +0,29R | — | — |
| var_sem_stop_allin | ETHUSDT | OOS_2a_metade | +55,5% | -36,6% | 9 | 22% | +0,92R | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | ETHUSDT | TOTAL | +6,5% | -21,8% | 8 | 25% | +1,11R | R$ 120 | 309 |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | ETHUSDT | IS_1a_metade | +8,2% | -17,6% | 3 | 33% | +1,81R | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | ETHUSDT | OOS_2a_metade | +4,7% | -5,0% | 5 | 20% | +0,68R | — | — |
| ESCOLHIDA_SMA100_stop3ATR_allin | SOLUSDT | TOTAL | +60,0% | -69,6% | 32 | 22% | +1,06R | R$ 406 | 0 |
| ESCOLHIDA_SMA100_stop3ATR_allin | SOLUSDT | IS_1a_metade | +135,9% | -57,3% | 20 | 15% | +1,48R | — | — |
| ESCOLHIDA_SMA100_stop3ATR_allin | SOLUSDT | OOS_2a_metade | +8,5% | -36,2% | 12 | 33% | +0,38R | — | — |
| var_stop2ATR_allin | SOLUSDT | TOTAL | +58,2% | -70,0% | 33 | 21% | +1,54R | R$ 393 | 0 |
| var_stop2ATR_allin | SOLUSDT | IS_1a_metade | +135,9% | -57,3% | 20 | 15% | +2,22R | — | — |
| var_stop2ATR_allin | SOLUSDT | OOS_2a_metade | +6,1% | -37,6% | 13 | 31% | +0,50R | — | — |
| var_sem_stop_allin | SOLUSDT | TOTAL | +60,5% | -69,3% | 32 | 22% | +1,07R | R$ 410 | 0 |
| var_sem_stop_allin | SOLUSDT | IS_1a_metade | +135,9% | -57,3% | 20 | 15% | +1,48R | — | — |
| var_sem_stop_allin | SOLUSDT | OOS_2a_metade | +9,3% | -36,2% | 12 | 33% | +0,38R | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | SOLUSDT | TOTAL | +5,1% | -4,5% | 1 | 100% | +6,70R | R$ 115 | 527 |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | SOLUSDT | IS_1a_metade | +0,0% | +0,0% | 0 | — | — | — | — |
| ESCOLHIDA_risco1pct_min6USDT_teto3pct_R$100 | SOLUSDT | OOS_2a_metade | +10,5% | -4,5% | 1 | 100% | +6,70R | — | — |


## 6. Walk-forward: escolher o N da SMA (20/50/100/150/200) a cada trimestre pelo Sharpe dos 12 meses anteriores

| Par | Método | Período | CAGR | Máx. DD | Sharpe | N escolhidos |
|---|---|---|---|---|---|---|
| BTCUSDT | walk_forward_N | TOTAL | +41,7% | -32,8% | 1,20 | [200, 50, 50, 50, 50, 150, 50, 50, 50, 100, 100, 200] |
| BTCUSDT | walk_forward_N | OOS_2a_metade | +16,1% | -24,5% | 0,77 | [200, 50, 50, 50, 50, 150, 50, 50, 50, 100, 100, 200] |
| BTCUSDT | fixo_N100 | TOTAL | +45,8% | -34,2% | 1,28 | nan |
| BTCUSDT | fixo_N100 | OOS_2a_metade | +14,0% | -23,2% | 0,69 | nan |
| ETHUSDT | walk_forward_N | TOTAL | +22,2% | -48,7% | 0,67 | [200, 150, 150, 150, 200, 150, 200, 50, 50, 50, 50, 150] |
| ETHUSDT | walk_forward_N | OOS_2a_metade | +25,1% | -35,8% | 0,79 | [200, 150, 150, 150, 200, 150, 200, 50, 50, 50, 50, 150] |
| ETHUSDT | fixo_N100 | TOTAL | +23,7% | -59,0% | 0,70 | nan |
| ETHUSDT | fixo_N100 | OOS_2a_metade | +55,6% | -36,6% | 1,24 | nan |
| SOLUSDT | walk_forward_N | TOTAL | +55,3% | -69,7% | 1,01 | [50, 50, 20, 20, 20, 20, 150, 50, 50, 50, 50, 100] |
| SOLUSDT | walk_forward_N | OOS_2a_metade | -7,9% | -59,8% | 0,03 | [50, 50, 20, 20, 20, 20, 150, 50, 50, 50, 50, 100] |
| SOLUSDT | fixo_N100 | TOTAL | +60,3% | -69,3% | 1,05 | nan |
| SOLUSDT | fixo_N100 | OOS_2a_metade | +9,4% | -36,2% | 0,42 | nan |


## 7. Monte Carlo (bootstrap de trades da estratégia escolhida; 20 mil caminhos; 1 posição por vez, ~7 trades/ano)

Supõe trades independentes; ignora regimes. Serve para intuição de dispersão, não como previsão.

```json
{
 "pool_BTC|risco_2.7pct_1ano": {
  "n_trades_simulados": 7,
  "mediana_final_R$": 106.28,
  "p5_final_R$": 93.34,
  "p95_final_R$": 166.58,
  "prob_terminar_abaixo_R$100": 0.384,
  "prob_tocar_R$90_(kill_switch)": 0.004,
  "prob_chegar_R$500": 0.0,
  "maxDD_mediano": -0.032,
  "maxDD_p5_pior": -0.072
 },
 "pool_BTC|risco_2.7pct_3anos": {
  "n_trades_simulados": 21,
  "mediana_final_R$": 137.25,
  "p5_final_R$": 90.79,
  "p95_final_R$": 260.12,
  "prob_terminar_abaixo_R$100": 0.134,
  "prob_tocar_R$90_(kill_switch)": 0.093,
  "prob_chegar_R$500": 0.002,
  "maxDD_mediano": -0.065,
  "maxDD_p5_pior": -0.133
 },
 "pool_BTC|risco_9pct_(~all-in_stop3ATR)_3anos": {
  "n_trades_simulados": 21,
  "mediana_final_R$": 224.37,
  "p5_final_R$": 71.75,
  "p95_final_R$": 1188.29,
  "prob_terminar_abaixo_R$100": 0.151,
  "prob_tocar_R$90_(kill_switch)": 0.476,
  "prob_chegar_R$500": 0.22,
  "maxDD_mediano": -0.207,
  "maxDD_p5_pior": -0.385
 },
 "pool_BTC|_amostra": {
  "n_trades_reais": 21,
  "acerto": 0.429,
  "expect_R": 0.741,
  "mediana_R": -0.156,
  "maior_ganho_R": 12.86,
  "pior_R": -1.04,
  "expect_R_sem_maior_trade": 0.135
 },
 "pool_3pares|risco_2.7pct_1ano": {
  "n_trades_simulados": 7,
  "mediana_final_R$": 99.47,
  "p5_final_R$": 93.15,
  "p95_final_R$": 180.32,
  "prob_terminar_abaixo_R$100": 0.519,
  "prob_tocar_R$90_(kill_switch)": 0.003,
  "prob_chegar_R$500": 0.0,
  "maxDD_mediano": -0.035,
  "maxDD_p5_pior": -0.072
 },
 "pool_3pares|risco_2.7pct_3anos": {
  "n_trades_simulados": 21,
  "mediana_final_R$": 120.01,
  "p5_final_R$": 87.46,
  "p95_final_R$": 278.84,
  "prob_terminar_abaixo_R$100": 0.258,
  "prob_tocar_R$90_(kill_switch)": 0.162,
  "prob_chegar_R$500": 0.006,
  "maxDD_mediano": -0.075,
  "maxDD_p5_pior": -0.144
 },
 "pool_3pares|risco_9pct_(~all-in_stop3ATR)_3anos": {
  "n_trades_simulados": 21,
  "mediana_final_R$": 156.85,
  "p5_final_R$": 62.33,
  "p95_final_R$": 1077.13,
  "prob_terminar_abaixo_R$100": 0.287,
  "prob_tocar_R$90_(kill_switch)": 0.606,
  "prob_chegar_R$500": 0.168,
  "maxDD_mediano": -0.234,
  "maxDD_p5_pior": -0.415
 },
 "pool_3pares|_amostra": {
  "n_trades_reais": 75,
  "acerto": 0.28,
  "expect_R": 0.666,
  "mediana_R": -0.169,
  "maior_ganho_R": 31.04,
  "pior_R": -1.04,
  "expect_R_sem_maior_trade": 0.255
 },
 "_trades_por_ano_1_posicao": 7.0
}
```
