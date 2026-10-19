import assert from 'node:assert/strict';
import test from 'node:test';
import type { RoomTheme } from '../../art/api';
import { assembleBuilding } from './building';
import { LOUNGE_ID } from './core';
import { DESK_CELLS, layoutDeskRoom } from './desk-floor';
import { DESK_SECTORS } from './desk-rooms';

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
  assert.equal(building.corridor.floors.length, 0);
  const chefe = rooms.find((r) => r.id === 'grok:chefe')!;
  assert.equal(chefe.furniture.filter((f) => f.kind === 'sofa').length, 1);
  assert.equal(chefe.furniture.filter((f) => f.kind === 'desk').length, 1);
  assert.equal(chefe.furniture.filter((f) => f.kind === 'office_chair' || f.kind === 'office_chair_front').length, 1);
  assert.equal(chefe.spots.filter((s) => s.kind === 'desk').length, 1);
  assert.ok(chefe.rect.x > 0 && chefe.rect.x + chefe.rect.w < building.rect.w);
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
