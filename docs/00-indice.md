# Índice da mesa (notas condensadas)

**Para:** Bernardo Iannini · **Compilado em:** 06/10/2026 · **Idioma:** pt-BR

> Simulação e estudo. **Não é recomendação de investimento.** Nada neste repositório garante lucro nem promete preservar os R$100. Preço, notícia e regra de exchange envelhecem. Imposto e autorização de exchange confirmam-se na fonte oficial e com contador.

A base longa (arquivos 01–13, dados brutos, transcrições) ficou de fora de propósito. O que entrou são as notas que mudam a operação:

| Nota | Para quê |
|---|---|
| [bybit-brasil.md](bybit-brasil.md) | Por que a conta brasileira é só spot, taxas, Pix, chave sem saque |
| [trading-algoritmico.md](trading-algoritmico.md) | O que o backtest próprio mostrou e qual regra ficou |
| [verificacao-videos.md](verificacao-videos.md) | O que os dois vídeos erraram, sem repetir o claim a claim |
| [deploy.md](deploy.md) | Ligar Supabase e Vercel sem commitar segredo |
| [../trading-system/ARQUITETURA.md](../trading-system/ARQUITETURA.md) | Fases, fluxo e critérios de go-live |
| [../trading-system/backtests/results/RESULTADOS.md](../trading-system/backtests/results/RESULTADOS.md) | Números gerados pelo código, não reescritos |

## O que a mesa trata como regra

1. Residente no Brasil na Bybit, desde **24/09/2026**: só spot, long ou caixa em USDT. Sem perpétuo, margem, opção, copy ou short.
2. Capital de teste simulado: **R$100**. Uma posição. Kill switch em **90%** do inicial.
3. Estratégia congelada: **SMA100 diária**, stop **3×ATR14**, entrada **10:00–12:30 BRT**. Taxa de trabalho **0,10% + 0,10%**.
4. Sem entrada nova em dia de **CPI, FOMC, payroll ou PCE**.
5. Regras de risco são código (`risco.py`). Agente que discorda não afrouxa o código.
6. Ordem real, se um dia existir, só com chave **SpotTrade, sem saque**, e com sim do Bernardo. Este repositório não tem essa chave e não envia ordem.

## O que os números de 06/10/2026 não autorizam

- Day trade de 15 minutos e reversão em 1h ficaram negativos depois da taxa, nos três pares e nas duas metades da amostra. Ver `RESULTADOS.md`.
- Na conta de R$100 com teto de 3%, o BTC da regra escolhida teria ido de R$100 a cerca de **R$148 em 3 anos** (CAGR +14,2%, pior queda −13,7%). Fora da amostra (abr/2025–out/2026) o CAGR foi **+2,4%**. Isso é backtest, não previsão.
- R$100 → R$500 pela rentabilidade do sistema não apareceu como caminho plausível. O Monte Carlo do BTC (risco ~2,7%, 3 anos) teve mediana de R$137 e cerca de 0,2% de chance de chegar a R$500.
