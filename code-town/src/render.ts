import type { Avatar } from './sim';
import { Camera } from './camera';
import { TH, tileToWorld, TW } from './iso';
import { MAP_H, MAP_W, ROOMS, doorOf, roomAt, type RoomDef } from './office';

const TICKER = 'BTC  ·  ETH  ·  SOL  ·  WALL ST  ·  CODE TOWN  ·  ';

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

function drawCharacter(
  ctx: CanvasRenderingContext2D,
  av: Avatar,
  px: number,
  py: number,
  scale: number,
  t: number,
): void {
  const bob = av.pose === 'walk' ? Math.sin(t * 10 + av.x) * 2 * scale : 0;
  const s = Math.max(4, Math.round(scale * 4.5));
  const sleep = av.pose === 'sleep';
  const h = sleep ? 10 : 16;
  const w = 10;
  ctx.save();
  ctx.translate(px, py + bob);
  ctx.imageSmoothingEnabled = false;
  const shirt = av.agent.shirt;
  const hair = av.agent.hair;
  const skin = av.agent.skin;
  const left = -((w * s) / 2);
  const top = -(h * s) - 6 * scale;
  const pxr = (col: number, row: number, ww: number, hh: number, color: string) => {
    ctx.fillStyle = color;
    ctx.fillRect(left + col * s, top + row * s, ww * s, hh * s);
  };
  if (sleep) {
    pxr(1, 4, 8, 5, shirt);
    pxr(1, 2, 6, 3, skin);
    pxr(1, 1, 6, 2, hair);
    ctx.fillStyle = '#d7ecff';
    ctx.font = `${12 * scale}px monospace`;
    ctx.fillText('z', 8 * scale, -18 * scale);
    ctx.restore();
    return;
  }
  const frame = av.pose === 'walk' ? (Math.floor(t * 8) % 2) : 0;
  pxr(2, 0, 6, 2, hair);
  pxr(3, 2, 4, 3, skin);
  pxr(2, 5, 6, 5, shirt);
  pxr(1, 6, 1, 3, skin);
  pxr(8, 6, 1, 3, skin);
  const leg = frame ? 1 : 0;
  pxr(3, 10, 2, 4 + leg, '#222');
  pxr(6, 10, 2, 5 - leg, '#222');
  if (av.pose === 'read') {
    pxr(1, 7, 2, 2, '#f4e2b0');
  }
  if (av.dir === 1) {
    pxr(3, 3, 1, 1, '#111');
  } else {
    pxr(5, 3, 1, 1, '#111');
  }
  ctx.restore();
}

function drawBubble(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, error: boolean): void {
  const msg = text.length > 42 ? `${text.slice(0, 40)}…` : text;
  ctx.font = '13px ui-monospace, monospace';
  const pad = 6;
  const w = ctx.measureText(msg).width + pad * 2;
  const h = 20;
  const bx = x - w / 2;
  const by = y - 58;
  ctx.fillStyle = error ? '#5a1020' : '#101820ee';
  ctx.strokeStyle = error ? '#ff4d6a' : '#f5c542';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(bx, by, w, h, 4);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = error ? '#ffd0d8' : '#f4f0e4';
  ctx.fillText(msg, bx + pad, by + 14);
  if (error) {
    ctx.fillStyle = '#ff3355';
    ctx.beginPath();
    ctx.arc(x + w / 2 - 4, by - 8, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText('!', x + w / 2 - 7, by - 4);
  }
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
  const g = ctx.createLinearGradient(0, 0, 0, vh);
  g.addColorStop(0, '#071018');
  g.addColorStop(1, '#0c1822');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, vw, vh);

  type Item = { z: number; draw: () => void };
  const items: Item[] = [];

  for (let ty = 0; ty < MAP_H; ty++) {
    for (let tx = 0; tx < MAP_W; tx++) {
      const room = roomAt(tx, ty);
      const wpos = tileToWorld(tx, ty);
      const edge = room && (tx === room.x || ty === room.y || tx === room.x + room.w - 1 || ty === room.y + room.h - 1);
      const door = room && (doorOf(room).x === tx || doorOf(room).x + 1 === tx) && doorOf(room).y === ty;
      const z = tx + ty;
      items.push({
        z,
        draw: () => {
          let color = '#1a242c';
          if ((tx + ty) % 2 === 0) color = '#141c24';
          if (room && !edge) color = (tx + ty) % 2 === 0 ? room.floor : room.floorAlt;
          if (room && edge && !door) color = room.wall;
          if (door) color = '#6b5430';
          if (hoverRoom && room?.id === hoverRoom && !edge) color = room.floorAlt;
          diamond(ctx, wpos.x, wpos.y, scale, ox, oy);
          ctx.fillStyle = color;
          ctx.fill();
          if (room && edge && !door && ty === room.y) {
            ctx.fillStyle = '#0006';
            ctx.fill();
          }
        },
      });
      if (room && !edge && isDesk(room, tx, ty)) {
        items.push({
          z: z + 0.2,
          draw: () => drawDesk(ctx, wpos.x, wpos.y, scale, ox, oy, room),
        });
      }
    }
  }

  for (const room of ROOMS) {
    const c = tileToWorld(room.x + room.w / 2, room.y + room.h / 2);
    items.push({
      z: room.x + room.y + 0.05,
      draw: () => {
        const sx = c.x * scale + ox;
        const sy = (c.y + 8) * scale + oy;
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.font = `bold ${Math.max(12, 13 * cam.zoom)}px ui-monospace, monospace`;
        ctx.textAlign = 'center';
        const label = room.label.toUpperCase();
        const lw = ctx.measureText(label).width + 12;
        ctx.fillStyle = '#071018dd';
        ctx.fillRect(sx - lw / 2, sy - 12, lw, 16);
        ctx.fillStyle = '#f5c542';
        ctx.fillText(label, sx, sy);
        ctx.restore();
      },
    });
  }

  // ticker on the north wall of the trading floor
  items.push({
    z: 3,
    draw: () => {
      const p = tileToWorld(4, 2.2);
      const s = { x: p.x * scale + ox, y: p.y * scale + oy };
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.font = `${Math.max(10, 11 * cam.zoom)}px ui-monospace, monospace`;
      ctx.fillStyle = '#39ff88';
      const shift = Math.floor(t * 12) % TICKER.length;
      const text = (TICKER + TICKER).slice(shift, shift + 28);
      ctx.fillText(text, s.x, s.y);
      ctx.restore();
    },
  });

  // world clocks in the meeting room
  items.push({
    z: 30,
    draw: () => {
      const p = tileToWorld(17, 15.6);
      const s = { x: p.x * scale + ox, y: p.y * scale + oy };
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.font = `${Math.max(10, 11 * cam.zoom)}px ui-monospace, monospace`;
      ctx.fillStyle = '#9ad7ff';
      const ny = clock('America/New_York');
      const ldn = clock('Europe/London');
      const sp = clock('America/Sao_Paulo');
      const tyo = clock('Asia/Tokyo');
      ctx.fillText(`NY ${ny}   LDN ${ldn}`, s.x, s.y);
      ctx.fillText(`SP ${sp}   TYO ${tyo}`, s.x, s.y + 14);
      ctx.restore();
    },
  });

  for (const av of avatars) {
    const wpos = tileToWorld(av.x, av.y);
    items.push({
      z: av.x + av.y + 0.5,
      draw: () => {
        const feetX = wpos.x * scale + ox;
        const feetY = (wpos.y + TH * 0.85) * scale + oy;
        drawCharacter(ctx, av, feetX, feetY, scale, t);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.font = `${Math.max(11, 11 * scale)}px ui-monospace, monospace`;
        ctx.textAlign = 'center';
        ctx.fillStyle = '#071018cc';
        const label = av.agent.name;
        const tw = ctx.measureText(label).width + 10;
        ctx.fillRect(feetX - tw / 2, feetY + 4, tw, 16);
        ctx.fillStyle = '#f6f1e4';
        ctx.fillText(label, feetX, feetY + 16);
        if (av.bubble) drawBubble(ctx, av.bubble, feetX, feetY, av.error);
        ctx.restore();
      },
    });
  }

  items.sort((a, b) => a.z - b.z);
  for (const it of items) it.draw();
}

function isDesk(room: RoomDef, tx: number, ty: number): boolean {
  if (room.id === 'trading') return ty === 5 && tx % 3 === 1 && tx > room.x + 1 && tx < room.x + room.w - 1;
  if (room.id === 'news') return ty === 3 && (tx === 24 || tx === 27);
  if (room.id === 'risk') return ty === 14 && tx === 33;
  if (room.id === 'library') return ty === 18 && (tx === 4 || tx === 8);
  if (room.id === 'meeting') return ty === 18 && tx === 19;
  if (room.id === 'coffee') return ty === 21 && tx === 34;
  if (room.id === 'other') return ty === 3 && tx === 35;
  return false;
}

function drawDesk(
  ctx: CanvasRenderingContext2D,
  wx: number,
  wy: number,
  scale: number,
  ox: number,
  oy: number,
  room: RoomDef,
): void {
  diamond(ctx, wx, wy - 6, scale, ox, oy);
  ctx.fillStyle = '#3a2c18';
  ctx.fill();
  const x = wx * scale + ox;
  const y = (wy - 10) * scale + oy;
  ctx.fillStyle = room.id === 'news' ? '#203040' : '#06140c';
  ctx.fillRect(x - 10 * scale, y - 8 * scale, 20 * scale, 12 * scale);
  ctx.fillStyle = room.id === 'risk' ? '#ff4466' : room.id === 'news' ? '#ffb020' : '#3dff9a';
  ctx.fillRect(x - 8 * scale, y - 6 * scale, 16 * scale, 8 * scale);
  if (room.id === 'trading') {
    ctx.fillStyle = '#06140c';
    ctx.font = `${8 * scale}px monospace`;
    ctx.fillStyle = '#39ff88';
    ctx.fillText('BTC', x - 8 * scale, y);
  }
}

function clock(timeZone: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date());
}

export function avatarAt(cam: Camera, avatars: Avatar[], sx: number, sy: number): Avatar | null {
  let best: Avatar | null = null;
  let bestD = 28;
  for (const av of avatars) {
    const w = tileToWorld(av.x, av.y);
    const p = cam.worldToScreen(w.x, w.y + TH * 0.4);
    const d = Math.hypot(p.x - sx, p.y - sy);
    if (d < bestD) {
      best = av;
      bestD = d;
    }
  }
  return best;
}
