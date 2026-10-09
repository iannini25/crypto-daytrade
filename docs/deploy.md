# Ligar Supabase e Vercel

O painel em `apps/web` sobe sem banco. As páginas de livro, posição, sinal e snapshot mostram um aviso até existirem `SUPABASE_URL` e `SUPABASE_ANON_KEY`. A página de risco mostra os limites mesmo offline, porque eles estão no código.

Nada disto cria ordem na Bybit. Não coloque chave da corretora na Vercel.

## 1. Supabase

1. Crie um projeto em [supabase.com/dashboard](https://supabase.com/dashboard). Anote a URL (`https://<ref>.supabase.co`) e a chave **anon** (publishable / anon). A chave **service_role** fica só no painel da Supabase. Ela ignora RLS. Não vai para o git, para o browser nem para a Vercel deste painel.
2. No SQL Editor, rode o arquivo [`supabase/migrations/001_init.sql`](../supabase/migrations/001_init.sql) inteiro.
3. Confira: as cinco tabelas (`signals`, `paper_trades`, `equity_snapshots`, `agent_notes`, `macro_calendar`) têm RLS ligado e **nenhuma policy**. A chave anon, de propósito, não lê linha.
4. Quando quiser ver dados no painel, crie um usuário em Authentication (e-mail e senha). Não ligue login anônimo: esse usuário também usa o papel `authenticated`.
5. Só então descomente as policies no final da migração e rode de novo esses `create policy`. Elas exigem `auth.uid()` preenchido. Não use `user_metadata` para autorizar.
6. O app de hoje ainda não faz login. Com a policy ativa, a leitura com a chave anon continua negada — e a página deve dizer isso, em vez de inventar número. O login no painel é o passo seguinte, fora deste scaffold.

O calendário macro de out–nov/2026 já entra no insert. Atualize a tabela quando o agente de notícias trouxer a semana nova e você aprovar. A cópia que o robô Python lê continua em `trading-system/config.py` (`EVENTOS_BLOQUEIO`). Os dois não se sincronizam sozinhos.

## 2. Vercel

1. Importe o repositório GitHub `iannini25/crypto-daytrade` em [vercel.com/new](https://vercel.com/new).
2. **Root Directory:** `apps/web`. Framework: Next.js. Install `npm install`, build `npm run build`. Não mude isso para a raiz do monorepo: o `package.json` do Next está em `apps/web`.
3. Em Settings → Environment Variables, crie só:

   | Nome | Onde | Observação |
   |---|---|---|
   | `SUPABASE_URL` | Production e Preview, servidor | Sem prefixo `NEXT_PUBLIC_` |
   | `SUPABASE_ANON_KEY` | Production e Preview, servidor | A anon key ainda é um segredo de projeto. Não commitar |

4. Não crie `BYBIT_API_KEY`, `BYBIT_API_SECRET` nem `service_role` neste projeto. O painel não precisa deles.
5. Faça o deploy. Abra `/`, `/ledger`, `/posicao`, `/sinal` e `/risco`. Sem as variáveis, o miolo pede configuração. Com as variáveis e sem policy, a leitura aparece como recusada.

Arquivo local, se for rodar na sua máquina:

```bash
cd apps/web
cp .env.example .env.local
# edite .env.local — este arquivo está no .gitignore
npm install
npm run dev
```

`.env.local` não entra no git. Se um segredo foi commitado, rode-o (gere outro na Supabase) e apague do histórico antes de continuar.

## 3. O que fica de fora dos dois serviços

- Estado ao vivo do paper (`trading-system/paper/estado.json`, logs, CSVs). Está no `.gitignore`. O formato vazio é `estado.template.json`.
- Candles baixados por `backtests/fetch_klines.py` (`backtests/data/`).
- Qualquer chave com permissão de saque. Quando a fase real existir, a chave é **SpotTrade**, sem saque, com IP fixo, fora deste repositório. Ver [bybit-brasil.md](bybit-brasil.md).
