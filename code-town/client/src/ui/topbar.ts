// Barra superior: marca, conexão, carteira pump.fun, uso por conta e botões de controle.
import type { UiComponent, UiContext } from './context';
import { h, iconButton, setHidden, setText, setTitle, setVariant } from './dom';
import { FALLBACK_MARK, ICONS } from './icons';
import { TIMELAPSE_ICONS } from './timelapse';
import { UsageCards } from './usage';
import { VersionChip } from './version';
import { WalletBar } from './wallet-bar';
import { wordmark } from './widgets';

export class TopBar implements UiComponent {
  readonly el: HTMLElement;
  private pill: HTMLElement;
  private pillText: HTMLElement;
  private demoBadge: HTMLElement;
  private usage: UsageCards;
  private version: VersionChip;
  private wallet: WalletBar;
  private hadOpen = false;
  private sidebarBtn: HTMLButtonElement;
  private feedBtn: HTMLButtonElement;
  private timelapseBtn: HTMLButtonElement;
  readonly settingsBtn: HTMLButtonElement;
  /** Grupo dos botões de painéis (feed, configurações, ajuda); o histórico entra aqui (ui/index.ts). */
  readonly panelGroup: HTMLElement;

  constructor(private ctx: UiContext) {
    // Marca: usa o logo do projeto se existir; senão, o prédio em pixels.
    const mark = h('span', { class: 'ui-brand__mark' });
    const logo = h('img', { attrs: { src: '/assets/brand/logo-mark.png', srcset: '/assets/brand/logo-mark@4x.png 4x', alt: '', width: 32, height: 32, draggable: 'false' } });
    logo.addEventListener('error', () => {
      mark.innerHTML = FALLBACK_MARK;
    });
    mark.append(logo);

    this.pillText = h('span', { class: 'ui-pill__text' });
    this.pill = h('span', { class: 'ui-pill', role: 'status', attrs: { 'aria-live': 'polite' } }, h('span', { class: 'ui-pill__dot' }), this.pillText);
    this.demoBadge = h('span', { class: 'ui-demo-badge', text: 'Demonstração', title: 'Agentes de demonstração ligados (desligue em Configurações)', hidden: true });

    this.wallet = new WalletBar();

    this.usage = new UsageCards(ctx);

    this.sidebarBtn = iconButton(ICONS.sidebar, 'Painel lateral ( [ )', () => ctx.togglePanel('sidebar'), 'ui-btn-sidebar');
    this.feedBtn = iconButton(ICONS.feed, 'Feed de atividade ( ] )', () => ctx.togglePanel('feed'));
    this.timelapseBtn = iconButton(TIMELAPSE_ICONS.timelapse, 'Timelapse: reproduzir o dia (L)', () => ctx.toggleTimelapse(), 'ui-btn-timelapse');
    this.settingsBtn = iconButton(ICONS.settings, 'Configurações', () => ctx.toggleSettings());
    this.settingsBtn.setAttribute('aria-haspopup', 'dialog');
    this.version = new VersionChip(ctx, this.settingsBtn);
    const viewGroup = h(
      'div',
      { class: 'ui-btn-group', role: 'group', attrs: { 'aria-label': 'Câmera' } },
      iconButton(ICONS.overview, 'Visão geral (O)', () => ctx.camera('overview')),
      iconButton(ICONS.zoomOut, 'Afastar (−)', () => ctx.camera('zoomOut')),
      iconButton(ICONS.zoomIn, 'Aproximar (+)', () => ctx.camera('zoomIn')),
    );
    const panelGroup = h(
      'div',
      { class: 'ui-btn-group', role: 'group', attrs: { 'aria-label': 'Painéis' } },
      this.timelapseBtn,
      this.feedBtn,
      this.settingsBtn,
      iconButton(ICONS.help, 'Ajuda (?)', () => ctx.openHelp()),
    );
    this.panelGroup = panelGroup;

    this.el = h(
      'header',
      { class: 'ui-topbar', role: 'banner' },
      h(
        'div',
        { class: 'ui-topbar__left' },
        this.sidebarBtn,
        h(
          'div',
          { class: 'ui-brand' },
          mark,
          h('div', { class: 'ui-brand__text' }, wordmark(), h('div', { class: 'ui-topbar__status' }, this.pill, this.version.el, this.demoBadge)),
        ),
      ),
      this.wallet.el,
      this.usage.el,
      h('div', { class: 'ui-topbar__right' }, viewGroup, panelGroup),
    );
  }

  /** Acrescenta um botão de janela própria (ex.: Meu dia) ao começo do grupo de painéis. */
  addPanelButton(btn: HTMLElement): void {
    this.panelGroup.prepend(btn);
  }

  render(): void {
    const { store } = this.ctx;
    const snap = store.snapshot;

    // Conexão.
    const conn = store.connection;
    if (conn === 'open') this.hadOpen = true;
    const label =
      conn === 'open' ? 'Conectado' : conn === 'mock' ? (store.grok ? (store.grokSource?.live ? 'Ao vivo · Grok Bot' : 'Grok Bot · demonstração') : 'Simulação') : conn === 'closed' ? 'Desconectado' : this.hadOpen ? 'Reconectando…' : 'Conectando…';
    setText(this.pillText, label);
    setVariant(this.pill, 'is-', conn);
    setTitle(
      this.pill,
      conn === 'mock'
        ? store.grok
          ? `Mesa do Grok Bot: ${store.grokSource?.status ?? ''}`
          : 'Dados simulados no navegador (?mock=1)'
        : conn === 'open'
          ? 'Recebendo eventos do servidor em tempo real'
          : 'Sem conexão com o servidor do Habblaud',
    );
    setHidden(this.demoBadge, !(conn === 'open' && snap?.meta.demo));

    this.usage.render();
    this.version.render();

    this.sidebarBtn.setAttribute('aria-pressed', String(this.ctx.isPanelOpen('sidebar')));
    this.feedBtn.setAttribute('aria-pressed', String(this.ctx.isPanelOpen('feed')));
    this.timelapseBtn.setAttribute('aria-pressed', String(this.ctx.isTimelapseOpen()));
    setHidden(this.timelapseBtn, store.mock);
  }
}
