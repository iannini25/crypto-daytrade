# crypto-daytrade

Mesa de **paper trading** de Bernardo Iannini. Bybit, só spot, conta simulada de R$100. Nenhuma ordem real sai deste repositório.

> Simulação e estudo. **Não é recomendação de investimento.** O backtest não promete o próximo mês. Não há meta de renda diária, link de afiliado nem chave de API aqui.

**English.** Paper-trading desk for Bernardo Iannini (Brazil). Bybit spot only since 24 Sep 2026 — no derivatives, no leverage, no short. Signals come from a daily SMA100 with a 3×ATR stop, entries only 10:00–12:30 BRT, one position, kill switch at 90% of starting equity, no new entries on CPI/FOMC/payroll/PCE days. Fees used: 0.10% + 0.10%. Real orders, later, would need a human yes and a trade-only key with withdrawal disabled. Do not commit API keys.

## Rodar um ciclo (paper)

```bash
python3 -m pip install -r requirements.txt
cd trading-system
python3 run_signal.py
```

O ciclo normal só entra ou sai por regime entre 10:00 e 12:30 BRT. O stop é checado em qualquer horário. Na primeira execução o script cria `paper/estado.json` (gitignored).

```bash
python3 run_signal.py --status
python3 run_signal.py --dry-run --ignorar-janela   # não grava
python3 run_signal.py --reset-kill-switch "motivo"  # só o humano
```

Testes, na raiz do repositório:

```bash
python3 -m pytest trading-system/tests
```

O mesmo comando roda no GitHub Actions (`.github/workflows/pytest.yml`).

## O que está onde

| Caminho | Função |
|---|---|
| `trading-system/` | Motor de paper: `run_signal.py`, estratégia, risco, livro, backtests e `RESULTADOS.md` |
| `trading-system/paper/estado.template.json` | Formato vazio. O estado ao vivo não entra no git |
| `trading-system/paper/exemplos/` | Ciclo de exemplo de 06/10/2026, congelado |
| `docs/` | Notas condensadas, fact-check e [como ligar Supabase e Vercel](docs/deploy.md) |
| `agents/` | Prompts em pt-BR para colar no Grok Bot: rastreador, caçador, notícias, baleias, risco e o chefe |
| `apps/web` | Painel Next.js (livro, posição, último sinal, limites). Sem segredo |
| `supabase/migrations/001_init.sql` | Tabelas da mesa, RLS ligado, sem policy aberta |

## Regras que o código já trava

- Spot long ou caixa em USDT. Pares: BTCUSDT, depois ETHUSDT, depois SOLUSDT.
- SMA100 do diário. Stop = entrada − 3×ATR14. No máximo uma posição.
- Taxa 0,10% + 0,10%. Kill switch em 90% do capital inicial. Perda diária −3%, semanal −5%.
- Sem entrada nova em dia de CPI, FOMC, payroll ou PCE.
- O Risco rejeita: a ideia morre. O chefe pergunta `SIM` ou `NÃO`. Os dois não enviam ordem.

Detalhe e números do teste de 3 anos: `trading-system/backtests/results/RESULTADOS.md` e `docs/trading-algoritmico.md`. Não edite o relatório para melhorar o passado.

## Segredos

Não commite `.env`, `paper/estado.json`, CSV de candle nem chave da Bybit. Quando existir ordem real, a chave é só SpotTrade, sem saque, com IP fixo, fora deste git. Passo a passo do painel: [docs/deploy.md](docs/deploy.md).

Painel local:

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```
