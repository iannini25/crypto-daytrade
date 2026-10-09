# trading-system — paper trading spot Bybit (Bernardo)

**Fase atual: PAPER TRADING.** Não há chave de API e nenhuma ordem real é enviada. Usa só a API pública v5 da Bybit.

## Rodar um ciclo
Na raiz do repositório:

```bash
python3 -m pip install -r requirements.txt
cd trading-system
python3 run_signal.py                         # ciclo normal (entradas/saídas só 10:00–12:30 BRT; stop checado sempre)
python3 run_signal.py --status                # só a conta simulada
python3 run_signal.py --dry-run --ignorar-janela   # TESTE: mostra o que faria agora, sem gravar
python3 run_signal.py --reset-kill-switch "revisei X"   # só o humano
python3 tests/test_ciclo.py                   # teste offline: stop, saída por regime, kill switch
```

O estado ao vivo (`paper/estado.json`, logs e CSVs) fica de fora do git. O formato vazio está em `paper/estado.template.json`. Um ciclo de exemplo de 06/10/2026 está em `paper/exemplos/` — é registro de simulação, não resultado novo.

## Arquivos
- `ARQUITETURA.md`: agentes, fluxo, regras de risco, go-live, fase real (API, chaves, endpoints).
- `config.py`: parâmetros e regras de risco (só o humano edita).
- `estrategia.py`: SMA100 diária + stop 3×ATR14 (compartilhado com o backtest).
- `risco.py`: Gestor de Risco (dimensionamento, teto de risco, limites, kill switch).
- `ledger.py`: Registrador (`paper/estado.json`, `trades.csv`, `patrimonio.csv`, `sinais.log`, `ultimo_ciclo.json`).
- `bybit_public.py`: cliente da API pública (kline, tickers, instruments-info).
- `backtests/`: `fetch_klines.py` (baixa os dados), `run_backtests.py` (todas as estratégias), `run_escolhida.py` (escolhida + R$100 + walk-forward + Monte Carlo), `make_report.py` → `results/RESULTADOS.md`.

## Refazer os backtests
Os CSVs de candle ficam em `backtests/data/` e **não entram no git** (são grandes). As métricas já calculadas estão em `backtests/results/`.
```bash
cd backtests
python3 fetch_klines.py 3 15 && python3 fetch_klines.py 5 60
python3 run_backtests.py && python3 run_escolhida.py && python3 make_report.py
```
