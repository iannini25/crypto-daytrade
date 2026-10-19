# ARQUITETURA — Sistema de agentes para operar spot na Bybit (Bernardo)

**Versão:** 06/10/2026 (BRT) · **Fase atual:** 1, PAPER TRADING (sem chave de API, sem ordem real)
**Base de estudo:** notas condensadas em [`docs/`](../docs/) (a base longa 00–15 de 06/10/2026 não está neste repositório; onde o texto cita `cripto-estudo/`, leia o resumo correspondente em `docs/`). **Backtests:** `backtests/results/RESULTADOS.md`

**Prompts da mesa (Grok Bot):** [`agents/`](../agents/). O código de risco continua mandando; os bots não enviam ordem.

> **Princípios:**
> 1. **Nenhuma garantia de lucro** e nenhuma garantia de "não perder os R$100". O sistema **limita** perdas; não as elimina.
> 2. As **regras de risco são código** (`risco.py`, `config.py`), não opinião de agente. Nenhum agente pode afrouxá-las; só o Bernardo edita `config.py`.
> 3. **Falha segura:** dado faltando, API com erro ou dúvida = **não operar**.
> 4. **Sem saque, nunca:** nenhuma chave terá permissão de saque ou de transferência.
> 5. **Humano no circuito:** na fase real, as primeiras ordens só saem com aprovação explícita do Bernardo.
>
> Legenda: 🟢 evidência · 🟡 evidência parcial · 🔵 opinião/boa prática · ✅ confirmado na doc oficial da Bybit · ⚠️ não confirmado.

---

## 1. Fases

| Fase | O que acontece | Dinheiro | Chave de API | Saída da fase |
|---|---|---|---|---|
| 0. Estudo | Base de conhecimento 00–15 e backtests | — | — | ✅ concluída |
| **1. Paper trading** (agora) | Agente de Sinais roda `run_signal.py` todo dia; o livro-razão registra; revisão semanal | Simulado (R$100) | **Nenhuma** (só dados públicos) | Critérios do §7 |
| 2. Real assistido | O mesmo sinal vira **proposta de ordem**; o Bernardo aprova cada uma; o executor envia limite + SL | R$100 real (convertido em USDT) | **Só spot-trade, sem saque, IP fixo** | ≥10 ordens reais sem erro + critérios do §7.2 |
| 3. Real semiautomático | Ordens dentro das regras saem sozinhas; o humano recebe aviso e pode vetar; o kill switch continua | R$100 + aportes | Idem | Revisão trimestral |

**Prazos pessoais que afetam o projeto** ([14](../cripto-estudo/14-bybit.md)):
- prova de vida e conta de pagamento para Pix entre **20/10 e 29/10/2026**;
- pedido de autorização (PSAV) da Bybit até **30/10** (protocolo ⚠️ não confirmado).

---

## 2. Os agentes (assistentes Grok Bot com rotinas agendadas)

| Agente | Quando roda (BRT) | O que faz | O que **não** pode fazer |
|---|---|---|---|
| **Pesquisador semanal** | Domingo 18:00 | (1) atualiza o calendário macro da semana (CPI, FOMC, payroll, PCE; fontes: BLS, Fed, BEA — [13](../cripto-estudo/13-noticias-e-movimentos.md)) e propõe a edição de `EVENTOS_BLOQUEIO` em `config.py`; (2) confere mudanças na Bybit: taxa VIP0, `minOrderAmt` via API, produtos para o Brasil, PSAV, Pix; (3) resume notícias que mudam o regime (hack, regulação) | Mudar regra de risco ou estratégia; operar |
| **Agente de Sinais** | **Todo dia 10:05** (janela 10:00–12:30). Checagens de stop a cada 4h: 14:05, 18:05, 22:05, 02:05 e 06:05 | Roda `python3 run_signal.py`, que faz um ciclo: marca a mercado, verifica stops, aplica regime e risco e registra. Envia ao Bernardo a mensagem do §5 (sinal, saída ou "SEM SINAL" com o motivo) | Ignorar uma checagem do Gestor de Risco; usar `--ignorar-janela` fora de teste; editar `config.py` |
| **Gestor de Risco** | Dentro de cada ciclo (código `risco.py`) + resumo diário | Regras duras do §6: tamanho, teto de risco, perda diária e semanal, kill switch, calendário, spread, custo em R. Bloqueia e explica por quê | Ser desligado por outro agente. Só o humano reativa o kill switch (`--reset-kill-switch "motivo"`) |
| **Registrador** | Dentro de cada ciclo (código `ledger.py`) | Grava `paper/estado.json`, `paper/trades.csv`, `paper/patrimonio.csv`, `paper/sinais.log` e `paper/ultimo_ciclo.json` | Apagar ou reescrever o histórico (só acrescenta) |
| **Revisor semanal** | Sábado 10:00 | Lê o livro-razão e calcula trades, acerto, expectativa em R após taxas, profit factor, pior queda e aderência (o sinal gerado bate com o recálculo independente do backtest no mesmo período?). Compara com o esperado do backtest e com buy-and-hold e CDI. Marca o status dos critérios de go-live (§7) | Declarar "aprovado para real" sozinho: ele só recomenda; quem decide é o Bernardo |

**Por que o Gestor de Risco e o Registrador são código e não "agentes que pensam":** são as peças que não podem errar nem ser persuadidas. 🔵 Os agentes LLM orquestram, explicam e revisam; as regras ficam em código testado (`tests/test_ciclo.py`).

---

## 3. Fluxo de dados

```
                      (domingo) Pesquisador ──► propõe calendário/ajustes ──► Bernardo aprova ──► config.py
                                                                                        │
API pública Bybit v5 (sem chave)                                                        ▼
  /v5/market/kline (D e 15m) ─┐                                                 regras de risco
  /v5/market/tickers ─────────┼──► run_signal.py ──► estrategia.py (SMA100, ATR) ──► risco.py ──┐
  /v5/market/instruments-info ┘        │                                                       │
                                       │◄──────────────── aprovado/bloqueado + motivos ◄────────┘
                                       ▼
                         ledger.py ──► paper/estado.json · trades.csv · patrimonio.csv · sinais.log · ultimo_ciclo.json
                                       │
                                       ├──► mensagem pt-BR ao Bernardo (Agente de Sinais)
                                       └──► (sábado) Revisor semanal ──► relatório + status do go-live
```

- **Fase 1 (agora):** só endpoints **públicos**, sem autenticação. Limite documentado: **600 requisições por 5 s por IP** ✅ ([rate limit](https://bybit-exchange.github.io/docs/v5/rate-limit)). Cada ciclo faz ~10 requisições.
- **Fase 2:** entra um módulo `executor.py` (ainda não existe), que só envia uma ordem com (a) sinal aprovado pelo `risco.py` **e** (b) aprovação humana registrada.

---

## 4. A estratégia (resumo; detalhes em [15 §9](../cripto-estudo/15-trading-algoritmico.md))

- **Tendência diária SMA100 + stop 3×ATR14**, spot long/flat, pares BTCUSDT > ETHUSDT > SOLUSDT (ordem de prioridade), **1 posição por vez** enquanto a conta for ~R$100.
- **Entrada:** o diário (fecha às 21:00 BRT) fechou acima da SMA100 → compra na janela de 10:00–12:30 BRT.
- **Saída:** o diário fechou abaixo da SMA100 → vende na janela seguinte; ou o stop (entrada − 3×ATR) é atingido a qualquer hora.
- **Por quê:**
  - foi a única família **positiva após taxas nos 3 pares e nas duas metades** do backtest;
  - tem 2 parâmetros, não otimizados;
  - custa ~0,04R por trade.
- **15m e reversão à média deram prejuízo após taxas** e ficaram de fora.
- **Expectativa realista:** ~7 trades por ano por par. Na maioria dos dias a resposta é "SEM SINAL" ou "posição aberta, regime segue de alta".

---

## 5. Formato exato das mensagens

### 5.1 Sinal de entrada

```
📈 SINAL (PAPER) — COMPRA {PAR} (spot, long)
Data/hora: {dd/mm/aaaa HH:MM} BRT | ID {P0001}
Estratégia: tendência diária SMA100 + stop 3×ATR14 (evidência 🟢 trend following; backtest próprio positivo após taxas)
Entrada: ordem LIMITE ~{ask} USDT (simulada a {ask×(1+slippage)} c/ slippage)
Stop: {preço} ({-x,x%}) → ordem SL na corretora, válida 24h
Alvo: SEM alvo fixo — sai quando o diário fechar abaixo da SMA100 (hoje {sma}). Referência 3R = {preço}
Tamanho: {n,nn} USDT ({qtd} BTC) = {xx,x%} do patrimônio
Risco até o stop (c/ taxas e slippage): {n,nnnn} USDT ≈ R$ {n,nn} ({x,x%} do capital)
R:R de referência após taxas: {x,xx} | custo ida+volta 0,30% = {0,0xx}R
Motivo: fechamento diário {x} > SMA100 {y} (+z%); ATR14 diário {a}
Obs.: {ex.: tamanho ideal para 1% seria 2,49 USDT, abaixo do mínimo prático de 6 USDT → usando o mínimo}
Checklist: [✓] dado diário fresco [✓] instrumento negociando [✓] janela 10:00–12:30 BRT [✓] sem CPI/FOMC/payroll hoje
           [✓] kill switch inativo [✓] perdas dia/semana no limite [✓] sem stop neste par hoje [✓] vaga de posição
           [✓] spread ≤ 0,10% [✓] mínimo de ordem 5 USDT e risco ≤ 3% [✓] custo ≤ 0,10R [✓] R:R de referência após taxas ≥ 2,0
⚠️ PAPER TRADING — nenhuma ordem real foi enviada.
```

### 5.2 Saída

```
🔻 SAÍDA (PAPER) — VENDER {PAR} (spot)          (🛑 se for stop ou kill switch)
Quando: {data hora} BRT | Motivo: {regime virou: fechamento diário X < SMA100 Y | stop atingido em Z}
Entrada: {a} → Saída: {b} (com slippage) | Qtd: {q}
Resultado líquido: {±n} USDT ≈ R$ {±n,nn} ({±x,xx}R) | taxas pagas {n} USDT
```

### 5.3 Sem sinal (sempre com o motivo, por par)

```
SEM SINAL.
Por par:
  • BTCUSDT [preço …]: regime de ALTA, mas entrada BLOQUEADA: {regra} ({detalhe})
  • ETHUSDT [preço …]: regime de BAIXA: fechamento diário … abaixo da SMA100 … → ficar em USDT
  • SOLUSDT [preço …]: … mínimo de ordem 5 USDT e risco ≤ 3% (posição mínima de 6,00 USDT com stop a 11,7% arriscaria 3,7% do capital)
Conta simulada: patrimônio … USDT ≈ R$ … | caixa … | posições … | kill switch inativo (gatilho … USDT)
```

### 5.4 Fase 2: pedido de aprovação (a implementar)

```
🟡 PEDIDO DE APROVAÇÃO — ordem REAL proposta {ID}
{mesmo conteúdo do 5.1, com preço limite, quantidade arredondada à precisão do par e o SL que será anexado}
Para aprovar, responda exatamente: APROVO {ID}   ·   Para recusar: NÃO {ID}
Validade: até 12:30 BRT de hoje; depois disso a proposta expira sozinha.
```

---

## 6. Regras de risco (Gestor de Risco, `config.py` + `risco.py`)

| # | Regra | Valor | Observação |
|---|---|---|---|
| 1 | Risco por trade (alvo) | **1%** do patrimônio | [10 §4](../cripto-estudo/10-operar-com-inteligencia.md) |
| 2 | Teto absoluto de risco por trade | **3%** | Exceção da conta pequena: o mínimo de 5 USDT + 20% de folga força ~2,4% no BTC. **SOL fica bloqueado** (3,7%) |
| 3 | Posição mínima | 6 USDT (`minOrderAmt` 5 USDT ✅ relido da API a cada ciclo + 20%) | Evita a posição "presa" abaixo de 5 USDT depois de cair até o stop (⚠️ inferência) |
| 4 | Máximo de posições | 1 | Até a conta permitir 2 posições mínimas com risco ≤ 3% |
| 5 | Perda diária | −3% → sem entradas até o dia seguinte | |
| 6 | Perda semanal | −5% → sem entradas até segunda | |
| 7 | **Kill switch** | Patrimônio ≤ **90% do capital inicial** (≈ R$90) → zera, bloqueia e **só o humano reativa** | Medido em USDT para não disparar por variação do dólar. Na fase real: cancelar ordens + vender + avisar + revogar a chave se houver suspeita de bug |
| 8 | Calendário macro | Sem entradas em dia de CPI, FOMC, payroll ou PCE | Depois de **01/11** (fim do horário de verão nos EUA), CPI e payroll saem às **10:30 BRT, dentro da janela** |
| 9 | Custo máximo | Ida e volta (0,30%) ≤ **0,10R** | Hoje, BTC: 0,04R |
| 10 | R:R mínimo após taxas | Referência 3R deve dar ≥ **2,0** líquido | Hoje: 2,87 |
| 11 | Spread | ≤ 0,10% | |
| 12 | Dado fresco | Último diário fechado há ≤ 26 h; se a API falhar → sem sinal | Falha segura |
| 13 | Esfriamento | Sem reentrada no mesmo par no dia de um stop | |
| 14 | Janela | Entradas e saídas por regime só entre 10:00 e 12:30 BRT; o stop vale 24h | Pico de liquidez às 11h BRT ([09](../cripto-estudo/09-gaps-e-volume.md)) |

---

## 7. Critérios de go-live

> **Verdade incômoda (🟢 aritmética):** esta estratégia faz ~7 trades por ano por par. Em 3–4 semanas de paper, o normal é ver **0 a 2 trades**. O critério de "≥30 trades" levaria **anos**. Nenhuma estratégia que gera 30 trades em semanas foi positiva após taxas nos nossos testes. Por isso, separo os critérios em **operacionais** (para começar com R$100) e **estatísticos** (para aumentar o tamanho).

### 7.1 Para passar à Fase 2 (R$100 real, com aprovação humana de cada ordem)

1. ✅ Backtest com regras congeladas, positivo após custos fora da amostra (2ª metade) nos 3 pares — **cumprido** (`RESULTADOS.md` §2 e §5).
2. ≥ **4 semanas** de paper com o ciclo das 10:05 rodando **todos os dias**, sem falha não explicada. No máximo 1 ciclo perdido por semana; cada erro de API deve ter terminado em "sem sinal".
3. **Aderência:** o Revisor recalcula com o código do backtest (`run_escolhida.py`) os sinais do mesmo período, e 100% dos sinais e saídas do paper batem (mesmo dia, mesmo lado).
4. Stops e saídas simulados conferidos à mão pelo Bernardo em pelo menos 1 caso, ou no teste offline `tests/test_ciclo.py`, se não houver trade real no período.
5. Infraestrutura do §8 pronta: subconta ou conta só com o capital de teste, chave **sem saque**, IP fixo e teste do `executor.py` na **testnet** (`api-testnet.bybit.com`) com 5 ordens limite + SL sem erro.
6. Pix com prova de vida feito (até 29/10) e o Bernardo de acordo, por escrito, com: risco ~2,4% por trade e kill switch em R$90.

### 7.2 Para aumentar o tamanho ou ligar a Fase 3

1. ≥ **30 trades** (paper + real, BTC/ETH somados).
2. **Expectativa após taxas > 0** e profit factor > 1,2 nos trades reais.
3. Pior queda real ≤ **10%** do capital (o kill switch não disparou).
4. Diferença de execução (preço real − preço do sinal) média ≤ 0,10%.
5. Os 10 primeiros trades reais, todos aprovados manualmente, sem erro de quantidade, de par ou de SL.

---

## 8. Fase real (2 e 3): chave, ordens e endpoints

### 8.1 Chave de API

| Item | Configuração | Fonte |
|---|---|---|
| Onde criar | **Só na web**: `https://www.bybit.com/app/user/api-management` (bloqueado nas primeiras 48h da conta; exige 2FA) | ✅ [14 §11](../cripto-estudo/14-bybit.md) |
| Permissões | **Spot → SpotTrade** (leitura + escrita). **Desmarcar** tudo o mais: Withdraw/saque, Wallet (AccountTransfer/SubMemberTransfer), Derivatives, Earn, P2P, Convert | ✅ [Modify API key: lista de permissões](https://bybit-exchange.github.io/docs/v5/user/modify-master-apikey) |
| Chave extra só leitura | `readOnly = 1` para o Revisor conciliar saldo e ordens | ✅ |
| IP whitelist | Vincular ao IP fixo do servidor que roda o executor. Chave sem IP **expira em 90 dias** e fica inválida 7 dias depois de troca de senha | ✅ [14 §11](../cripto-estudo/14-bybit.md) |
| Isolamento | Ideal: **subconta** só com o capital de teste (⚠️ disponibilidade de subconta na conta brasileira migrada não confirmada). Alternativa: deixar na exchange só o capital de trading | 🔵 |
| Onde guardar | Arquivo `~/.config/bybit/credentials.env` com `chmod 600`, **fora** de `/workspace/trading-system` (o livro-razão nunca contém a chave), lido por variável de ambiente só pelo `executor.py`. **Nunca** colar a chave no chat. ⚠️ A "box" é compartilhada por todos os agentes do Bernardo: qualquer agente com shell consegue ler o arquivo. Por isso, **chave sem saque + IP fixo + saldo pequeno** são obrigatórios. Melhor ainda: rodar o executor na máquina do Bernardo ou num servidor com IP fixo dedicado | 🔵 |
| Revogação | Em suspeita de vazamento ou bug: apagar a chave na web na hora. O kill switch real deve lembrar disso | 🔵 |

### 8.2 Tipos de ordem (spot)

- **Entrada:** `POST /v5/order/create` com `category=spot`, `side=Buy`, `orderType=Limit`, `price` ≈ melhor ask (ou 1 tick abaixo com `timeInForce=PostOnly`), `qty` na precisão `basePrecision` e **`stopLoss`** anexado (`slOrderType=Market`) ✅ ([Place Order](https://bybit-exchange.github.io/docs/v5/order/create-order): "Spot Limit order supports take profit, stop loss…").
  - Sem `takeProfit`, porque a estratégia não tem alvo fixo.
  - No VIP0 spot, maker e taker pagam 0,10% ✅ ([14 §5](../cripto-estudo/14-bybit.md)). O PostOnly só evita pagar o spread.
- **TP/SL pré-configurado não pode ser editado depois da execução** ✅ ([14 §7](../cripto-estudo/14-bybit.md)). Para mudar o stop: cancelar e criar um TP/SL avulso (`orderFilter=tpslOrder`, com `triggerPrice`). No `tpslOrder` spot, os ativos ficam reservados ✅.
- **OCO:** existe na interface spot ✅ ([14 §7](../cripto-estudo/14-bybit.md)) e aparece como filtro `OcoOrder` nas consultas e cancelamentos da API ✅. ⚠️ Porém, a página de criação de ordem **não lista** `OcoOrder` como valor de `orderFilter` na criação. Use o TP/SL anexado à limite, que já funciona como "um cancela o outro".
- **Ordem a mercado:** a Bybit converte em IOC limitada por proteção de slippage; há `slippageToleranceType`/`slippageTolerance` ✅. Usar só na saída por regime ou no kill switch.
- **Saída por regime:** `Sell` Limit no bid (ou Market com tolerância) **depois de cancelar o SL** pendente (`/v5/order/cancel` ou `cancel-all` com `orderFilter=tpslOrder`) ✅.

### 8.3 Endpoints necessários (todos v5) e limites

| Uso | Endpoint | Auth | Limite documentado | Fonte |
|---|---|---|---|---|
| Candles (D, 15m) | `GET /v5/market/kline` (`category=spot`, até 1000 por chamada) | Não | IP: 600 req / 5 s | ✅ [kline](https://bybit-exchange.github.io/docs/v5/market/kline), [rate limit](https://bybit-exchange.github.io/docs/v5/rate-limit) |
| Preço, bid e ask | `GET /v5/market/tickers` | Não | idem | ✅ |
| Mínimo de ordem, precisão e tick | `GET /v5/market/instruments-info` (`minOrderAmt`, `basePrecision`, `tickSize`) | Não | idem | ✅ [instrument](https://bybit-exchange.github.io/docs/v5/market/instrument) |
| Hora do servidor | `GET /v5/market/time` | Não | idem | ✅ (usado no estudo) |
| Enviar ordem (limite + SL) | `POST /v5/order/create` | Sim | **20/s** (spot) | ✅ |
| Cancelar | `POST /v5/order/cancel` · `POST /v5/order/cancel-all` | Sim | 20/s (spot) | ✅ |
| Ordens abertas | `GET /v5/order/realtime` | Sim | 50/s | ✅ |
| Histórico e execuções | `GET /v5/order/history` · `GET /v5/execution/list` | Sim | 50/s | ✅ |
| Saldo | `GET /v5/account/wallet-balance` (`accountType=UNIFIED`) | Sim | 50/s | ✅ [wallet](https://bybit-exchange.github.io/docs/v5/account/wallet-balance). ⚠️ A conta brasileira virou "Standard Account": confirmar se responde com `UNIFIED` ou se é preciso usar `/v5/asset/transfer/query-account-coins-balance` (5/s) |
| Taxa real da conta | `GET /v5/account/fee-rate` | Sim | 5/s | ✅ (conferir se a entidade BR cobra 0,10%) |

- **Autenticação:** HMAC com cabeçalhos `X-BAPI-API-KEY`, `X-BAPI-TIMESTAMP`, `X-BAPI-SIGN` e `X-BAPI-RECV-WINDOW` (5000 ms) ✅ ([14 §11](../cripto-estudo/14-bybit.md)).
- **Domínio:** `api.bybit.com`. A doc diz "Brazil users: … use api.bybit.com" ✅; ⚠️ não está confirmado se a conta migrada usa outro.
- **Bloqueio por excesso:** quem estoura o limite por IP recebe 403 e precisa esperar ≥ 10 min ✅.
- **Teste:** testnet `api-testnet.bybit.com` ✅.

---

## 9. Agendamento das rotinas (BRT)

| Rotina | Horário | Comando |
|---|---|---|
| Ciclo principal | Todo dia **10:05** | `cd /workspace/trading-system && python3 run_signal.py` |
| Repescagem (se o das 10:05 falhou) | 11:30 | idem (o ciclo é idempotente: não duplica posição) |
| Checagem de stop | 14:05, 18:05, 22:05, 02:05 e 06:05 | idem (fora da janela, só marca a mercado e verifica os stops) |
| Revisor | Sábado 10:00 | Lê `paper/*.csv`, recalcula métricas e roda `backtests/run_escolhida.py` para checar a aderência |
| Pesquisador | Domingo 18:00 | Atualiza o calendário e checa mudanças na Bybit |

- 🔵 **Depois de 01/11** (fim do horário de verão nos EUA), o pico de liquidez passa para ~12h BRT. Avaliar mover a janela para 11:00–13:30. A estratégia diária é pouco sensível ao horário: no backtest, executar às 21h ou às 10h deu resultado parecido no BTC.

---

## 10. Lacunas e riscos conhecidos

- **Estatística fraca:** 21 trades fechados no BTC em 3 anos. Sem o melhor trade, a expectativa cai de +0,74R para +0,14R.
- **Retorno da conta de R$100 é pequeno:** ~14% ao ano no backtest de 3 anos e +3,7% em 18 meses na 2ª metade, abaixo do CDI. **R$500 só com aportes.**
- ⚠️ Não confirmado na conta brasileira:
  - venda de saldo < 5 USDT;
  - desconto da taxa na compra;
  - funcionamento da API de trade e do `wallet-balance` na Standard Account;
  - disponibilidade de subconta;
  - taxa real (consultar `fee-rate`).
- O `executor.py` (Fase 2) **não foi escrito**, de propósito. Nenhuma chave existe.
- O calendário macro em `config.py` é manual e precisa de atualização semanal.
- A box é compartilhada entre agentes. Ver §8.1 sobre onde guardar a chave.
