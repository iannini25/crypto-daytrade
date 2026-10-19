// Painéis somente leitura: $DACITY e o top 10 pump.fun do DexScreener. Sem chave e sem botão de compra.
import {
  bestQuote,
  boostsLatestUrl,
  boostsTopUrl,
  DACITY_MINT,
  dacityPairsUrl,
  formatPct,
  formatUsd,
  rankedPumpMints,
  tokensUrl,
  trendingQuotes,
  type TokenQuote,
} from '../market/dex';
import type { UiComponent, UiContext } from './context';
import { h, iconButton, setHidden, setText } from './dom';

const MARKET_ICON =
  '<svg class="ui-px-icon" width="20" height="20" viewBox="0 0 10 10" shape-rendering="crispEdges" aria-hidden="true" focusable="false">' +
  '<path fill="currentColor" d="M0 8h10v1H0zM1 6h2v2H1zM4 3h2v5H4zM7 4h2v4H7z"/></svg>';

const POLL_MS = 60_000;

export class MarketPanel implements UiComponent {
  readonly el: HTMLElement;
  readonly button: HTMLButtonElement;
  private body: HTMLElement;
  private status: HTMLElement;
  private open: boolean;
  private loading = true;
  private error = '';
  private dacity: TokenQuote | null = null;
  private trending: TokenQuote[] = [];
  private loadedAt = 0;
  private sig = '';
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(private ctx: UiContext) {
    this.open = !ctx.isNarrow();
    this.button = iconButton(MARKET_ICON, 'Mercado: $DACITY e trending pump.fun', () => this.toggle(), 'ui-btn-market');
    this.button.setAttribute('aria-pressed', this.open ? 'true' : 'false');
    this.button.setAttribute('aria-controls', 'ui-market');
    this.status = h('p', { class: 'ui-market__status ui-muted', text: 'Lendo o DexScreener…' });
    this.body = h('div', { class: 'ui-market__body' });
    this.el = h(
      'aside',
      { class: 'ui-panel ui-market', attrs: { id: 'ui-market', 'aria-label': 'Mercado pump.fun, somente leitura' } },
      h('div', { class: 'ui-market__head' }, h('h2', { text: 'Mesa memecoins' }), h('span', { class: 'ui-market__flag', text: 'somente leitura' })),
      this.status,
      this.body,
    );
    this.el.hidden = !this.open;
    void this.refresh();
    this.timer = setInterval(() => void this.refresh(), POLL_MS);
  }

  toggle(open?: boolean): void {
    this.open = open ?? !this.open;
    this.button.setAttribute('aria-pressed', this.open ? 'true' : 'false');
    setHidden(this.el, !this.open);
    this.ctx.invalidate();
  }

  render(): void {
    setHidden(this.el, !this.open);
    const when = this.loadedAt ? `Atualizado ${formatAgo(Date.now() - this.loadedAt)}` : '';
    if (this.loading && !this.dacity && !this.trending.length) setText(this.status, 'Lendo o DexScreener…');
    else if (this.error && !this.dacity) setText(this.status, this.error);
    else setText(this.status, when);
    const sig = JSON.stringify({ error: this.error, dacity: this.dacity, trending: this.trending });
    if (sig === this.sig) return;
    this.sig = sig;
    this.body.replaceChildren(dacityCard(this.dacity), trendingCard(this.trending));
  }

  private async refresh(): Promise<void> {
    try {
      const [pairs, top, latest] = await Promise.all([getJson(dacityPairsUrl()), getJson(boostsTopUrl()), getJson(boostsLatestUrl())]);
      const quote = bestQuote(pairs, DACITY_MINT);
      const wanted = rankedPumpMints(top, latest, 30);
      const hydrated = wanted.length ? await getJson(tokensUrl(wanted)) : [];
      this.dacity = quote;
      this.trending = trendingQuotes(top, latest, hydrated, 10);
      this.error = quote ? '' : 'DexScreener não devolveu $DACITY.';
      this.loadedAt = Date.now();
    } catch (err) {
      this.error = `DexScreener indisponível (${(err as Error).message})`;
    } finally {
      this.loading = false;
      this.ctx.invalidate();
    }
  }
}

async function getJson(url: string): Promise<unknown> {
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function formatAgo(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 5) return 'agora';
  if (s < 60) return `há ${s} s`;
  return `há ${Math.round(s / 60)} min`;
}

function dacityCard(quote: TokenQuote | null): HTMLElement {
  const card = h('section', { class: 'ui-market__card', attrs: { 'aria-label': '$DACITY' } }, h('h3', { text: '$DACITY' }));
  if (!quote) {
    card.append(h('p', { class: 'ui-muted', text: 'Sem cotação ainda.' }));
    return card;
  }
  card.append(
    statGrid([
      ['Preço', formatUsd(quote.priceUsd)],
      ['Market cap', formatUsd(quote.marketCap)],
      ['Liquidez', formatUsd(quote.liquidityUsd)],
      ['Volume 24h', formatUsd(quote.volumeH24)],
      ['Variação 24h', formatPct(quote.changeH24), changeClass(quote.changeH24)],
    ]),
    h(
      'a',
      { class: 'ui-market__link', attrs: { href: quote.url, target: '_blank', rel: 'noreferrer noopener' } },
      'Ver no DexScreener',
    ),
  );
  return card;
}

function trendingCard(rows: TokenQuote[]): HTMLElement {
  const card = h('section', { class: 'ui-market__card', attrs: { 'aria-label': 'Top 10 trending Solana pump.fun' } }, h('h3', { text: 'Top 10 · Solana / pump.fun' }));
  if (!rows.length) {
    card.append(h('p', { class: 'ui-muted', text: 'Nenhum mint pump.fun no ranking público agora.' }));
    return card;
  }
  const list = h('ol', { class: 'ui-market__list' });
  rows.forEach((row, i) => {
    list.append(
      h(
        'li',
        { class: 'ui-market__row' },
        h('span', { class: 'ui-market__rank', text: String(i + 1) }),
        h(
          'a',
          { class: 'ui-market__sym', attrs: { href: row.url, target: '_blank', rel: 'noreferrer noopener' }, title: row.name || row.mint },
          row.symbol,
        ),
        h('span', { class: 'ui-market__px', text: formatUsd(row.priceUsd) }),
        h('span', { class: `ui-market__chg ${changeClass(row.changeH24)}`, text: formatPct(row.changeH24) }),
      ),
    );
  });
  card.append(list);
  return card;
}

function statGrid(items: Array<[string, string, string?]>): HTMLElement {
  const grid = h('dl', { class: 'ui-market__stats' });
  for (const [label, value, cls] of items) {
    grid.append(h('div', {}, h('dt', { text: label }), h('dd', { class: cls, text: value })));
  }
  return grid;
}

function changeClass(value: number | null): string {
  if (value == null || value === 0) return '';
  return value > 0 ? 'is-up' : 'is-down';
}
