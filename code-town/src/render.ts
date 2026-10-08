import { nameTag } from './agents';
import { Camera } from './camera';
import { MAP_H, MAP_W, ROOMS, TILE, doorOf, roomAt, worldOf, type RoomDef } from './office';
import { activityIcon } from './routing';
import type { Avatar } from './sim';

const BUBBLE_MS = 20_000;

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

function shadow(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number): void {
  ctx.save();
  ctx.fillStyle = 'rgba(70, 42, 24, 0.18)';
  ctx.beginPath();
  ctx.ellipse(x + w / 2, y + h - 2, w * 0.46, Math.max(4, h * 0.12), 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function desk(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, screens: string[]): void {
  shadow(ctx, x, y, w, 28);
  ctx.fillStyle = '#8a5a32';
  roundRect(ctx, x, y + 10, w, 22, 4);
  ctx.fill();
  ctx.fillStyle = '#c4894f';
  roundRect(ctx, x + 2, y + 8, w - 4, 16, 4);
  ctx.fill();
  const sw = (w - 16) / screens.length;
  screens.forEach((color, i) => {
    const sx = x + 6 + i * sw;
    ctx.fillStyle = '#1b2430';
    roundRect(ctx, sx, y - 16, sw - 4, 22, 3);
    ctx.fill();
    ctx.fillStyle = color;
    roundRect(ctx, sx + 2, y - 13, sw - 8, 16, 2);
    ctx.fill();
    ctx.fillStyle = color === '#163024' ? '#3dff9a' : '#ffd56a';
    for (let k = 0; k < 4; k++) {
      const bh = 4 + ((k * 3) % 7);
      ctx.fillRect(sx + 4 + k * 4, y - 4 - bh, 3, bh);
    }
  });
}

function chair(ctx: CanvasRenderingContext2D, x: number, y: number, color: string): void {
  shadow(ctx, x, y, 16, 16);
  ctx.fillStyle = color;
  roundRect(ctx, x, y, 16, 14, 4);
  ctx.fill();
  ctx.fillStyle = '#f4e2c8';
  roundRect(ctx, x + 3, y + 3, 10, 6, 3);
  ctx.fill();
}

function plant(ctx: CanvasRenderingContext2D, x: number, y: number): void {
  shadow(ctx, x, y + 6, 16, 12);
  ctx.fillStyle = '#c47a45';
  roundRect(ctx, x + 4, y + 10, 8, 8, 2);
  ctx.fill();
  ctx.fillStyle = '#3e8f4a';
  ctx.beginPath();
  ctx.arc(x + 8, y + 8, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#67c56b';
  ctx.beginPath();
  ctx.arc(x + 5, y + 6, 4, 0, Math.PI * 2);
  ctx.fill();
}

function lamp(ctx: CanvasRenderingContext2D, x: number, y: number): void {
  ctx.fillStyle = 'rgba(255, 214, 120, 0.35)';
  ctx.beginPath();
  ctx.ellipse(x + 6, y + 16, 14, 6, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#f0d78a';
  ctx.beginPath();
  ctx.moveTo(x + 2, y + 8);
  ctx.lineTo(x + 10, y + 8);
  ctx.lineTo(x + 8, y);
  ctx.lineTo(x + 4, y);
  ctx.fill();
  ctx.fillStyle = '#6b4a2a';
  ctx.fillRect(x + 5, y + 8, 2, 8);
}

function shelf(ctx: CanvasRenderingContext2D, x: number, y: number, h: number): void {
  shadow(ctx, x, y, 18, h);
  ctx.fillStyle = '#7a4e32';
  roundRect(ctx, x, y, 18, h, 3);
  ctx.fill();
  const colors = ['#e25b5b', '#f0c14a', '#5aa6e6', '#67c56b', '#c9a0ff', '#f4e2c8'];
  for (let row = 0; row < 3; row++) {
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = colors[(row + i) % colors.length];
      ctx.fillRect(x + 2 + i * 4, y + 4 + row * (h / 3), 3, h / 3 - 6);
    }
  }
}

function drawRoomFurniture(ctx: CanvasRenderingContext2D, room: RoomDef, veto: boolean): void {
  const x = room.x * TILE;
  const y = room.y * TILE;
  const w = room.w * TILE;
  const h = room.h * TILE;
  // rug in the middle of the room
  ctx.fillStyle = room.rug;
  roundRect(ctx, x + TILE * 1.2, y + TILE * 1.6, w - TILE * 2.4, h - TILE * 3.1, 10);
  ctx.fill();
  ctx.globalAlpha = 0.25;
  ctx.fillStyle = '#fff';
  roundRect(ctx, x + TILE * 1.4, y + TILE * 1.8, w - TILE * 2.8, 8, 4);
  ctx.fill();
  ctx.globalAlpha = 1;

  if (room.id === 'charts') {
    desk(ctx, x + 28, y + 36, 92, ['#163024', '#163024']);
    desk(ctx, x + 140, y + 36, 92, ['#163024', '#102040']);
    desk(ctx, x + 250, y + 36, 100, ['#163024', '#163024', '#102040']);
    chair(ctx, x + 60, y + 78, '#3d6b8a');
    chair(ctx, x + 172, y + 78, '#c46a4a');
    chair(ctx, x + 286, y + 78, '#3e8f4a');
    plant(ctx, x + w - 36, y + h - 48);
    lamp(ctx, x + 18, y + 28);
  } else if (room.id === 'news') {
    ctx.fillStyle = '#1c2430';
    roundRect(ctx, x + 24, y + 28, w - 48, 48, 6);
    ctx.fill();
    ctx.fillStyle = '#203040';
    roundRect(ctx, x + 30, y + 34, (w - 70) / 3, 34, 3);
    ctx.fill();
    roundRect(ctx, x + 40 + (w - 70) / 3, y + 34, (w - 70) / 3, 34, 3);
    ctx.fill();
    roundRect(ctx, x + 50 + (2 * (w - 70)) / 3, y + 34, (w - 70) / 3, 34, 3);
    ctx.fill();
    ctx.fillStyle = '#8d1d2c';
    roundRect(ctx, x + 24, y + 78, w - 48, 14, 3);
    ctx.fill();
    ctx.fillStyle = '#ffd0d6';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('BTC  ETH  SOL  FED  ETF', x + 32, y + 89);
    desk(ctx, x + 40, y + 110, 80, ['#3a2414']);
    chair(ctx, x + 64, y + 150, '#d27b45');
    plant(ctx, x + w - 34, y + 110);
  } else if (room.id === 'whales') {
    desk(ctx, x + 28, y + 40, 86, ['#0e2a3a']);
    desk(ctx, x + 130, y + 40, 86, ['#0e2a3a']);
    ctx.font = '18px sans-serif';
    ctx.fillText('🐋', x + 58, y + 36);
    ctx.fillText('🐋', x + 160, y + 36);
    chair(ctx, x + 56, y + 82, '#3d7ea6');
    chair(ctx, x + 158, y + 82, '#3d7ea6');
    plant(ctx, x + w - 32, y + h - 46);
  } else if (room.id === 'risk') {
    ctx.fillStyle = '#8d97a3';
    roundRect(ctx, x + w / 2 - 28, y + 28, 56, 70, 6);
    ctx.fill();
    ctx.strokeStyle = '#5c6670';
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = veto ? '#ff3355' : '#3dce6e';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 46, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#d9dee6';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 70, 6, 0, Math.PI * 2);
    ctx.fill();
    desk(ctx, x + 18, y + 120, 70, ['#3a1820']);
    chair(ctx, x + 40, y + 158, '#a33b45');
  } else if (room.id === 'code') {
    desk(ctx, x + 22, y + 36, 88, ['#102418']);
    desk(ctx, x + 130, y + 36, 88, ['#102418']);
    ctx.fillStyle = '#9cffb0';
    ctx.font = '10px ui-monospace, monospace';
    ctx.fillText('fn()', x + 36, y + 28);
    ctx.fillText('{ }', x + 150, y + 28);
    chair(ctx, x + 50, y + 78, '#3f6f86');
    chair(ctx, x + 158, y + 78, '#3f6f86');
    // server rack
    ctx.fillStyle = '#2c3644';
    roundRect(ctx, x + 22, y + h - 70, 28, 48, 3);
    ctx.fill();
    for (let i = 0; i < 4; i++) {
      ctx.fillStyle = i % 2 ? '#3dce6e' : '#f0c14a';
      ctx.fillRect(x + 28, y + h - 62 + i * 10, 8, 3);
    }
    plant(ctx, x + w - 36, y + 40);
    lamp(ctx, x + w - 28, y + h - 60);
  } else if (room.id === 'talk') {
    shadow(ctx, x + w / 2 - 36, y + h / 2 - 10, 72, 48);
    ctx.fillStyle = '#a86838';
    ctx.beginPath();
    ctx.ellipse(x + w / 2, y + h / 2 + 10, 40, 26, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#e2b072';
    ctx.beginPath();
    ctx.ellipse(x + w / 2, y + h / 2 + 6, 32, 18, 0, 0, Math.PI * 2);
    ctx.fill();
    chair(ctx, x + w / 2 - 46, y + h / 2 - 8, '#c46a4a');
    chair(ctx, x + w / 2 + 28, y + h / 2 - 8, '#3d6b8a');
    chair(ctx, x + w / 2 - 10, y + h / 2 + 28, '#3e8f4a');
    chair(ctx, x + w / 2 - 10, y + h / 2 - 36, '#6d5b8a');
    plant(ctx, x + 16, y + 28);
    lamp(ctx, x + w - 28, y + 28);
  } else if (room.id === 'present') {
    ctx.fillStyle = '#f7f4ee';
    roundRect(ctx, x + 20, y + 26, w - 40, 58, 4);
    ctx.fill();
    ctx.strokeStyle = '#6d5b8a';
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = '#3dce6e';
    ctx.beginPath();
    ctx.moveTo(x + 36, y + 68);
    ctx.lineTo(x + 56, y + 48);
    ctx.lineTo(x + 74, y + 58);
    ctx.lineTo(x + 96, y + 36);
    ctx.lineTo(x + 120, y + 50);
    ctx.strokeStyle = '#3d6b8a';
    ctx.stroke();
    desk(ctx, x + 28, y + h - 78, 70, ['#241c30']);
    chair(ctx, x + 48, y + h - 46, '#6d5b8a');
    lamp(ctx, x + w - 30, y + h - 70);
  } else if (room.id === 'library') {
    shelf(ctx, x + 14, y + 22, 70);
    shelf(ctx, x + 36, y + 22, 70);
    shelf(ctx, x + 58, y + 22, 70);
    desk(ctx, x + 22, y + h - 80, 64, ['#3a2414']);
    chair(ctx, x + 42, y + h - 48, '#7a4e32');
    plant(ctx, x + w - 28, y + h - 48);
  } else if (room.id === 'coffee') {
    ctx.fillStyle = '#d7dde2';
    roundRect(ctx, x + 12, y + 22, 26, 32, 4);
    ctx.fill();
    ctx.fillStyle = '#6b3a22';
    ctx.fillRect(x + 18, y + 40, 10, 6);
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.fillRect(x + 28, y + 16, 3, 8);
    ctx.fillStyle = '#c47a4a';
    roundRect(ctx, x + 46, y + 36, 36, 16, 6);
    ctx.fill();
    plant(ctx, x + 14, y + 70);
    lamp(ctx, x + w - 24, y + 24);
  } else {
    desk(ctx, x + 16, y + 28, 60, ['#14302c']);
    chair(ctx, x + 34, y + 66, '#2f8f86');
    plant(ctx, x + 16, y + 78);
  }
}

function drawCharacter(ctx: CanvasRenderingContext2D, av: Avatar, x: number, y: number, t: number): void {
  const helper = Boolean(av.agent.helper);
  const s = helper ? 2.1 : 2.7;
  const bob = av.pose === 'walk' ? Math.sin(t * 9 + av.x) * 1.5 : 0;
  const sit = av.pose !== 'walk' && av.pose !== 'sleep';
  ctx.save();
  ctx.translate(x, y + bob);
  shadow(ctx, -8 * s, 2, 16 * s, 8);
  const px = (col: number, row: number, w: number, h: number, color: string) => {
    ctx.fillStyle = color;
    ctx.fillRect((col - 6) * s, (row - 16) * s, w * s, h * s);
  };
  if (av.pose === 'sleep') {
    px(1, 8, 10, 5, av.agent.shirt);
    px(2, 6, 6, 3, av.agent.skin);
    px(2, 5, 6, 2, av.agent.hair);
    ctx.fillStyle = '#7aa2c4';
    ctx.font = '12px monospace';
    ctx.fillText('z', 8, -8);
    ctx.restore();
    return;
  }
  const frame = av.pose === 'walk' ? Math.floor(t * 8) % 2 : 0;
  px(3, 2, 6, 3, av.agent.hair);
  px(4, 5, 4, 3, av.agent.skin);
  px(av.dir === 1 ? 4 : 6, 6, 1, 1, '#222');
  px(3, 8, 6, sit ? 4 : 5, av.agent.shirt);
  if (!helper && av.agent.tag === 'Chefe') px(5, 8, 1, 4, '#6b4a12');
  if (helper) px(8, 8, 2, 2, '#f5c542');
  px(2, 9, 1, 3, av.agent.skin);
  px(9, 9, 1, 3, av.agent.skin);
  if (!sit) {
    px(4, 13, 2, 4 + frame, '#2c3444');
    px(7, 13, 2, 5 - frame, '#2c3444');
  }
  ctx.restore();
}

interface Tag {
  x: number;
  y: number;
  w: number;
  h: number;
  text: string;
  sub: string;
  helper: boolean;
  error: boolean;
}

function layoutTags(tags: Tag[]): void {
  tags.sort((a, b) => a.y - b.y || a.x - b.x);
  for (let pass = 0; pass < 8; pass++) {
    for (let i = 0; i < tags.length; i++) {
      for (let j = 0; j < i; j++) {
        const a = tags[i];
        const b = tags[j];
        const overlap = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
        if (!overlap) continue;
        if (a.x >= b.x) a.x = b.x + b.w + 4;
        else a.y = b.y + b.h + 2;
      }
    }
  }
}

export function drawOffice(ctx: CanvasRenderingContext2D, cam: Camera, avatars: Avatar[], hover: string | null, t: number): void {
  const { scale, ox, oy } = cam.transform();
  const vw = cam.viewW * cam.dpr;
  const vh = cam.viewH * cam.dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, vw, vh);
  ctx.fillStyle = '#1a120e';
  ctx.fillRect(0, 0, vw, vh);

  ctx.setTransform(scale, 0, 0, scale, ox, oy);
  ctx.imageSmoothingEnabled = false;

  // hallway floor
  for (let ty = 0; ty < MAP_H; ty++) {
    for (let tx = 0; tx < MAP_W; tx++) {
      const room = roomAt(tx, ty);
      const edge = room && (tx === room.x || ty === room.y || tx === room.x + room.w - 1 || ty === room.y + room.h - 1);
      const door = room ? isDoor(room, tx, ty) : false;
      const px = tx * TILE;
      const py = ty * TILE;
      if (!room) {
        ctx.fillStyle = (tx + ty) % 2 ? '#c4a574' : '#b99564';
      } else if (edge && !door) {
        ctx.fillStyle = '#e7edf2';
      } else if (door) {
        ctx.fillStyle = '#f3e2c4';
      } else {
        ctx.fillStyle = (tx + ty) % 2 ? room.floor : room.floorAlt;
        if (hover === room.id) ctx.fillStyle = room.floor;
      }
      ctx.fillRect(px, py, TILE + 0.5, TILE + 0.5);
      if (room && edge && !door) {
        ctx.fillStyle = '#b7c0ca';
        ctx.fillRect(px, py + TILE - 7, TILE + 0.5, 7);
        ctx.fillStyle = '#8e98a3';
        ctx.fillRect(px, py, TILE + 0.5, 3);
      }
    }
  }

  const veto = avatars.some((a) => a.room === 'risk' && a.error);
  for (const room of ROOMS) drawRoomFurniture(ctx, room, veto);

  for (const room of ROOMS) {
    const d = doorOf(room);
    ctx.fillStyle = '#2a241c';
    ctx.font = 'bold 11px ui-monospace, monospace';
    ctx.textAlign = 'center';
    const label = room.plate;
    const tw = ctx.measureText(label).width + 10;
    const lx = (d.x + 1) * TILE;
    const ly = d.y * TILE + (room.door === 'south' ? -4 : TILE + 2);
    roundRect(ctx, lx - tw / 2, ly - 12, tw, 14, 6);
    ctx.fillStyle = '#fffaf3';
    ctx.fill();
    ctx.fillStyle = '#3a2a1c';
    ctx.fillText(label, lx, ly - 1);
  }

  const order = [...avatars].sort((a, b) => a.y - b.y);
  for (const av of order) {
    const p = worldOf(av.x, av.y);
    drawCharacter(ctx, av, p.x, p.y, t);
  }

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const tags: Tag[] = [];
  const fontPx = Math.max(12, Math.min(15, 13 * cam.zoom)) * cam.dpr;
  ctx.font = `600 ${fontPx}px ui-monospace, monospace`;
  const now = Date.now();
  for (const av of avatars) {
    const p = worldOf(av.x, av.y);
    const s = cam.worldToScreen(p.x, p.y - 18);
    const ev = av.events[0];
    const icon = ev ? activityIcon(ev.kind, ev.summary) : '☕';
    const fresh = ev && now - Date.parse(ev.created_at) < BUBBLE_MS && !av.leaving;
    const text = `${icon}  ${nameTag(av.agent)}`;
    const sub = fresh ? (av.bubble.length > 42 ? `${av.bubble.slice(0, 40)}…` : av.bubble) : '';
    const w = Math.max(ctx.measureText(text).width, sub ? ctx.measureText(sub).width * 0.92 : 0) + fontPx * 1.4;
    const h = (sub ? fontPx * 2.3 : fontPx * 1.35) + 8;
    tags.push({
      x: s.x - w / 2,
      y: s.y - h - 8 * cam.dpr,
      w,
      h,
      text,
      sub,
      helper: Boolean(av.agent.helper),
      error: av.error && Boolean(fresh),
    });
  }
  layoutTags(tags);
  for (const tag of tags) {
    ctx.fillStyle = 'rgba(70,42,24,0.18)';
    roundRect(ctx, tag.x + 2, tag.y + 3, tag.w, tag.h, 12);
    ctx.fill();
    ctx.fillStyle = tag.error ? '#fff1f3' : '#fffaf3';
    ctx.strokeStyle = tag.helper ? '#3d7ea6' : tag.error ? '#e23b4a' : '#e2c9a4';
    ctx.lineWidth = Math.max(1, cam.dpr);
    roundRect(ctx, tag.x, tag.y, tag.w, tag.h, 12);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#2c241c';
    ctx.textAlign = 'center';
    ctx.font = `600 ${fontPx}px ui-monospace, monospace`;
    ctx.fillText(tag.text, tag.x + tag.w / 2, tag.y + fontPx + 2);
    if (tag.sub) {
      ctx.font = `${Math.max(10, fontPx * 0.78)}px ui-monospace, monospace`;
      ctx.fillStyle = '#6a5344';
      ctx.fillText(tag.sub, tag.x + tag.w / 2, tag.y + fontPx * 2 + 2);
    }
  }
}

function isDoor(room: RoomDef, tx: number, ty: number): boolean {
  const d = doorOf(room);
  return ty === d.y && (tx === d.x || tx === d.x + 1);
}

export function avatarAt(cam: Camera, avatars: Avatar[], sx: number, sy: number): Avatar | null {
  let best: Avatar | null = null;
  let bestD = 28;
  for (const av of avatars) {
    const p = worldOf(av.x, av.y);
    const s = cam.worldToScreen(p.x, p.y);
    const d = Math.hypot(s.x - sx, s.y - sy);
    if (d < bestD) {
      best = av;
      bestD = d;
    }
  }
  return best;
}
