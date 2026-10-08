import { nameTag } from './agents';
import { Camera } from './camera';
import { TH, TW, tileToWorld } from './iso';
import { MAP_H, MAP_W, PROPS, ROOMS, doorOf, roomAt, type Prop, type RoomDef } from './office';
import type { Avatar } from './sim';

function diamond(ctx: CanvasRenderingContext2D, wx: number, wy: number, scale: number, ox: number, oy: number): void {
  const x = wx * scale + ox;
  const y = wy * scale + oy;
  const hw = (TW / 2) * scale;
  const hh = (TH / 2) * scale;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + hw, y + hh);
  ctx.lineTo(x, y + TH * scale);
  ctx.lineTo(x - hw, y + hh);
  ctx.closePath();
}

function saoPauloHour(): number {
  const hour = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Sao_Paulo',
    hour: '2-digit',
    hourCycle: 'h23',
  }).format(new Date());
  return Number(hour);
}

export function dayTint(): { color: string; alpha: number; label: string } {
  const h = saoPauloHour();
  if (h >= 19 || h < 6) return { color: '#061018', alpha: 0.34, label: 'noite' };
  if (h >= 17) return { color: '#2a1408', alpha: 0.16, label: 'entardecer' };
  return { color: '#000', alpha: 0, label: 'dia' };
}

function drawCharacter(ctx: CanvasRenderingContext2D, av: Avatar, px: number, py: number, scale: number, t: number): void {
  const helper = Boolean(av.agent.helper);
  const s = Math.max(3, Math.round(scale * (helper ? 3.1 : 4.2)));
  const bob = av.pose === 'walk' ? Math.sin(t * 9 + av.x * 3) * s : 0;
  ctx.save();
  ctx.translate(px, py + bob);
  ctx.imageSmoothingEnabled = false;
  const shirt = av.agent.shirt;
  const hair = av.agent.hair;
  const skin = av.agent.skin;
  const pxr = (col: number, row: number, ww: number, hh: number, color: string) => {
    ctx.fillStyle = color;
    ctx.fillRect(col * s, row * s, ww * s, hh * s);
  };
  if (av.pose === 'sleep') {
    ctx.translate(-6 * s, -8 * s);
    pxr(0, 3, 10, 4, shirt);
    pxr(1, 1, 6, 3, skin);
    pxr(1, 0, 6, 2, hair);
    ctx.fillStyle = '#d7ecff';
    ctx.font = `${11 * Math.max(1, scale)}px monospace`;
    ctx.fillText('z', 11 * s, -2 * s);
    ctx.restore();
    return;
  }
  const frame = av.pose === 'walk' ? Math.floor(t * 8) % 2 : 0;
  const stand = av.pose === 'present' || av.pose === 'talk';
  ctx.translate(-5 * s, stand ? -18 * s : -16 * s);
  pxr(2, 0, 6, 2, hair);
  if ((av.agent.name.length + av.agent.shirt.length) % 3 === 0) pxr(1, 0, 8, 1, hair);
  pxr(3, 2, 4, 3, skin);
  if (av.dir === 1) pxr(3, 3, 1, 1, '#111');
  else pxr(6, 3, 1, 1, '#111');
  if (av.agent.id.endsWith('9') || av.agent.hair === '#f2f2f2') pxr(3, 3, 4, 1, '#2228');
  pxr(2, 5, 6, stand ? 6 : 5, shirt);
  if (!helper && av.agent.shirt === '#f5c542') pxr(4, 5, 1, 4, '#6b4a12');
  if (helper) {
    ctx.fillStyle = '#f5c542';
    ctx.fillRect(7 * s, 5 * s, 2 * s, 2 * s);
  }
  pxr(1, 6, 1, 3, skin);
  pxr(8, 6, 1, 3, skin);
  if (av.pose === 'type') {
    pxr(1, 8, 2, 1, skin);
    pxr(7, 8, 2, 1, skin);
  }
  if (av.pose === 'read') pxr(0, 7, 3, 2, '#f4e2b0');
  if (av.pose === 'present') pxr(8, 4, 2, 4, '#f5c542');
  const leg = frame ? 1 : 0;
  pxr(3, 10, 2, 4 + (av.pose === 'walk' ? leg : 0), '#243044');
  pxr(6, 10, 2, 4 + (av.pose === 'walk' ? 1 - leg : 0), '#243044');
  ctx.restore();
}

function roundTag(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  fill: string,
  stroke: string,
  fontPx: number,
): void {
  ctx.font = `600 ${fontPx}px ui-monospace, monospace`;
  const w = ctx.measureText(text).width + fontPx;
  const h = fontPx + 8;
  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = Math.max(1, fontPx / 10);
  ctx.beginPath();
  ctx.roundRect(x - w / 2, y - h, w, h, 6);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#f7f3ea';
  ctx.textAlign = 'center';
  ctx.fillText(text, x, y - 6);
}

function drawNameTag(ctx: CanvasRenderingContext2D, av: Avatar, x: number, y: number, zoom: number, dpr: number): void {
  const fontPx = Math.max(12, Math.min(18, 15 * zoom)) * dpr;
  const text = nameTag(av.agent);
  const fill = av.agent.helper ? '#1a2740f2' : '#101820f2';
  const stroke = av.agent.helper ? '#7fd3ff' : '#f5c542';
  roundTag(ctx, text, x, y - 8 * dpr, fill, stroke, fontPx);
}

export function drawOffice(
  ctx: CanvasRenderingContext2D,
  cam: Camera,
  avatars: Avatar[],
  hoverRoom: string | null,
  t: number,
): void {
  const { scale, ox, oy } = cam.transform();
  const vw = cam.viewW * cam.dpr;
  const vh = cam.viewH * cam.dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, vw, vh);
  const sky = ctx.createLinearGradient(0, 0, 0, vh);
  sky.addColorStop(0, '#0b1520');
  sky.addColorStop(1, '#101820');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, vw, vh);

  const veto = avatars.some((a) => a.room === 'risk' && a.error);
  type Item = { z: number; draw: () => void };
  const items: Item[] = [];

  for (let ty = 0; ty < MAP_H; ty++) {
    for (let tx = 0; tx < MAP_W; tx++) {
      const room = roomAt(tx, ty);
      const wpos = tileToWorld(tx, ty);
      const edge = room && (tx === room.x || ty === room.y || tx === room.x + room.w - 1 || ty === room.y + room.h - 1);
      const door = room ? isDoor(room, tx, ty) : false;
      const z = tx + ty;
      items.push({
        z,
        draw: () => {
          let color = (tx + ty) % 2 === 0 ? '#2c343c' : '#262e36';
          if (room && !edge) {
            color = (tx + ty) % 2 === 0 ? room.floor : room.floorAlt;
            if (hoverRoom === room.id) color = room.trim + '55';
          }
          if (room && edge && !door) color = room.wall;
          if (door) color = '#8a7040';
          diamond(ctx, wpos.x, wpos.y, scale, ox, oy);
          ctx.fillStyle = color;
          ctx.fill();
          if (room && edge && !door) {
            diamond(ctx, wpos.x, wpos.y - 10, scale, ox, oy);
            ctx.fillStyle = room.trim;
            ctx.globalAlpha = 0.9;
            ctx.fill();
            ctx.globalAlpha = 1;
          }
        },
      });
    }
  }

  for (const prop of PROPS) {
    const wpos = tileToWorld(prop.x, prop.y);
    items.push({
      z: prop.x + prop.y + 0.2,
      draw: () => drawProp(ctx, prop, wpos.x, wpos.y, scale, ox, oy, t, veto),
    });
  }

  for (const room of ROOMS) {
    const d = doorOf(room);
    const wpos = tileToWorld(d.x, d.y - 0.2);
    items.push({
      z: d.x + d.y + 0.15,
      draw: () => {
        const x = wpos.x * scale + ox;
        const y = wpos.y * scale + oy - 18 * scale;
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const fontPx = Math.max(10, Math.min(13, 11 * cam.zoom)) * cam.dpr;
        ctx.font = `700 ${fontPx}px ui-monospace, monospace`;
        const label = room.plate;
        const tw = ctx.measureText(label).width + 10 * cam.dpr;
        ctx.fillStyle = '#120e08ee';
        ctx.strokeStyle = room.trim;
        ctx.lineWidth = cam.dpr;
        ctx.beginPath();
        ctx.roundRect(x - tw / 2, y - fontPx, tw, fontPx + 6 * cam.dpr, 3);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#f6edd4';
        ctx.textAlign = 'center';
        ctx.fillText(label, x, y - 2);
        ctx.restore();
      },
    });
  }

  for (const av of avatars) {
    const wpos = tileToWorld(av.x, av.y);
    items.push({
      z: av.x + av.y + 0.55,
      draw: () => {
        const feetX = wpos.x * scale + ox;
        const feetY = (wpos.y + TH * 0.72) * scale + oy;
        drawCharacter(ctx, av, feetX, feetY, scale, t);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const headY = feetY - 52 * scale;
        drawNameTag(ctx, av, feetX, headY, cam.zoom, cam.dpr);
        if (av.bubble && !av.leaving) {
          const msg = av.bubble.length > 36 ? `${av.bubble.slice(0, 34)}…` : av.bubble;
          const fontPx = Math.max(11, Math.min(14, 12 * cam.zoom)) * cam.dpr;
          roundTag(ctx, msg, feetX, headY - (22 * cam.dpr), av.error ? '#4a1020f2' : '#101820f2', av.error ? '#ff4d6a' : '#9ad7ff', fontPx);
          if (av.error) {
            ctx.fillStyle = '#ff3355';
            ctx.beginPath();
            ctx.arc(feetX + 28 * cam.dpr, headY - 40 * cam.dpr, 7 * cam.dpr, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.font = `700 ${12 * cam.dpr}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText('!', feetX + 28 * cam.dpr, headY - 36 * cam.dpr);
          }
        }
        ctx.restore();
      },
    });
  }

  items.sort((a, b) => a.z - b.z);
  for (const it of items) it.draw();

  const tint = dayTint();
  if (tint.alpha > 0) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = tint.color;
    ctx.globalAlpha = tint.alpha;
    ctx.fillRect(0, 0, vw, vh);
    ctx.restore();
  }
}

function isDoor(room: RoomDef, tx: number, ty: number): boolean {
  const d = doorOf(room);
  return ty === d.y && (tx === d.x || tx === d.x + 1);
}

function drawProp(
  ctx: CanvasRenderingContext2D,
  prop: Prop,
  wx: number,
  wy: number,
  scale: number,
  ox: number,
  oy: number,
  t: number,
  veto: boolean,
): void {
  const x = wx * scale + ox;
  const y = wy * scale + oy;
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const u = Math.max(4, 7 * scale);
  if (prop.kind === 'desk') {
    diamond(ctx, wx, wy - 4, scale, ox, oy);
    ctx.fillStyle = '#4a3420';
    ctx.fill();
  } else if (prop.kind === 'screens' || prop.kind === 'code' || prop.kind === 'whale') {
    ctx.fillStyle = '#061018';
    ctx.fillRect(x - u * 2.2, y - u * 2.4, u * 2, u * 1.5);
    ctx.fillRect(x - u * 0.1, y - u * 2.2, u * 2, u * 1.4);
    ctx.fillStyle = prop.kind === 'code' ? '#9cffb0' : prop.kind === 'whale' ? '#7fd3ff' : '#3dff9a';
    if (prop.kind === 'screens') candles(ctx, x - u * 2, y - u * 2.1, u, t);
    else if (prop.kind === 'code') {
      for (let i = 0; i < 4; i++) ctx.fillRect(x - u * 2, y - u * 2 + i * (u / 3), u * (0.6 + ((i + Math.floor(t)) % 3) * 0.3), Math.max(1, u / 6));
    } else {
      ctx.font = `${u}px sans-serif`;
      ctx.fillText('🐋', x - u * 1.6, y - u * 0.8);
      ctx.fillRect(x, y - u * 1.6, u * 0.3, u);
      ctx.fillRect(x + u * 0.5, y - u, u * 0.3, u * 0.5);
    }
  } else if (prop.kind === 'tv') {
    ctx.fillStyle = '#101820';
    ctx.fillRect(x - u * 1.6, y - u * 2, u * 3.2, u * 2);
    ctx.fillStyle = '#203040';
    ctx.fillRect(x - u * 1.3, y - u * 1.7, u * 2.6, u * 1.4);
    ctx.fillStyle = '#ffb020';
    ctx.font = `${u * 0.7}px monospace`;
    ctx.fillText('NEWS', x - u, y - u * 0.7);
  } else if (prop.kind === 'ticker') {
    ctx.fillStyle = '#120e08';
    ctx.fillRect(x - u * 3, y - u, u * 6, u * 0.7);
    ctx.fillStyle = '#f5c542';
    ctx.font = `${u * 0.55}px monospace`;
    const msg = ' BTC ETH SOL FED ETF ';
    ctx.fillText(msg.slice(Math.floor(t * 2) % 8), x - u * 2.6, y - u * 0.35);
  } else if (prop.kind === 'papers') {
    ctx.fillStyle = '#f4e2b0';
    ctx.fillRect(x - u, y - u * 0.4, u * 1.4, u);
    ctx.fillStyle = '#222';
    ctx.fillRect(x - u * 0.8, y - u * 0.1, u, 1);
  } else if (prop.kind === 'vault') {
    ctx.fillStyle = '#2a3038';
    ctx.fillRect(x - u * 1.4, y - u * 2.4, u * 2.8, u * 2.6);
    ctx.strokeStyle = veto ? '#ff3355' : '#3dff7a';
    ctx.lineWidth = 2;
    ctx.strokeRect(x - u * 1.4, y - u * 2.4, u * 2.8, u * 2.6);
    ctx.fillStyle = veto ? '#ff3355' : '#3dff7a';
    ctx.beginPath();
    ctx.arc(x, y - u * 2.8, u * 0.35, 0, Math.PI * 2);
    ctx.fill();
  } else if (prop.kind === 'table') {
    diamond(ctx, wx, wy - 2, scale, ox, oy);
    ctx.fillStyle = '#6b4a28';
    ctx.fill();
  } else if (prop.kind === 'projector') {
    ctx.fillStyle = '#e8eef8';
    ctx.fillRect(x - u * 3, y - u * 2.6, u * 6, u * 3);
    ctx.strokeStyle = '#f5c542';
    ctx.strokeRect(x - u * 3, y - u * 2.6, u * 6, u * 3);
    candles(ctx, x - u * 2, y - u * 1.6, u * 1.4, t + 2);
  } else if (prop.kind === 'shelf') {
    ctx.fillStyle = '#4a3424';
    ctx.fillRect(x - u, y - u * 2.2, u * 2, u * 2);
    ctx.fillStyle = '#c9a0ff';
    ctx.fillRect(x - u * 0.7, y - u * 1.8, u * 0.4, u * 0.7);
    ctx.fillStyle = '#f4e2b0';
    ctx.fillRect(x, y - u * 1.7, u * 0.4, u * 0.6);
  } else if (prop.kind === 'book') {
    ctx.fillStyle = '#f4e2b0';
    ctx.fillRect(x - u * 0.6, y - u * 0.3, u * 1.2, u * 0.8);
  } else if (prop.kind === 'coffee') {
    ctx.fillStyle = '#c0c6cc';
    ctx.fillRect(x - u * 0.7, y - u * 1.6, u * 1.4, u * 1.6);
    ctx.fillStyle = '#6b3a22';
    ctx.fillRect(x - u * 0.3, y - u * 0.5, u * 0.6, u * 0.4);
    ctx.fillStyle = '#d7ecff';
    ctx.globalAlpha = 0.7;
    ctx.fillRect(x, y - u * 2.2 - (t % 1) * u, u * 0.2, u * 0.4);
    ctx.globalAlpha = 1;
  } else if (prop.kind === 'plant') {
    ctx.fillStyle = '#3a6b3a';
    ctx.beginPath();
    ctx.arc(x, y - u, u * 0.7, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#6b4a28';
    ctx.fillRect(x - u * 0.25, y - u * 0.4, u * 0.5, u * 0.5);
  }
  ctx.restore();
}

function candles(ctx: CanvasRenderingContext2D, x: number, y: number, u: number, t: number): void {
  for (let i = 0; i < 5; i++) {
    const up = Math.sin(t + i) > 0;
    ctx.fillStyle = up ? '#3dff9a' : '#ff5570';
    const h = u * (0.3 + ((i * 3 + Math.floor(t)) % 4) * 0.12);
    ctx.fillRect(x + i * (u * 0.35), y - h, Math.max(1, u * 0.2), h);
  }
}

export function avatarAt(cam: Camera, avatars: Avatar[], sx: number, sy: number): Avatar | null {
  let best: Avatar | null = null;
  let bestD = 36;
  for (const av of avatars) {
    const w = tileToWorld(av.x, av.y);
    const p = cam.worldToScreen(w.x, w.y + TH * 0.2);
    const d = Math.hypot(p.x - sx, p.y - sy);
    if (d < bestD) {
      best = av;
      bestD = d;
    }
  }
  return best;
}
