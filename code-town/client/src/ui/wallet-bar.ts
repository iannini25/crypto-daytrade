// Painel da carteira pump.fun no lugar dos contadores do escritório.
import { h, setAttr, setText, setTitle } from './dom';
import type { Figure, OpenPosition, PeriodKey, WalletPnl } from '../../../shared/wallet/types';

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: 'day', label: 'Diário' },
  { key: 'week', label: 'Semanal' },
  { key: 'all', label: 'Total' },
];

const STATS: { key: keyof WalletPnl['periods']['day']; label: string; hint: string; tone: 'plain' | 'loss' | 'gain' | 'open' }[] = [
  {
    key: 'investido',
    label: 'Investido',
    hint: 'Tudo que entrou de fora (SOL e USDC), no valor do dólar e do câmbio na hora de cada entrada. Não muda com o filtro.',
    tone: 'plain',
  },
  {
    key: 'aportes',
    label: 'Aportes',
    hint: 'O que entrou de fora no período. O dia e a semana são no horário de Brasília; a semana começa na segunda.',
    tone: 'plain',
  },
  {
    key: 'prejuizo',
    label: 'Prejuízo',
    hint: 'Perdas realizadas no período, no custo médio, com as taxas da transação incluídas. Retirada de SOL ou USDC não entra aqui.',
    tone: 'loss',
  },
  {
    key: 'lucro',
    label: 'Lucro',
    hint: 'Ganhos realizados no período, no custo médio, com as taxas incluídas.',
    tone: 'gain',
  },
  {
    key: 'aberto',
    label: 'Em aberto',
    hint: 'Lucro ou prejuízo ainda não realizado, marcado agora. Não muda com o filtro.',
    tone: 'open',
  },
];

interface StatRefs {
  el: HTMLElement;
  value: HTMLElement;
  usd: HTMLElement;
  sub: HTMLElement;
}

export class WalletBar {
  readonly el: HTMLElement;
  private period: PeriodKey = 'all';
  private data: WalletPnl | null = null;
  private failed = '';
  private buttons = new Map<PeriodKey, HTMLButtonElement>();
  private stats = new Map<string, StatRefs>();
  private timer = 0;

  constructor() {
    const toggle = h('div', { class: 'ui-wallet__toggle', role: 'radiogroup', attrs: { 'aria-label': 'Período em Brasília' } });
    for (const period of PERIODS) {
      const btn = h('button', {
        class: 'ui-wallet__period',
        type: 'button',
        attrs: { role: 'radio', 'aria-checked': period.key === this.period ? 'true' : 'false' },
        on: { click: () => this.select(period.key) },
      }, period.label);
      this.buttons.set(period.key, btn);
      toggle.append(btn);
    }
    this.el = h('div', { class: 'ui-wallet', role: 'group', attrs: { 'aria-label': 'Carteira pump.fun', 'aria-busy': 'true' } }, toggle);
    for (const stat of STATS) {
      const value = h('span', { class: 'ui-wallet__value', text: '…' });
      const usd = h('span', { class: 'ui-wallet__usd', text: '' });
      const sub = h('span', { class: 'ui-wallet__sub', text: '' });
      const label = h('span', { class: 'ui-wallet__label', text: stat.label });
      const el = h('div', { class: `ui-wallet__stat ui-wallet__stat--${stat.tone}`, title: stat.hint }, value, usd, sub, label);
      this.stats.set(stat.key, { el, value, usd, sub });
      this.el.append(el);
    }
    void this.refresh();
    this.timer = window.setInterval(() => void this.refresh(), 60_000);
  }

  private select(period: PeriodKey): void {
    this.period = period;
    for (const [key, btn] of this.buttons) setAttr(btn, 'aria-checked', key === period ? 'true' : 'false');
    this.paint();
  }

  private async refresh(): Promise<void> {
    try {
      const res = await fetch('/api/wallet-pnl');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as WalletPnl;
      this.data = body;
      this.failed = body.ok ? '' : body.note;
    } catch (error) {
      this.data = null;
      this.failed = error instanceof Error ? error.message : 'sem resposta';
    }
    this.paint();
  }

  private paint(): void {
    setAttr(this.el, 'aria-busy', this.data ? 'false' : 'true');
    const period = this.data?.periods[this.period];
    for (const stat of STATS) {
      const refs = this.stats.get(stat.key)!;
      const figure = period?.[stat.key];
      const reason = figure?.reason || this.failed || (!this.data ? 'calculando a carteira…' : '');
      paintFigure(refs, figure, reason, stat.hint);
      if (stat.key === 'aberto') paintOpen(refs, this.data?.open ?? [], figure);
      refs.el.classList.toggle('is-up', !!figure && figure.usd !== null && figure.usd > 0.005 && (stat.tone === 'gain' || stat.tone === 'open'));
      refs.el.classList.toggle('is-down', !!figure && figure.usd !== null && (stat.tone === 'loss' ? figure.usd > 0.005 : stat.tone === 'open' && figure.usd < -0.005));
    }
    const when = this.data ? `Atualizado ${new Date(this.data.computedAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' })} BRT.` : '';
    for (const [key, btn] of this.buttons) {
      setTitle(btn, `${PERIODS.find((p) => p.key === key)?.label}. ${this.data?.note ?? ''} ${when}`.trim());
    }
  }
}

function paintFigure(refs: StatRefs, figure: Figure | undefined, reason: string, hint: string): void {
  if (!figure || figure.brl === null || figure.usd === null) {
    setText(refs.value, '—');
    setText(refs.usd, '');
    setTitle(refs.el, reason ? `${hint}\n${reason}` : hint);
    setAttr(refs.el, 'aria-label', `${refs.el.querySelector('.ui-wallet__label')?.textContent ?? ''}: indisponível. ${reason}`);
    return;
  }
  setText(refs.value, formatBrl(figure.brl));
  setText(refs.usd, formatUsd(figure.usd));
  setTitle(refs.el, hint);
  setAttr(refs.el, 'aria-label', `${refs.el.querySelector('.ui-wallet__label')?.textContent ?? ''} ${formatBrl(figure.brl)}, ${formatUsd(figure.usd)}`);
}

function paintOpen(refs: StatRefs, open: OpenPosition[], figure: Figure | undefined): void {
  const meme = open.find((p) => p.symbol !== 'SOL' && p.symbol !== 'USDC' && p.symbol !== 'USDT');
  if (!meme) {
    setText(refs.sub, '');
    return;
  }
  const qty = meme.qty.toLocaleString('pt-BR', { maximumFractionDigits: meme.qty >= 100 ? 0 : 2 });
  const avg = meme.avgUsd === null ? '' : ` · médio ${formatUsd(meme.avgUsd, meme.avgUsd < 1 ? 6 : 2)}`;
  const pnl = meme.pnlUsd === null ? '' : ` · ${formatUsd(meme.pnlUsd)}`;
  setText(refs.sub, `${qty} ${meme.symbol}${avg}`);
  const lines = open.map((p) => {
    const q = p.qty.toLocaleString('pt-BR', { maximumFractionDigits: 4 });
    const mark = p.pnlUsd === null ? 'sem preço' : formatUsd(p.pnlUsd);
    const average = p.avgUsd === null ? '' : `, médio ${formatUsd(p.avgUsd, p.avgUsd < 1 ? 6 : 2)}`;
    return `${p.symbol} ${q}${average}: ${mark}`;
  });
  const base = refs.el.title.split('\n')[0] || 'Lucro ou prejuízo ainda não realizado, marcado agora.';
  if (!figure || figure.usd === null) return;
  setTitle(refs.el, `${base}\n${qty} ${meme.symbol}${avg}${pnl}\n${lines.join('\n')}`);
}

function formatBrl(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatUsd(value: number, digits = 2): string {
  const body = Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: Math.min(2, digits), maximumFractionDigits: digits });
  return `${value < -0.0000005 ? '−' : ''}US$ ${body}`;
}
