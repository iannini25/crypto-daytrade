import { DESK_AGENTS, nameTag } from './agents';
import { Camera } from './camera';
import { nextDemo, seedDemo, startLive, supabaseConfigured, type Mode } from './events';
import { MAP_H, MAP_W, ROOMS, TILE, buildBlocked, roomAt, roomCenter, tileOf, worldOf } from './office';
import { avatarAt, drawOffice } from './render';
import { applyEvent, createAvatars, stepAvatars, type Avatar } from './sim';

const canvas = document.querySelector<HTMLCanvasElement>('#view')!;
const ctx = canvas.getContext('2d')!;
const feedEl = document.querySelector<HTMLElement>('#feed')!;
const cardEl = document.querySelector<HTMLElement>('#card')!;
const modeEl = document.querySelector<HTMLElement>('#mode')!;
const roomsEl = document.querySelector<HTMLElement>('#rooms')!;
const statusEl = document.querySelector<HTMLElement>('#conn')!;

const cam = new Camera();
const blocked = buildBlocked();
const avatars = createAvatars(blocked, MAP_W, MAP_H);
let mode: Mode = 'demo';
let hoverRoom: string | null = null;
let selected: Avatar | null = null;
let tick = 0;
const t0 = performance.now();

const worldBounds = () => {
  cam.bounds = { x: -20, y: -20, w: MAP_W * TILE + 40, h: MAP_H * TILE + 40 };
};

function resize(): void {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.floor(window.innerWidth * dpr);
  canvas.height = Math.floor(window.innerHeight * dpr);
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  const narrow = window.innerWidth < 800;
  cam.insets = narrow
    ? { top: 96, right: 8, bottom: Math.round(window.innerHeight * 0.4), left: 8 }
    : { top: 96, right: 340, bottom: 10, left: 10 };
  cam.setView(window.innerWidth, window.innerHeight, dpr);
  worldBounds();
  const freeW = Math.max(200, window.innerWidth - cam.insets.left - cam.insets.right);
  const freeH = Math.max(200, window.innerHeight - cam.insets.top - cam.insets.bottom);
  const fit = Math.min(freeW / (MAP_W * TILE), freeH / (MAP_H * TILE)) * 0.98;
  if (!resizedOnce) {
    const id = location.hash.replace('#', '');
    const room = ROOMS.find((r) => r.id === id);
    if (room) {
      const c = roomCenter(room);
      const w = worldOf(c.x, c.y);
      cam.focus(w.x, w.y, 1.55);
    } else {
      cam.focus((MAP_W * TILE) / 2, (MAP_H * TILE) / 2, fit);
    }
  }
  cam.clamp();
}
let resizedOnce = false;
resize();
resizedOnce = true;
window.addEventListener('resize', resize);

for (const room of ROOMS) {
  const btn = document.createElement('button');
  btn.textContent = room.label;
  btn.type = 'button';
  btn.addEventListener('click', () => {
    const c = roomCenter(room);
    const w = worldOf(c.x, c.y);
    cam.focus(w.x, w.y, Math.max(cam.zoom, 1.35));
    hoverRoom = room.id;
  });
  roomsEl.append(btn);
}

function fmt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(d);
}

function renderFeed(): void {
  const rows: string[] = [];
  for (const av of avatars) {
    const latest = av.events.slice(0, 3);
    if (!latest.length) continue;
    rows.push(`<section><h3>${escapeHtml(nameTag(av.agent))} <span>${escapeHtml(av.agent.role)}</span></h3>`);
    for (const ev of latest) {
      const bad = ev.status !== 'ok' ? ' bad' : '';
      rows.push(
        `<p class="${bad}"><time>${fmt(ev.created_at)}</time> <b>${escapeHtml(ev.kind)}</b> ${escapeHtml(ev.summary)}</p>`,
      );
    }
    rows.push('</section>');
  }
  feedEl.innerHTML = rows.join('') || '<p class="empty">Sem eventos ainda.</p>';
}

function renderCard(): void {
  if (!selected) {
    cardEl.hidden = true;
    return;
  }
  const av = selected;
  const last = av.events[0];
  cardEl.hidden = false;
  cardEl.innerHTML = `
    <button type="button" id="close-card">fechar</button>
    <h2>${escapeHtml(nameTag(av.agent))}</h2>
    <p class="role">${escapeHtml(av.agent.role)}${av.agent.helper ? ' · ajudante' : ''}</p>
    <p>Sala: <b>${escapeHtml(av.room)}</b> · pose ${escapeHtml(av.pose)}${av.error ? ' · <b class="bad">erro</b>' : ''}</p>
    <p class="id">${escapeHtml(av.agent.id)}</p>
    <h3>Últimos eventos</h3>
    <ul>
      ${(av.events.length ? av.events : []).map((ev) => `<li><time>${fmt(ev.created_at)}</time> <b>${escapeHtml(ev.kind)}</b> ${escapeHtml(ev.status)} — ${escapeHtml(ev.summary)}</li>`).join('') || '<li>sem eventos</li>'}
    </ul>
    ${last ? '' : ''}
  `;
  cardEl.querySelector('#close-card')?.addEventListener('click', () => {
    selected = null;
    renderCard();
  });
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

function onEvent(ev: Parameters<typeof applyEvent>[1]): void {
  applyEvent(avatars, ev, blocked, MAP_W, MAP_H);
  renderFeed();
  if (selected && !avatars.includes(selected)) selected = null;
  if (selected && (selected.agent.id === ev.agent_id || selected.agent.name === ev.agent_name)) renderCard();
}

let dragging = false;
let lastX = 0;
let lastY = 0;
canvas.addEventListener('pointerdown', (e) => {
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', (e) => {
  if (dragging) {
    cam.panBy(e.clientX - lastX, e.clientY - lastY);
    lastX = e.clientX;
    lastY = e.clientY;
    return;
  }
  const w = cam.screenToWorld(e.clientX, e.clientY);
  const t = tileOf(w.x, w.y);
  hoverRoom = roomAt(t.tx, t.ty)?.id ?? null;
});
canvas.addEventListener('pointerup', (e) => {
  const moved = Math.hypot(e.clientX - lastX, e.clientY - lastY);
  dragging = false;
  if (moved > 6) return;
  const hit = avatarAt(cam, avatars, e.clientX, e.clientY);
  if (hit) {
    selected = hit;
    renderCard();
    return;
  }
  const wpt = cam.screenToWorld(e.clientX, e.clientY);
  const tile = tileOf(wpt.x, wpt.y);
  const room = roomAt(tile.tx, tile.ty);
  if (room) {
    const c = roomCenter(room);
    const p = worldOf(c.x, c.y);
    cam.focus(p.x, p.y, Math.max(cam.zoom, 1.25));
  }
});
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const factor = e.deltaY > 0 ? 0.9 : 1.1;
  cam.zoomAt(cam.zoom * factor, e.clientX, e.clientY);
}, { passive: false });

let last = performance.now();
function frame(now: number): void {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  stepAvatars(avatars, dt);
  drawOffice(ctx, cam, avatars, hoverRoom, (now - t0) / 1000);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

async function boot(): Promise<void> {
  if (supabaseConfigured()) {
    mode = 'live';
    modeEl.textContent = 'LIVE';
    statusEl.textContent = 'conectando ao Supabase…';
    const client = await startLive(onEvent, (s) => {
      statusEl.textContent = s;
    });
    if (!client) {
      mode = 'demo';
      startDemo('Supabase indisponível — modo demo');
    }
  } else {
    startDemo('sem NEXT_PUBLIC_SUPABASE_* — modo demo');
  }
  renderFeed();
}

function startDemo(reason: string): void {
  mode = 'demo';
  modeEl.textContent = 'DEMO';
  modeEl.classList.add('demo');
  statusEl.textContent = reason;
  for (const ev of seedDemo()) onEvent(ev);
  window.setInterval(() => {
    onEvent(nextDemo(tick++));
    renderFeed();
  }, 6000);
}

boot();

document.querySelector('#count')!.textContent = `${DESK_AGENTS.length} agentes da mesa`;
renderCard();
