# Mesa memecoins — protocolo consultivo

A mesa de Bernardo passou a olhar só memecoins de Solana na pump.fun. Este diretório **não opera**. Ele lê APIs públicas e imprime JSON. O escritório em `code-town/` mostra os mesmos números. Ninguém daqui assina transação, guarda chave, seed ou segredo de API.

**English.** Advisory only. These scripts GET public DexScreener and RugCheck endpoints and print JSON. They do not sign, they do not store keys, and they do not send an order.

## O que a mesa faz

1. Um coletor lê preço, capitalização, liquidez, volume e variação. Outro lê o relatório público de risco.
2. O escritório mostra $DACITY, o top 10 e o que cada agente registrou em `agent_events`.
3. Uma pessoa lê o painel e decide fora deste repositório.
4. O banner **FAKE ALARM** é um aviso visual. Ele não dispara ordem. Fica escondido até alguém gravar um evento `fake_alarm` (ou abrir `?fakeAlarm=1`).

## O que a mesa não faz

- Não assina transação e não fala com RPC de carteira.
- Não pede, não lê e não grava chave privada, seed phrase, keypair ou API secret.
- Não envia `POST` para exchange, pump.fun ou qualquer serviço de ordem.
- Não tem variável de ambiente obrigatória. Se existir um `.env` em outro lugar, estes scripts ignoram.

## Comandos

Python 3, só biblioteca padrão. Rode a partir desta pasta:

```bash
cd memecoins
python3 dexscreener.py dacity
python3 dexscreener.py trending
python3 rugcheck.py nxPqZ4F7ux8Vph5NFu25rEP6Kx9Gr1U6Fmj36Rjpump
python3 collect.py
python3 test_public.py
```

`collect.py` junta a cotação de $DACITY (`nxPqZ4F7ux8Vph5NFu25rEP6Kx9Gr1U6Fmj36Rjpump`), o top 10 de mints Solana/pump.fun e o resumo RugCheck desse mint. `--mint` troca só o relatório RugCheck. `rugcheck.py --raw` imprime o JSON público inteiro; o padrão é o resumo (score, riscos, LP, holders), sem a lista de carteiras.

Fontes, todas sem chave:

| Dado | URL |
| --- | --- |
| Pares de $DACITY | `GET https://api.dexscreener.com/token-pairs/v1/solana/{mint}` |
| Ranking | `GET https://api.dexscreener.com/token-boosts/top/v1` e `.../latest/v1` |
| Cotação dos mints | `GET https://api.dexscreener.com/tokens/v1/solana/{mints}` |
| Risco | `GET https://api.rugcheck.xyz/v1/tokens/{mint}/report` |

O top 10 usa a ordem pública do DexScreener e fica só com `chainId=solana` e mint terminado em `pump`.

## Nomes no escritório

Eventos antigos em `agent_events` continuam válidos. O escritório traduz:

| Nome antigo | Nome na mesa |
| --- | --- |
| PumpFun | PumpFun Analista |
| Notícias | Monitor X |
| Rastreador | Monitor Trending |
| Caçador | Caçador Memecoins |
| Baleias | Holders e Carteira |
| Risco | Risco Memecoins |
| Estatística | Estatística Memecoins |
| Estudante | Estudante Memecoins |
| Macro Bolsas | Conferência de Dados |

O Chefe é **Trader Crypto - Chefe**.
