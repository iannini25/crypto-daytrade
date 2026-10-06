# 20 — PLAYBOOK DE PADRÕES v1 (mesa cripto do Bernardo)

| Campo | Valor |
|---|---|
| **Versão** | **v1** |
| **Data** | 2026-10-06 ~18:45 BRT (GATE: decisão do Chefe 18:42 BRT — manter regra de custo e ancorar stop na estrutura 1h/D; 15m só entrada) |
| **Autor** | Estudante (pesquisa) · aprovação: Chefe · gate: Risco · medição: Estatística |
| **Modo** | **PAPER ONLY**: nunca ordem real, nunca API key. "ATIVO" = elegível para **paper**, não para dinheiro real. |
| **Fontes cruzadas** | Clear Cap.11 + Cap.12 ([livros/clear-estudo-cap11.md](livros/clear-estudo-cap11.md)) · Strike 55 ([16](16-padroes-strike.md)) · Web/Bulkowski ([18](18-padroes-web.md)) · evidência + medidas 15m ([12](12-padroes-graficos.md)) · Deriv 10 padrões ([19](19-deriv-10padroes.md), aprovado pelo Chefe 18:42) · Clear caps 06–10 · [mesa/00-protocolo.md](mesa/00-protocolo.md) |
| **Fora desta versão** | Candlesticks (Clear Cap.13+), harmônicos, Elliott, Wolfe, megafone/diamante, fundo/topo arredondado como setup |

> **Caveat Bulkowski (vale para toda a tabela):** números de [thepatternsite.com](https://thepatternsite.com/) = **ações dos EUA, gráfico diário, "trades perfeitos", sem custos**. "Falha" = anda <5% após o rompimento. Servem **só como ranking relativo** entre padrões, nunca como expectativa no BTC 15m. Os % de "sucesso" do Strike são didáticos e não são usados. Clear e Deriv **não trazem nenhuma estatística**.

---

## 1. Regras globais da mesa (curtas)

1. **Bybit spot BR, long-only.** Sem short, sem margem, sem alavancagem. Padrão de baixa = **só saída / não comprar**.
2. **Custo:** fees 0,20% RT; **all-in com slip = 0,30% RT** (usado em todas as contas).
3. **Conta ~R$100 (~19,9 USDT) · ordem mínima 6 USDT · 1 posição · ≤3 trades/dia · depois de 1 loss no dia, sem nova entrada** (um stop já quase esgota o −3%/dia).
4. **Janela de entrada paper 10:00–12:30 BRT.**
5. **Diário = filtro, não âncora de stop:** HH/HL obrigatório para long; SMA100 competitiva como regime; **conflito D × 15m = flat**; **quebra de LTA no D = flat**.
6. **15m = gatilho só no candle FECHADO.** 1m/5m proibidos. O 15m não redesenha a tese do D.
7. **S/R e flip só com close.** Volume relativo do par Bybit (mesmo horário) ajuda. S/R isolado ≠ setup.
8. **Stop candidato = estrutura do padrão no 1h ou no diário** (ombro, 2º fundo, HL do triângulo, base da bandeira/alça — no TF do padrão). **15m só marca a entrada** (close). O swing 15m (Rastreador 09:32) é **registro, não candidato**. **3×ATR D (`run_signal`) = só TETO**, não é o stop do setup.
9. **GATE (vale durante o bootcamp; só o Bernardo afrouxa, no `config.py`):**
   - stop estrutural **1h/D < 3,0% = não candidato** (`risco.py`: taxa+slip 0,30% ≤ 10% do risco; stop de ~1% no 15m = **NÃO** no bootcamp);
   - **3,00–3,02% = normal** (risco ≤1% da conta com 6 USDT);
   - **acima de 3,02% até 9,66% = EXCEÇÃO**: justificativa escrita no journal + Risco confere (risco ≤3%);
   - **> 9,66% OU > 3×ATR D = NÃO**. **Não apertar o stop**;
   - **E** R:R ≥2 líquido: `(alvo − 0,30) / (stop + 0,30) ≥ 2` ⇔ **alvo ≥ 2×stop + 0,90%** ⇒ no piso, alvo mínimo **6,9%** (stop 3,0%) até **20,2%** (stop 9,66%);
   - **Nunca apertar o stop para caber. Stop "no meio do padrão" (Deriv/BabyPips) é proibido.** Se não cabe → setup **FORA** nesta janela.
10. **Altura do padrão:** ≪ ~1% = descartar (piso de desenho do 16/18). **Altura mínima efetiva pelo GATE = 2×stop + 0,90% ≥ 6,9%** (só padrões no 1h/D costumam chegar aí). Range mediano 15m: BTC 0,185% · ETH 0,254% · SOL 0,304% (arquivo 12) → **a mediana do 15m não paga o R:R pós-taxa**; o 15m não é âncora de stop.
11. **Liberação real** só com **expectativa líquida positiva medida pela Estatística**. Até lá: paper.

**Tetos 3×ATR D de hoje (`run_signal`, Estatística 18:38 BRT) = teto do run_signal, NÃO o stop do setup:** BTC 7,7% · ETH 9,3% · SOL 11,7% (SOL: teto efetivo da conta = 9,66%). Faixa válida do stop estrutural **1h/D**: **3,0–9,66% e ≤ 3×ATR D** (BTC ≤7,7% · ETH ≤9,3% · SOL ≤9,66%); acima de 3,02% = exceção + Risco confere.

> **Expectativa honesta:** com stop ≥3,0% (1h/D) e alvo ≥6,9%, quase nenhum padrão intradiário passa. **Poucos ou zero setups no bootcamp é resultado esperado**: o E1 registra dias com setup (sem estimar frequência com poucos dias, ver §4) e não é falha do playbook.

**Abreviação usada na tabela:** **GATE** = regras 8 + 9 (stop estrutural **1h/D** na faixa 3,0–9,66% e ≤ teto 3×ATR D; swing 15m = registro, não candidato; >3,02% = exceção + journal + Risco confere; alvo ≥ 2×stop + 0,90% ≥ 6,9% no piso; sem apertar; sem stop no meio; 1 loss = dia encerrado).

---

## 2. Tabela única

| Padrão | Direção | Clear (seção) | Strike (#) | Web/Bulkowski (falha/alvo; ações D sem custo, só ranking) · Deriv (19) | Regra da mesa (filtro D · gatilho 15m close · stop · alvo · altura mín · GATE) | Status | Experimento paper |
|---|---|---|---|---|---|---|---|
| **Triângulo ascendente** | Continuação ↑ | Cap.11 §11.2 (topo ~horizontal; ≥2 topos + ≥2 fundos; projeção = base) | #7 ✅ (top 5) | Rompe ↑ 63% · falha 17% · alvo 70% · throwback 64%; Bybit Learn: romper antes de ~75% do ápice · **Deriv p.21: "bilateral"** (só o lado ↑ adotado) | D HH/HL + SMA100 · close 15m acima do topo plano + vol relativo · **stop = último HL do triângulo no 1h/D** (swing 15m = registro) · alvo = altura (base) · altura ≥1% de desenho, **≥2×stop+0,90% (≥6,9%) para passar** · **GATE** | **ATIVO** (prioridade 1) | E1, E4 |
| **Triângulo simétrico** | Bilateral | Cap.11 §11.2 (vértice; figura rompe ↑) | #9 ✅ só se ↑ + D alta | ↑: falha 25% · alvo 58%; Bulkowski: "performance is awful" · Deriv: não cobre | Só registrar; se romper ↓ com posição aberta = sair | **FORA v1** (log de controle) | E1 (controle) |
| **Triângulo descendente** | Continuação ↓ | Cap.11 §11.2 (base ~horizontal; figura rompe ↓) | #8 🟡 | **Sem fonte** de stat (12/18) · Deriv p.22: "bilateral", stop "logo abaixo da linha" = REJEITADO | Não comprar; D HH/HL + descendente no 1h = conflito → flat; close 15m abaixo da base com posição = sair | **SÓ SAÍDA** | E3 (veto) |
| **Retângulo** | Bilateral (mesa: só breakout ↑) | Cap.11 §11.3 ("grande congestão/equilíbrio"; figura: rompe para os 2 lados) | #16 ✅ ↑ / #17 🟡 ↓ | **Sem fonte** de stat; Investopedia: falsos breakouts abundantes · Deriv: não cobre | D a favor · close 15m acima da resistência + vol (flip só com close) · stop = suporte do range/último HL no **1h/D** (swing 15m = registro) · alvo = altura · **GATE** · compra na base (mean-reversion) = FORA v1 · rompe ↓ = sair | **ATIVO** (só breakout ↑) | E1, E2, E4 |
| **Cunha descendente** | Continuação ↑ (Clear) / R-C ↑ (Strike, Deriv) | Cap.11 §11.4 (linhas convergentes inclinadas p/ baixo; figura: dentro de alta, rompe ↑; projeção = triângulo) | #11 ✅ (top 5, empate) | Rompe ↑ 68% · ↑: falha 26% · alvo 62%; Bulkowski: "poor performer" · Deriv p.23: entra "exatamente quando sai" (pavio) = REJEITADO | Só como **pullback dentro de D HH/HL** (nunca "fundo" em D de baixa) · padrão no 1h · close 15m acima da LTB da cunha + vol · stop = mínima da cunha no **1h/D** (swing 15m = registro) · alvo = altura · altura ≥1,5% de desenho · **GATE** | **ATIVO** (baixa prioridade) | E1, E4 |
| **Cunha ascendente** | ↓ (Clear: continuação de baixa; Strike/Deriv: reversão ↓) | Cap.11 §11.4 (figura: dentro de baixa, rompe ↓) | #10 🟡 | Rompe ↓ 60% · ↓: último 36/36 · falha 51% · alvo 32% · Deriv p.23: short (proibido) | Não comprar; close 15m abaixo do suporte da cunha com posição = sair | **SÓ SAÍDA** | E3 (veto) |
| **Bandeira de alta** | Continuação ↑ | Cap.11 §11.5 (paralelogramo inclinado contra a tendência; **exige mastro** após forte rally; figura projeta o mastro) | #12 ✅ (top 5) | Rompe ↑ 60% · falha 44% · alvo 46%; Investopedia: 5–20 barras, base não passa do meio do mastro · Deriv: não cobre | D HH/HL · **mastro ≥1,5%** (desenho) · close 15m acima da borda superior + vol relativo · stop = base da bandeira no **1h/D** (swing 15m = registro) · alvo = mastro "com cautela" (metade não bate) · **para passar: mastro ≥2×stop+0,90% (≥6,9%)** · **GATE** | **ATIVO** (prioridade 2) | E1, E2 |
| **Bandeira de baixa** | Continuação ↓ | Cap.11 §11.5 (espelho) | #13 🟡 | **Sem fonte** de stat (12/18) · Deriv: não cobre | Não comprar; close abaixo da base com posição = sair | **SÓ SAÍDA** | E3 (veto) |
| **Flâmula (↑ / ↓)** | Continuação | Cap.11 §11.6 ("não deixa de ser bandeira"; linhas convergentes = pequeno triângulo) | #14 ✅ ↑ / #15 🟡 ↓ | Falha 54% · alvo 32–35% · "meio do movimento" só ~30% · Deriv: não cobre | ↑: só registrar (sem trade) · ↓: não comprar / sair | **FORA v1** (↑) · **SÓ SAÍDA** (↓) | E1 (controle) / E3 |
| **OCO (H&S topo)** | Reversão ↓ | Cap.12 §12.1 (ombro-cabeça-ombro + neckline; projeção cabeça→neckline; "também como continuação") | #1 🟡 | 9º/36 · falha 19% · alvo 51% · pullback 68% · Deriv p.14: short + stop no meio (proibidos) | Não comprar; close 15m abaixo da neckline (D/1h) com posição = sair; pullback à neckline perdida ≠ compra | **SÓ SAÍDA** | E3 (veto) |
| **OCOI (H&S invertido)** | Reversão ↑ | Cap.12 §12.1 (espelho; figura projeta ↑) | #2 ✅ (preferir D) | 13º/39 · falha 11% · alvo 71% · throwback 65% · Deriv p.15: entra "logo acima" (sem close) = adaptado | Padrão no **D ou 1h** (nunca micro-15m) · (a) D: só após close D acima da neckline (= 1º HH; ombro dir. = HL) + SMA100, ou (b) 1h: fim de pullback **dentro** de D HH/HL · close 15m na janela acima da neckline + vol · **stop = mínima do ombro direito no 1h/D** (swing 15m = registro) · alvo = cabeça→neckline · **GATE** | **ATIVO** (D/1h) | E1, E5 |
| **Fundo duplo (W)** | Reversão ↑ | Cap.12 §12.2 (só em região de fundo; confirma ao romper o **eixo**) | #4 ✅ (top 5) | Adam&Eve: 17º/39 · falha 12% · alvo 69% · **48% nunca confirmam** · Deriv p.16: stop "no meio" (proibido); alvo-2 = início do declínio (só sombra) | Igual OCOI: D/1h · só após close 15m acima do **eixo** (comprar o 2º fundo antes = veto) · stop = abaixo do **2º fundo no 1h/D** (swing 15m = registro) · alvo 1 = fundo→eixo (alvo 2 Deriv só sombra) · **GATE** | **ATIVO** (D/1h) | E1, E5 |
| **Topo duplo (M)** | Reversão ↓ | Cap.12 §12.2 (alta c/ volume → correção c/ menos volume → falha na R → perde o eixo) | #3 🟡 | Adam&Eve: 10º · falha 21% · alvo 54%; ~63% não confirmam (⚠️ snippets, não reconferido) · Deriv p.17: "pequena operação" short (proibido) | Não comprar perto do 2º topo; long de rompimento contra M recém-formado no 1h = veto; perda do eixo (close) com posição = sair | **SÓ SAÍDA** | E3 (veto) |
| **Cup & handle** | Continuação ↑ | **Não está no Clear** | #18 ✅ (melhor D/1h) | 3º/39 · falha 5% · alvo 61%; 47% devolvem em 2 meses; forma em 7–65 semanas · Deriv p.18: igual, "explosivo" sem fonte, sem stop | Só **D/swing** (scan do Rastreador às 09:32): se a alça do D romper na janela, close 15m + vol · stop = mínima da **alça no D** (swing 15m = registro) · alvo = profundidade da xícara · **GATE** · "mini-cup" 15m proibido | **FORA no 15m** · D = observação (raro) | E1 |

**Deriv (19) cruzado:** 0 padrões novos; nuances (bilaterais, stop no meio, alvo-2 do W, quebra > 1 dia) tratadas acima. Fundo arredondado (Deriv p.20, Strike #20) = REJEITADO como setup (entrada no meio do U); topo arredondado (Deriv p.19, Strike #19) = SÓ SAÍDA (não comprar o ressalto ao pescoço).

---

## 3. Checklist de entrada paper (vale para todo padrão ATIVO)

1. **Pré-condições:** 10:00–12:30 BRT · sem bloqueio do Notícias (evitar 15 min antes/depois de dado macro) · **nenhum loss hoje** · <3 trades no dia · sem posição aberta.
2. **Filtro D (só filtro):** HH/HL + SMA100 ok · sem quebra de LTA no D · sem padrão SÓ SAÍDA ativo no D/1h do ativo · D e 15m sem conflito. Falhou um → **FLAT**.
3. **Padrão ATIVO desenhado no TF certo:** continuação no 15m/1h; reversão (fundo duplo/OCOI) só no D/1h. Critérios do Clear: ≥2 topos + ≥2 fundos (triângulo), mastro (bandeira), eixo/neckline (W/OCOI). Não desenhar padrão em cima de 1 pavio anômalo (Deriv p.7).
4. **Gatilho:** candle 15m **FECHADO** além do nível + volume relativo do par Bybit acima da média do mesmo horário. Pavio ≠ gatilho. O 15m não redesenha a tese.
5. **Stop candidato = estrutura do padrão no 1h/D** (ombro, 2º fundo, HL, base da bandeira/alça). Escolhido **antes** de calcular o risco. **Anotar lado a lado: (a) stop 1h/D % · (b) swing 15m % (registro) · (c) teto 3×ATR D %.** Nunca o "meio do padrão". O 15m só marca o close de entrada.
6. **GATE do stop (só sobre (a) 1h/D):** < 3,0% → **não candidato** · 3,00–3,02% → ok · acima de 3,02% até 9,66% → **EXCEÇÃO** (justificativa no journal + Risco confere) · > 9,66% **ou** > 3×ATR D → **NÃO**. **Não apertar para caber.** Swing 15m não decide.
7. **GATE do alvo:** alvo = menor entre altura projetada e próxima resistência; precisa de **alvo ≥ 2×stop + 0,90%** (≥ **6,9%** no piso). Não passou → FORA.
8. **Fluxo:** Rastreador (fatos) → Caçador → Notícias/Baleias se relevante → **Risco** (único NÃO) → Chefe → journal paper (ledger só Chefe/designado). **Nunca ordem real.**
9. **Pós-trade:** 1 loss = dia encerrado. Registrar tudo no log (inclusive vetados, em `barrados.csv` da Estatística).

---

## 4. Experimentos v1 (máx 5) — quem mede: **Estatística**

> IDs alinhados com o [19 §5](19-deriv-10padroes.md) (E1, E3, E4, E5 iguais). **E2 aqui substitui o E2 do 19** ("quebra > 1 dia" vai para a v2). Amostras mínimas são parâmetros de desenho (Chefe pode ajustar), não estatística de mercado. Métrica comum: **expectativa líquida por trade (R e %) após 0,30% RT**. Tudo paper/sombra.

| # | Hipótese | Como roda | Sucesso | Falha | Mede |
|---|---|---|---|---|---|
| **E1 — GATE: quantos dias com setup 3,0–9,66% (1h/D)** | Em **quantos dias** (07, 08 e 09/10) aparece **pelo menos um** setup ATIVO com stop na estrutura **1h/D** entre 3,0–9,66%, ≤ teto 3×ATR D, altura ≥6,9% e ≥2×stop+0,90%, close 15m na janela. **0/3 = "sem evento"** | Por candidato: `(a) stop 1h/D %` (conta) · `(b) swing 15m %` (registro) · `(c) teto 3×ATR D %` · stop "meio" Deriv (sombra) · risco % conta · altura · passa? → `barrados.csv` + `dia · setup_na_janela (s/n)` | 3 dias com X/3; 0 decisões por (b)/(c); 0 stops apertados; 0 entradas fora do GATE; exceção >3,02% com justificativa + Risco | Dia sem registro; decisão pelo swing 15m ou pelo ATR; stop movido. **Leitura:** 0/3 **não estima frequência** (ver nota) | Estatística (Risco confere) |
| **E2 — Continuação com mastro/range: bandeira ↑ (mastro ≥1,5%) + retângulo ↑ breakout** | Só mastro/range grande paga o GATE; os pequenos viram veto | Logar toda bandeira com mastro ≥1,5% e todo retângulo com altura ≥1% (15m/1h); paper só os que passam no GATE; medir hit alvo × stop até 12:30 e throwback em 4 candles | Expectativa líquida > 0 com ≥10 setups aprovados | ≤0, ou <10 setups em 10 sessões → rebaixar para FORA na v2 (registrar % vetado por altura) | Estatística |
| **E3 — Veto bearish "SÓ SAÍDA"** | Os vetos (OCO, topo duplo, triângulo desc., cunha asc., bandeira/flâmula ↓, topo arredondado) protegem | Às 09:32 e 10:00, marcar bearish ativo no D/1h por ativo; quando houver veto com gatilho long, registrar R líquido-sombra até 12:30 | Com N ≥10 vetos com gatilho: soma do R-sombra ≤ 0 → veto fica | Long tomado com bearish ativo, ou veto sem registro; soma > 0 e média ≥ +0,5R → revisar veto (critério do 19) | Estatística |
| **E4 — Pavio × close 15m + volume** | Close + vol reduz falsos rompimentos e melhora a expectativa (Deriv entra no pavio) | Em todo rompimento de triângulo asc. / cunha ↓ / retângulo ↑ / neckline (altura ≥1%): entrada-sombra (a) pavio vs (b) close 15m + vol; falso = close de volta dentro em ≤4 candles; registrar % do caminho até o ápice | Com N ≥15: close mantido salvo se pavio tiver falso ≤ close **e** R líquido maior | Entrada paper por pavio antes da decisão | Estatística |
| **E5 — Reversões D/1h (fundo duplo / OCOI)** | Só confirmadas e dentro do GATE têm edge; alvo-2 do Deriv (início do declínio) pode melhorar R:R | Para cada W/OCOI confirmado (close 15m acima do eixo/neckline): o que vem primeiro — stop estrutural 1h/D, alvo 1 (altura), alvo 2 (sombra) — até 12:30 e +24h; % vetado pelo GATE | N ≥10: alvo-2 só vira parcial se a expectativa líquida com alvo 2 > alvo 1; expectativa líquida > 0 com ≥5 setups aprovados | Usar alvo 2 para justificar R:R antes da validação; 0–4 setups → manter só como mapa de contexto | Estatística |


**Critério de leitura do E1 (Estatística, alinhado ao 19 §5 / Chefe 18:42 BRT):** E1 mede **quantos dias** (07–09/10) com ≥1 setup na faixa. Sucesso = **registro completo** (X/3), não um % de frequência. **0/3 = "sem evento"** e **NÃO estima frequência:** com 0 em 3, o teto de 95% é `1 − 0,05^(1/3)` ≈ **63% dos dias**. Diga só que é **raro**, não o quanto. "Sem evento" **não** vira conclusão de que o padrão não existe nem de que o GATE está errado.

---

## 5. O que muda na v2

1. **Dados do paper (E1–E5 / `barrados.csv`):** promover/rebaixar status pela expectativa líquida; recalibrar a altura mínima com a distribuição real de stops estruturais 15m × teto 3×ATR D.
2. **Regra de custo do `risco.py` (stop ≥3,0%):** se o Bernardo mudar o `config.py` depois do bootcamp, refazer o GATE (a mesa não muda isso).
3. **Candles (Clear Cap.13+):** entram **só como gatilho** dentro de um padrão ATIVO (nunca setup isolado; ver 12 §1).
4. **Deriv E2 "quebra > 1 dia"** para níveis do D: testar na v2.
5. **Capital/ordem mínima:** se a conta ou a ordem mínima mudarem, a Estatística recalcula 3,02% / 9,66%.
6. **Medidas que faltam ("sem fonte" hoje):** stats de triângulo descendente, retângulo e bandeira de baixa; range mediano 1h na Bybit para dimensionar padrões do 1h.

---

Arquivo: `/workspace/cripto-estudo/20-playbook-padroes-v1.md` · Estudo de base: `livros/clear-estudo-cap11.md` · Paper only.
