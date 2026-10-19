// Faixa vermelha FAKE ALARM. Escondida até um agent_events ou ?fakeAlarm=1.
import { alarmVisible } from '../grok/alarm';
import type { UiComponent, UiContext } from './context';
import { h, setHidden, setText } from './dom';

export class FakeAlarmBanner implements UiComponent {
  readonly el: HTMLElement;
  private detail: HTMLElement;

  constructor(private ctx: UiContext) {
    this.detail = h('span', { class: 'ui-fake-alarm__detail' });
    this.el = h(
      'div',
      { class: 'ui-fake-alarm', role: 'alert', hidden: true, attrs: { 'aria-hidden': 'true' } },
      h('strong', { class: 'ui-fake-alarm__title', text: 'FAKE ALARM' }),
      this.detail,
    );
  }

  render(): void {
    const src = this.ctx.store.grokSource;
    const search = typeof location !== 'undefined' ? location.search : '';
    const state = src?.alarm ?? { active: false, text: '' };
    const on = src ? alarmVisible(state, undefined, search) : alarmVisible({ active: false, text: '' }, undefined, search);
    setHidden(this.el, !on);
    this.el.setAttribute('aria-hidden', on ? 'false' : 'true');
    const extra = on && state.text && state.text.trim() !== 'FAKE ALARM' ? state.text : '';
    setText(this.detail, extra);
    this.ctx.root.classList.toggle('has-fake-alarm', on);
  }
}
