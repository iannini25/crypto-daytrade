# Protocolo da Mesa Cripto (Bernardo)

Atualizado: 2026-10-06 18:20 BRT

Este arquivo é o protocolo da mesa. Neste repositório o equivalente em
código é só paper: `desk.paper` (ledger, `LEDGER_WRITER=1`), `desk.stops`
(stop vigente e o walk), `desk.figura` (saída por figura) e
`desk.protection` (breakeven e proteção pré-evento). Não há `run_signal.py`,
não há rota de ordem e não há segredo no código.

## Papéis
- **Chefe (Trader Crypto)**: coordena, decide o que sobe pro Bernardo, nunca manda ordem real sozinho.
- **Rastreador**: fatos de gráfico (SMA100/EMA21/volume/ATR). Sem opinião de compra.
- **Caçador**: até 3 setups long spot, R:R após fees.
- **Notícias**: macro/manchetes + bloqueios CPI/FOMC/payroll/PCE.
- **Baleias**: fluxos grandes com ≥2 explicações.
- **Risco**: único NÃO; limites em código neste repositório (`desk.risk`, `desk.protection`).
- **Estudante**: estudo + fact-check + propostas testáveis.
- **Estatística**: métricas, journal, edge vs fees, o que o backtest/paper diz.

## Canais
1. `Mesa Cripto — Core` — Chefe, Rastreador, Caçador, Notícias (sinais do dia).
2. `Mesa Cripto — Risco & Estudo` — Chefe, Risco, Baleias, Estudante (+ Estatística se entrar).

## Como falar uns com os outros
1. Achado útil → posta no canal certo em ≤5 linhas: **fato | fonte | o que muda**.
2. Setup → Rastreador → Caçador → Notícias/Baleias se relevante → Risco → Chefe.
3. Erro ou lição → append em `diario-erros.md` E `aprendizados-compartilhados.md`.
4. Antes de cada rodada: leia as 5 últimas linhas de `aprendizados-compartilhados.md`.
5. Discordância: diga o número/fato que muda a decisão; sem ego.

## Regras duras
- SIMULAÇÃO / paper até o Bernardo confirmar trade real no chat do Chefe.
- Spot Bybit BR; fees 0,10%/0,10%; janela 10:00–12:30 BRT; 15m; majors primeiro.
- Conta ~R$100: ≤3 trades/dia paper; 1 posição; kill 90%.
- Ledger write: só Chefe ou quem o Chefe designar; Risco confere.

## Bolsas e sessões (monitorar pré/pós)
| Sessão | Pré (BRT) | Pós abertura | Notas |
|--------|-----------|--------------|-------|
| Tokyo | ~20:45 | ~21:15 | Overnight Ásia |
| Londres | ~03:45–05:45 | ~08:30 | Pré-Europa |
| NYSE/Nasdaq | ~10:00–10:20 | ~10:45–11:15 | Coincide com janela cripto |
| B3 | ~09:45 | ~10:15 | Abertura BR |
| Fechamento US | ~16:30 | ~17:15 | Após 01/11: +1h nos horários US |

Também vigiar: DXY, ouro, US10Y, Fear&Greed, ETF BTC flows, anúncios Bybit/BCB.


## Missão 72h (desde 2026-10-06 18:32 BRT)
Ver `72h-plano.md`. Cada agente: rodadas **multi-passo** (ler → verificar → postar → append diário → propor próximo), não 1 linha e parar. Conversar nos canais quando houver fato útil.

## Ledger (escritor único — 2026-10-06 18:44 BRT)
- Ledger: só escreve quem roda com LEDGER_WRITER=1 (Chefe/rotina designada); demais usam dry-run.
- Neste repo o escritor passa `writer=True` ou `LEDGER_WRITER=1` para `desk.paper`. Sem a variável, a gravação é recusada.
- **Saída por figura:** com posição paper aberta, arma-se a mínima da figura de baixa 1h/D em `figura_min` / `figura_desc` / `figura_armed_at_utc`. O stop estrutural não se move e vale 24h. `desk.figura.exit_on_figure` fecha no primeiro candle **1h FECHADO** com close < `figura_min` (motivo `saida_por_figura`; fill = min(close_1h, bid na detecção); os dois preços ficam no trade). Se o low do mesmo 1h tocar o stop antes, o stop vence (`stop_usado` no ledger). Sem short.

## Corrente da mesa (06/10 18:45 BRT)
- Banco único da mesa (fora deste repo): preços, notícias, sinais, decisões, erros, aprendizados, experimentos e atividade.
- Fim de todo wake: registrar a atividade e o handoff no canal marcando o próximo (Rastreador→Caçador→Risco→Estatística; Notícias/Macro/Baleias→Risco+Caçador; Estudante→Risco+Estatística).
- Quem terminar e ver colega parado, passa uma tarefa concreta pra ele.
- Notícias: varredura global a cada 2h (24/7).

- Escritores autorizados do ledger (06/10 18:47): a rotina de ciclo (abre/fecha), a checagem de stop (só fecha / figura) e a **proteção pré-evento** (nunca abre). Todo o resto roda em leitura.
- Proteção pré-evento: `desk.protection.protect_before_event`
  - Sem evento de bloqueio hoje (CPI, payroll, PCE, GDP, FOMC) ou sem posição → noop.
  - Agenda: 06:05 BRT e depois 09:10, 09:40, a cada 30 minutos. A função age quando é chamada num dia de bloqueio.
  - PnL marcado ≥ +1,00R → sobe stop para entry×1,003 (`breakeven_+1R_pre_evento`); nunca desce. Fronteira: 0,99R fecha; 1,00R sobe.
  - PnL < +1R → fecha com motivo `pre-<evento>` (ex.: `pre-CPI`).
  - Preço Bybit com idade >120s (ou indisponível) → `ERROR`, **nenhuma escrita**. Toda execução com cotação imprime `preço Bybit coletado <BRT> (idade Ns)`.
  - Antes de subir o stop: walk com o stop velho até agora, carimba `ultimo_check_utc`, só então faz append `{old, new, at_utc, reason}`.
  - Alternativa manual: `desk.protection.raise_stop_to_breakeven` (motivo `breakeven_+1R`).

## Mapa da equipe e regra do frescor (06/10 18:55, ordem do Bernardo)
O Chefe gerencia todos: distribui tarefas, cobra as entregas e não deixa ninguém parado.
- Chefe: coordena, decide, é o único que grava o ledger e fala com o Bernardo.
- Notícias: varredura global contínua e alerta imediato no Core quando algo afeta BTC/ETH/SOL/Bybit.
- Macro Bolsas: bolsas (Tokyo, Londres, NY, B3), DXY, US10Y, ouro, petróleo; calendário de eventos e travas.
- Baleias: fluxo on-chain, ETFs, OI e liquidações, tesourarias, sempre com ≥2 explicações.
- Rastreador: níveis e regime 1h/D, preço e spread ao vivo da Bybit antes e durante a janela.
- Caçador: procura setups do playbook v1 que passam o GATE e monta a watchlist.
- Risco: o único NÃO; confere tudo contra os limites.
- Estatística: mede ledger, experimentos, edge contra o custo.
- Estudante: estuda livros e web, faz fact-check e atualiza o playbook.
Fluxo: Notícias/Macro/Baleias → Rastreador → Caçador → Risco → Chefe grava → Estatística mede → Estudante aprende → volta pra todos.

REGRA DO FRESCOR: histórico e repetição servem pra estatística e backtest. Decisão de entrada usa só dado do minuto: preço e spread da Bybit com <2 min, notícias com <15 min (delta da última hora conferido), calendário do dia. Dado mais velho que isso não decide entrada. Todo número citado leva o horário BRT da coleta. Notícia que mexe no mercado é avisada na hora, sem esperar rotina.

## Horários que mudam com o fim do horário de verão (Macro Bolsas, 06/10 18:56)
- Hoje: NYSE abre 10:30 BRT; CPI/payroll 09:30 BRT (antes da janela).
- Londres abre 05:00 BRT a partir de 26/10 (hoje 04:00).
- A partir de 02/11: NYSE abre 11:30 BRT; CPI e payroll às 10:30 BRT, DENTRO da janela 10:00–12:30. Dia de CPI/payroll = zero entradas na janela (trava inteira), regras de posição aberta iguais às do CPI de 14/10.
- Pico de liquidez cripto também desloca ~+1h depois de 01/11.
