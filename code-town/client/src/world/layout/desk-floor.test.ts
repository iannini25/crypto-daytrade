import assert from 'node:assert/strict';
import test from 'node:test';
import type { RoomTheme } from '../../art/api';
import type { TileRect } from './types';
import { assembleBuilding } from './building';
import { LOUNGE_ID } from './core';
import { CHEFE_H, CHEFE_W, CHEFE_X, CHEFE_Y, DESK_CELLS, layoutDeskRoom, RING } from './desk-floor';
import { DESK_SECTORS } from './desk-rooms';

function roomGap(a: TileRect, b: TileRect): number {
  const overlapX = a.x < b.x + b.w && b.x < a.x + a.w;
  const overlapY = a.y < b.y + b.h && b.y < a.y + a.h;
  const dx = a.x + a.w <= b.x ? b.x - (a.x + a.w) : b.x + b.w <= a.x ? a.x - (b.x + b.w) : 0;
  const dy = a.y + a.h <= b.y ? b.y - (a.y + a.h) : b.y + b.h <= a.y ? a.y - (b.y + b.h) : 0;
  if (overlapX && overlapY) return 0;
  if (overlapX) return dy;
  if (overlapY) return dx;
  return Math.min(dx, dy);
}

const theme: RoomTheme = {
  carpet: '#2f6b4f',
  carpet2: '#1d4a38',
  wall: { base: '#e7e1d6', trim: '#8d7b62', pattern: 'plain' },
  accent: '#f5c542',
  deskVariant: 'dark',
  chairVariant: 'black',
};

test('a planta põe o Chefe no centro e liga todas as mesas ao lounge', () => {
  const rooms = DESK_SECTORS.map((s, i) => {
    const layout = layoutDeskRoom(`grok:${s.id}`, 1000 + i, theme);
    assert.ok(layout, s.id);
    return layout;
  });
  assert.equal(rooms.length, DESK_CELLS.length);
  const building = assembleBuilding(8, rooms, 1);
  assert.equal(building.desk, true);
  assert.equal(building.core.some((a) => a.id === 'core:recepcao' || a.id === 'core:banheiros' || a.id === 'core:copa'), false);
  assert.ok(building.corridor.floors.length >= 4);
  assert.ok(building.corridor.walkable.length >= 4);
  const chefe = rooms.find((r) => r.id === 'grok:chefe')!;
  assert.deepEqual(chefe.rect, { x: CHEFE_X, y: CHEFE_Y, w: CHEFE_W, h: CHEFE_H });
  assert.equal(chefe.furniture.filter((f) => f.kind === 'sofa').length, 1);
  assert.equal(chefe.furniture.filter((f) => f.kind === 'desk').length, 1);
  assert.equal(chefe.furniture.filter((f) => f.kind === 'office_chair' || f.kind === 'office_chair_front').length, 1);
  assert.equal(chefe.spots.filter((s) => s.kind === 'desk').length, 1);
  assert.ok(chefe.spots.filter((s) => s.kind === 'sofa').length >= 3);
  assert.equal(chefe.floors[0]?.kind, 'carpet');
  assert.equal(chefe.walls[0]?.kind === 'face' && chefe.walls[0].style.pattern, 'marble');
  assert.ok(chefe.rect.x > 0 && chefe.rect.x + chefe.rect.w < building.rect.w);
  const looks = new Set<string>();
  for (const room of rooms) {
    const floor = room.floors[0];
    const wall = room.walls.find((w) => w.kind === 'face');
    assert.ok(floor && wall && wall.kind === 'face', room.id);
    const sig = `${floor.kind}|${floor.tint ?? ''}|${wall.style.base}|${wall.style.pattern}|${(room.screens ?? []).join('+')}`;
    assert.equal(looks.has(sig), false, sig);
    looks.add(sig);
    const gap = roomGap(chefe.rect, room.rect);
    if (room.id !== 'grok:chefe') assert.ok(gap >= RING, `${room.id} gap ${gap}`);
  }
  const lounge = building.core.find((a) => a.id === LOUNGE_ID)!;
  const rest = lounge.spots.filter((s) => s.kind === 'sofa' || s.kind === 'armchair' || s.kind === 'beanbag' || s.kind === 'bench');
  assert.ok(rest.length >= 12, `lounge seats ${rest.length}`);
  const elev = lounge.spots.find((s) => s.kind === 'elevator')!;
  const reach = building.grid.reachableFrom(elev.tx, elev.ty);
  for (const room of rooms) {
    const desk = room.spots.find((s) => s.kind === 'desk');
    assert.ok(desk, room.id);
    assert.equal(reach[desk.ty * building.grid.w + desk.tx], 1, room.id);
    if (room.id !== 'grok:chefe') {
      assert.ok(room.wallItems.some((w) => w.kind === 'tv' || w.kind === 'whiteboard'), room.id);
      assert.ok(room.furniture.some((f) => f.kind === 'desk'), room.id);
    }
  }
});
