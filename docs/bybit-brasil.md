# Bybit para quem mora no Brasil

**Pesquisa de:** 06/10/2026 (BRT). Condensado de um levantamento mais longo. Onde a fonte oficial não fechou o ponto, está marcado ⚠️.

> Estudo operacional. **Não é recomendação de investimento** e não é passo a passo para abrir alavancagem.

## O corte que define a mesa

A Bybit anunciou a migração dos usuários no Brasil e o corte de produtos não permitidos localmente ([anúncio de 20/07/2026](https://announcements.bybit.com/en/article/important-update-for-bybit-users-in-brazil--art1501e51cfacf/)).

| Data | Efeito |
|---|---|
| 21/09/2026 | Posições abertas liquidadas a mercado; fiat não suportado virou USDT |
| **24/09/2026** | Conta migrada para a entidade local. Conta principal vira Standard. Fiat: BRL |
| 20/10/2026 | Pix/BRL passa a exigir prova de vida e conta de pagamento |
| 29/10/2026 | Quem não concluiu isso tem o BRL convertido em USDT |

Para residente no Brasil a operação desta mesa é **spot: comprar e vender o que tem**. Sem alavancagem e sem short. Em regime de baixa a posição é USDT. Perpétuos, margem, opções e copy ficaram de fora. A lista exata do que ainda existe no app (alguns bots, parte do Earn) ⚠️ não estava numa página oficial conferida em 06/10/2026 — olhar no app antes de usar.

Pedido de autorização (PSAV) ao Banco Central: a corretora declarou intenção. ⚠️ Protocolo confirmado em página do BC não constava deste levantamento em 06/10/2026. Prazo citado para quem já opera: **30/10/2026**.

## Onde operar e quanto custa

Pares de trabalho: **BTCUSDT, ETHUSDT, SOLUSDT**. BTCBRL apareceu com spread de cerca de 1% na API pública de 06/10/2026; a rota prática anotada foi Pix → BRL → USDTBRL → USDT → par em USDT.

| Item | Valor usado pela mesa | Fonte no estudo |
|---|---|---|
| Taxa spot VIP0 | **0,10% maker e 0,10% taker** | Tabela de fees da Bybit, conferida no estudo |
| Ida e volta só de taxa | 0,20% | Soma dos dois lados |
| Slippage no backtest | 0,05% por lado (estresse 0,15%) | Premissa do código, não taxa da corretora |
| Mínimo de ordem spot | **5 USDT** (`minOrderAmt`) | API `instruments-info` em 06/10/2026 |
| Posição mínima prática | 6 USDT (mínimo + 20% de folga) | Para ainda conseguir vender depois de uma queda |
| Câmbio BRL→USDT no modelo | 0,44% (spread ~0,24% + taxa do par) | USDTBRL na mesma coleta |

Confira "My Fee Rate" no app. A entidade local pode divergir do cardápio global. ⚠️

## Chave de API — só numa fase futura, e nunca neste git

A fase atual **não usa chave**. Dados vêm da API pública v5.

Se um dia houver ordem real:

- Criar a chave na web, com 2FA. Permissão **Spot → SpotTrade** apenas.
- **Desmarcar saque, transferência, derivativos, Earn, P2P e Convert.**
- Vincular a um IP fixo. Chave sem IP expira.
- Guardar fora do repositório (`chmod 600`), nunca no chat, nunca na Vercel do painel, nunca num commit.
- Saldo na exchange = só o capital de teste.
- Em suspeita de vazamento, apagar a chave na hora.

O painel em `apps/web` lê no máximo a chave anônima do Supabase, no servidor. Ela não fala com a Bybit.
