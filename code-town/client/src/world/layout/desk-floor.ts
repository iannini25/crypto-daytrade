// Planta da mesa: o escritório do Chefe no centro, um corredor em anel em volta,
// uma sala por agente do lado de fora, e um lounge largo embaixo.
//
//   [ PumpFun ] [ Monitor X ] [ Trending ] [ Caçador ]
//   [ Holders ] [== anel ==][ Chefe ][== anel ==][ Risco ]
//   [ Estat.  ] [ Reunião   ] [ Estudos  ] [ Confer. ]
//   [ ============== Lounge ============== ]
import type { FloorKind, RoomTheme, ScreenMode, WallStyle } from '../../art/api';
import { COL_W, TILE } from '../constants';
import { AreaBuilder } from './builder';
import { LOUNGE_ID } from './core';
import { CORRIDOR_ID } from './corridor';
import { DESK_SECTORS } from './desk-rooms';
import type { AreaLayout, TileRect } from './types';

export const CELL = 16;
export const CELL_H = 12;
export const RING = 2;
export const LOUNGE_H = 14;
/** Faixa do meio: salas laterais altas o bastante para fechar o anel. */
export const MID_H = CELL_H + RING * 2;
export const ROW2_Y = CELL_H + MID_H;
export const LOUNGE_Y = ROW2_Y + CELL_H;
export const FLOOR_W = CELL * 4;
export const FLOOR_H = LOUNGE_Y + LOUNGE_H;
export const DESK_COLS = FLOOR_W / COL_W;
export const CHEFE_X = CELL + RING;
export const CHEFE_Y = CELL_H + RING;
export const CHEFE_W = CELL * 2 - RING * 2;
export const CHEFE_H = CELL_H;

const POSTERS = ['btc', 'eth', 'candles', 'bull'] as const;

interface CellDoors {
  /** Portas na face norte, x local de cada vão de 2 tiles. */
  north: number[];
  south: number[];
  west: boolean;
  east: boolean;
}

interface Cell {
  id: string;
  rect: TileRect;
  doors: CellDoors;
  kind: 'trade' | 'meeting' | 'study' | 'chefe';
  /** Cadeiras de mesa (Monitor X cabe o Radar junto). */
  seats: number;
}

interface Look {
  floor: FloorKind;
  tint?: string;
  tint2?: string;
  wall: WallStyle;
  rug: string;
  desk: string;
  chair: string;
  posters: string[];
  screens: ScreenMode[];
  plant: string;
}

const R = (x: number, y: number, w = CELL, h = CELL_H): TileRect => ({ x, y, w, h });

/** Porta padrão, alinhada entre a sala de cima e a de baixo. */
const DOOR = 7;

export const DESK_CELLS: Cell[] = [
  { id: 'grok:pumpfun', rect: R(0, 0), doors: { north: [], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:monitor-x', rect: R(CELL, 0), doors: { north: [], south: [DOOR], west: true, east: true }, kind: 'trade', seats: 2 },
  { id: 'grok:trending', rect: R(CELL * 2, 0), doors: { north: [], south: [DOOR], west: true, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:cacador', rect: R(CELL * 3, 0), doors: { north: [], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
  { id: 'grok:whales', rect: R(0, CELL_H, CELL, MID_H), doors: { north: [DOOR], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  {
    id: 'grok:chefe',
    rect: R(CHEFE_X, CHEFE_Y, CHEFE_W, CHEFE_H),
    doors: { north: [13], south: [13], west: true, east: true },
    kind: 'chefe',
    seats: 1,
  },
  { id: 'grok:risk', rect: R(CELL * 3, CELL_H, CELL, MID_H), doors: { north: [DOOR], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
  { id: 'grok:stats', rect: R(0, ROW2_Y), doors: { north: [DOOR], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:talk', rect: R(CELL, ROW2_Y), doors: { north: [DOOR], south: [DOOR], west: true, east: true }, kind: 'meeting', seats: 1 },
  { id: 'grok:library', rect: R(CELL * 2, ROW2_Y), doors: { north: [DOOR], south: [DOOR], west: true, east: true }, kind: 'study', seats: 1 },
  { id: 'grok:conferencia', rect: R(CELL * 3, ROW2_Y), doors: { north: [DOOR], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
];

/** Piso, parede, telas e móveis próprios. Nenhuma sala repete o trio. */
const LOOKS: Record<string, Look> = {
  'grok:pumpfun': {
    floor: 'carpet',
    tint: '#0e3b2e',
    tint2: '#145c45',
    wall: { base: '#12382c', trim: '#2f6b4f', pattern: 'wood_panel' },
    rug: '#1f6b45',
    desk: 'wood',
    chair: 'green',
    posters: ['btc', 'bull'],
    screens: ['candles', 'browser'],
    plant: 'palm',
  },
  'grok:monitor-x': {
    floor: 'tile_check',
    wall: { base: '#16324f', trim: '#4f7ea8', pattern: 'stripes' },
    rug: '#1d4e89',
    desk: 'white',
    chair: 'blue',
    posters: ['eth'],
    screens: ['browser', 'search'],
    plant: 'ficus',
  },
  'grok:trending': {
    floor: 'wood',
    wall: { base: '#5a3b22', trim: '#c4a574', pattern: 'wood_panel' },
    rug: '#8a5a32',
    desk: 'wood',
    chair: 'black',
    posters: ['bull', 'candles'],
    screens: ['terminal', 'candles'],
    plant: 'monstera',
  },
  'grok:cacador': {
    floor: 'carpet',
    tint: '#2a1844',
    tint2: '#3d2460',
    wall: { base: '#2c1848', trim: '#8d66cf', pattern: 'stripes' },
    rug: '#4a2d78',
    desk: 'dark',
    chair: 'gray',
    posters: ['bull', 'eth'],
    screens: ['search', 'browser'],
    plant: 'monstera',
  },
  'grok:whales': {
    floor: 'marble',
    wall: { base: '#2a3038', trim: '#8a93a0', pattern: 'brick' },
    rug: '#3d4a5c',
    desk: 'dark',
    chair: 'black',
    posters: ['btc'],
    screens: ['docs', 'candles'],
    plant: 'ficus',
  },
  'grok:chefe': {
    floor: 'carpet',
    tint: '#1a1612',
    tint2: '#2c261c',
    wall: { base: '#16130f', trim: '#c6a15a', pattern: 'marble' },
    rug: '#c6a15a',
    desk: 'dark',
    chair: 'black',
    posters: ['btc', 'candles'],
    screens: ['code', 'candles', 'terminal'],
    plant: 'palm',
  },
  'grok:risk': {
    floor: 'carpet',
    tint: '#5c1a22',
    tint2: '#7a2430',
    wall: { base: '#5c2424', trim: '#c46a5a', pattern: 'stripes' },
    rug: '#8a3030',
    desk: 'wood',
    chair: 'red',
    posters: ['candles'],
    screens: ['alert', 'terminal'],
    plant: 'bonsai',
  },
  'grok:stats': {
    floor: 'tile_white',
    wall: { base: '#d7e4ea', trim: '#7fa3b5', pattern: 'tiles' },
    rug: '#8fb4c9',
    desk: 'white',
    chair: 'blue',
    posters: ['eth', 'candles'],
    screens: ['tasks', 'docs'],
    plant: 'bonsai',
  },
  'grok:talk': {
    floor: 'carpet',
    tint: '#6b4a2a',
    tint2: '#8a6240',
    wall: { base: '#4a3424', trim: '#a67c52', pattern: 'wood_panel' },
    rug: '#a87448',
    desk: 'wood',
    chair: 'gray',
    posters: ['bull'],
    screens: ['chat', 'tasks'],
    plant: 'ficus',
  },
  'grok:library': {
    floor: 'carpet',
    tint: '#243044',
    tint2: '#31445c',
    wall: { base: '#1c2836', trim: '#6d8294', pattern: 'wood_panel' },
    rug: '#3d5168',
    desk: 'dark',
    chair: 'gray',
    posters: ['btc'],
    screens: ['docs', 'search'],
    plant: 'bonsai',
  },
  'grok:conferencia': {
    floor: 'concrete',
    wall: { base: '#3e3a36', trim: '#8a8178', pattern: 'brick' },
    rug: '#5c574f',
    desk: 'dark',
    chair: 'gray',
    posters: ['candles', 'eth'],
    screens: ['terminal', 'progress'],
    plant: 'palm',
  },
};

const CELL_BY_ID = new Map(DESK_CELLS.map((c) => [c.id, c]));

export function layoutDeskRoom(id: string, seed: number, _theme: RoomTheme): AreaLayout | null {
  const cell = CELL_BY_ID.get(id);
  const look = LOOKS[id];
  if (!cell || !look) return null;
  if (cell.kind === 'chefe') return layoutChefe(cell, seed, look);
  if (cell.kind === 'meeting') return layoutMeeting(cell, seed, look);
  if (cell.kind === 'study') return layoutStudy(cell, seed, look);
  return layoutTrading(cell, seed, look);
}

export function layoutDeskLounge(): AreaLayout {
  const b = new AreaBuilder(LOUNGE_ID, 'lounge', { x: 0, y: LOUNGE_Y, w: FLOOR_W, h: LOUNGE_H });
  const wall: WallStyle = { base: '#e6e2ea', trim: '#8f8aa3', pattern: 'plain' };
  b.floor('carpet', 0, 0, FLOOR_W, LOUNGE_H, 401, '#10243a', '#1a3354');
  b.rug(2, 4.2, 18, 6.5, '#3d5c49', 402);
  b.rug(24, 4.2, 16, 6.5, '#4a6741', 403);
  b.rug(44, 4.2, 16, 5.5, '#d7c8a8', 404);
  const doors = [7, 23, 39, 55].map((lx) => ({ lx, w: 2 }));
  b.face(0.5, FLOOR_W - 1, wall, doors);
  b.south(0.5, FLOOR_W - 1, LOUNGE_H - 1, { ...wall, exterior: true });
  b.cap(0, 0, 0.5, LOUNGE_H, wall);
  b.cap(FLOOR_W - 0.5, 0, 0.5, LOUNGE_H, wall);
  b.walk(1, 2, FLOOR_W - 2, LOUNGE_H - 3);
  for (const d of doors) b.walk(d.lx, 0, d.w, 2);
  b.area.door = { x: 7, y: LOUNGE_Y, w: 2, h: 2 };

  for (const [i, cx] of [3, 61].entries()) {
    b.wall('elevator', cx, undefined, { order: 0.2 + i * 0.05 });
    const lx = Math.floor(cx - 0.5);
    b.spot('elevator', lx, 2, 'up', { x: b.px(cx), y: b.py(2) + 2, group: `elevator:${i}` });
  }
  b.wall('sign', 18, undefined, { order: 0.9 });
  b.wall('tv', 14, undefined, { order: 0.4 });
  b.wall('tv', 30, undefined, { order: 0.41 });
  b.wall('tv', 46, undefined, { order: 0.42 });
  b.wall('clock', 34, undefined, { order: 0.7 });

  const sofas = [2, 11, 16, 27, 32, 43, 49];
  sofas.forEach((x, i) => {
    const sofa = b.furn('sofa', x, 5, i % 2 === 0 ? 'down' : 'up', { order: 0.5 });
    for (let k = 0; k < 3; k++) b.seat('sofa', 'sofa', x + k, 5, i % 2 === 0 ? 'down' : 'up', i % 2 === 0 ? 'down' : 'up', { noFurniture: true, furnitureId: sofa, order: 0.55 });
  });
  for (const [i, x] of [5, 14, 20, 30, 36, 46].entries()) {
    b.seat('armchair', 'armchair', x, 8, i % 2 === 0 ? 'right' : 'left', i % 2 === 0 ? 'right' : 'left', { order: 0.6 });
  }
  const bags = ['red', 'blue', 'yellow', 'green'] as const;
  for (const [i, x] of [4, 13, 19, 29, 35, 52].entries()) b.seat('beanbag', 'beanbag', x, 10, 'up', bags[i % bags.length], { order: 0.62 });
  for (const x of [10, 26, 42]) b.furn('coffee_table', x, 7, undefined, { order: 0.45 });
  b.furn('plant_tall', 1, 3, 'monstera', { order: 0.2 });
  b.furn('plant_tall', 62, 3, 'ficus', { order: 0.21 });
  b.furn('plant_small', 21, 10, 'fern', { order: 0.22 });
  b.furn('floor_lamp', 37, 3, undefined, { order: 0.23 });
  b.furn('pingpong_table', 58, 8, undefined, { order: 0.4 });
  const ppY = b.py(9) + 5;
  b.spot('pingpong', 57, 9, 'right', { x: b.px(58) - 2, y: ppY, group: 'pingpong:lounge' });
  b.spot('pingpong', 61, 9, 'left', { x: b.px(61) + 2, y: ppY, group: 'pingpong:lounge' });
  b.furn('arcade', 1, 10, undefined, { order: 0.35 });
  b.furn('arcade', 2, 10, undefined, { order: 0.36 });
  for (const [i, x] of [9, 28, 44].entries()) {
    b.spot('talk', x, 3, 'right', { group: `talk:lounge:${i}`, dx: -1 });
    b.spot('talk', x + 1, 3, 'left', { group: `talk:lounge:${i}`, dx: 1 });
  }
  return b.build();
}

/**
 * Anel de 2 tiles em volta do escritório do Chefe. Só piso e passadeira:
 * os agentes atravessam; móvel nenhum fecha o caminho.
 */
export function layoutChefeRing(): AreaLayout {
  const x = CELL;
  const y = CELL_H;
  const w = CELL * 2;
  const h = MID_H;
  const b = new AreaBuilder(CORRIDOR_ID, 'corridor', { x, y, w, h });
  const innerY = RING;
  b.floor('concrete', 0, 0, w, RING, 701);
  b.floor('concrete', 0, h - RING, w, RING, 702);
  b.floor('concrete', 0, innerY, RING, CHEFE_H, 703);
  b.floor('concrete', w - RING, innerY, RING, CHEFE_H, 704);
  b.rug(1, 0.4, w - 2, 1.15, '#6a5344', 710);
  b.rug(1, h - 1.6, w - 2, 1.15, '#6a5344', 711);
  b.rug(0.4, innerY, 1.15, CHEFE_H, '#5c4638', 712);
  b.rug(w - 1.55, innerY, 1.15, CHEFE_H, '#5c4638', 713);
  b.walk(0, 0, w, RING);
  b.walk(0, h - RING, w, RING);
  b.walk(0, innerY, RING, CHEFE_H);
  b.walk(w - RING, innerY, RING, CHEFE_H);
  return b.build();
}

function shell(cell: Cell, seed: number, look: Look): AreaBuilder {
  const { rect, doors } = cell;
  const b = new AreaBuilder(cell.id, 'room', rect);
  const wall = look.wall;
  b.floor(look.floor, 0, 0, rect.w, rect.h, seed, look.tint, look.tint2);
  b.area.screens = look.screens;
  const northDoors = doors.north.map((lx) => ({ lx, w: 2 }));
  const southDoors = doors.south.map((lx) => ({ lx, w: 2 }));
  if (northDoors.length) b.face(0.5, rect.w - 1, wall, northDoors);
  else b.face(0.5, rect.w - 1, wall);
  const southStyle = cell.rect.y + cell.rect.h >= LOUNGE_Y ? { ...wall, exterior: false as const } : wall;
  b.south(0.5, rect.w - 1, rect.h - 1, southStyle, southDoors);
  sideCap(b, 0, rect.h, doors.west, wall);
  sideCap(b, rect.w - 0.5, rect.h, doors.east, wall);
  b.walk(1, 2, rect.w - 2, rect.h - 3);
  for (const lx of doors.north) b.walk(lx, 0, 2, 2);
  for (const lx of doors.south) b.walk(lx, rect.h - 1, 2, 1);
  if (doors.west) b.walk(0, 6, 1, 2);
  if (doors.east) b.walk(rect.w - 1, 6, 1, 2);
  const doorX = doors.south[0] ?? doors.north[0] ?? DOOR;
  const doorY = doors.south.length ? rect.y + rect.h - 1 : rect.y;
  b.area.door = { x: rect.x + doorX, y: doorY, w: 2, h: doors.south.length ? 1 : 2 };
  const signCx = cell.id === 'grok:chefe' ? 6.4 : doors.north.length ? 5.1 : 8.4;
  b.area.signId = b.wall('sign', signCx, undefined, { order: 0.95 });
  b.wall('light_switch', Math.max(1.4, doorX - 1.2), 'on', { order: 0.8 });
  b.spot('switch', Math.max(1, doorX - 2), 2, 'up', { dy: -3 });
  const p = { x: rect.x * TILE, y: rect.y * TILE, w: rect.w * TILE, h: rect.h * TILE };
  b.area.shade = { x: p.x, y: p.y, w: p.w, h: p.h };
  return b;
}

function sideCap(b: AreaBuilder, x: number, h: number, door: boolean, wall: WallStyle): void {
  if (!door) {
    b.cap(x, 0, 0.5, h, wall);
    return;
  }
  b.cap(x, 0, 0.5, 6, wall);
  b.cap(x, 8, 0.5, h - 8, wall);
}

function deskSeat(b: AreaBuilder, x: number, look: Look, rank: number): void {
  const desk = b.furn('desk', x, 6, look.desk, { order: 0.4 + rank * 0.02, seat: `S${rank}` });
  b.seat('desk', 'office_chair', x, 7, 'up', look.chair, { dx: TILE / 2, deskId: desk, rank, side: 'S', order: 0.6 + rank * 0.01 });
}

function layoutTrading(cell: Cell, seed: number, look: Look): AreaLayout {
  const b = shell(cell, seed, look);
  const id = cell.id;
  b.rug(id === 'grok:trending' || id === 'grok:risk' ? 9 : 2.2, 4.2, 6.5, 3.6, look.rug, seed);
  if (id === 'grok:whales') {
    b.wall('poster', 1.6, look.posters[0], { order: 0.46 });
    b.wall('tv', 10.2, undefined, { order: 0.5 });
    b.wall('tv', 13.4, undefined, { order: 0.51 });
    b.wall('clock', 4.2, undefined, { order: 0.7 });
    b.furn('bookshelf', 1, 3, undefined, { order: 0.25 });
    b.furn('bookshelf', 1, 4, undefined, { order: 0.26 });
    deskSeat(b, 10, look, 0);
    b.furn('filing_cabinet', 14, 3, undefined, { order: 0.32 });
    b.furn('plant_tall', 14, 9, look.plant, { order: 0.2 });
    b.furn('floor_lamp', 4, 9, undefined, { order: 0.22 });
  } else if (id === 'grok:cacador') {
    b.wall('poster', 1.4, look.posters[0], { order: 0.46 });
    b.wall('poster', 11.2, look.posters[1], { order: 0.47 });
    b.wall('tv', 13.6, undefined, { order: 0.5 });
    b.wall('clock', 4.4, undefined, { order: 0.7 });
    b.furn('bookshelf', 1, 3, undefined, { order: 0.25 });
    deskSeat(b, 4, look, 0);
    b.furn('plant_tall', 12, 3, look.plant, { order: 0.2 });
    b.furn('plant_small', 14, 4, 'flower', { order: 0.21 });
    b.furn('plant_small', 1, 9, 'fern', { order: 0.22 });
    b.furn('floor_lamp', 14, 9, undefined, { order: 0.23 });
  } else if (id === 'grok:monitor-x') {
    b.wall('poster', 1.4, 'eth', { order: 0.46 });
    b.wall('tv', 4.2, undefined, { order: 0.5 });
    b.wall('tv', 13.2, undefined, { order: 0.51 });
    b.wall('whiteboard', 10.4, undefined, { order: 0.6 });
    b.spot('whiteboard', 10, 2, 'up', { dx: 8, dy: 2 });
    deskSeat(b, 2, look, 0);
    deskSeat(b, 11, look, 1);
    b.furn('binder_shelf', 14, 3, undefined, { order: 0.3 });
    b.furn('plant_tall', 9, 9, look.plant, { order: 0.2 });
  } else if (id === 'grok:trending') {
    b.wall('poster', 1.4, 'bull', { order: 0.46 });
    b.wall('poster', 4.2, 'candles', { order: 0.47 });
    b.wall('tv', 11.4, undefined, { order: 0.5 });
    b.wall('tv', 14, undefined, { order: 0.51 });
    b.wall('clock', 8, undefined, { order: 0.7 });
    deskSeat(b, 10, look, 0);
    b.furn('desk_back', 10, 4, look.desk, { order: 0.36 });
    b.furn('plant_tall', 1, 4, look.plant, { order: 0.2 });
    b.furn('plant_small', 2, 9, 'succulent', { order: 0.21 });
    b.furn('floor_lamp', 14, 3, undefined, { order: 0.22 });
    b.furn('trash_bin', 14, 9, undefined, { order: 0.7 });
  } else if (id === 'grok:risk') {
    b.wall('poster', 1.5, 'candles', { order: 0.46 });
    b.wall('tv', 4, undefined, { order: 0.5 });
    b.wall('tv', 13.5, undefined, { order: 0.51 });
    b.wall('clock', 10.5, undefined, { order: 0.7 });
    deskSeat(b, 10, look, 0);
    b.furn('filing_cabinet', 1, 3, undefined, { order: 0.3 });
    b.furn('filing_cabinet', 2, 3, undefined, { order: 0.31 });
    b.furn('filing_cabinet', 1, 4, undefined, { order: 0.32 });
    b.furn('printer', 14, 9, undefined, { order: 0.33 });
    b.furn('plant_small', 4, 9, 'succulent', { order: 0.21 });
  } else if (id === 'grok:stats') {
    b.wall('poster', 1.4, 'eth', { order: 0.46 });
    b.wall('whiteboard', 11.2, undefined, { order: 0.6 });
    b.wall('tv', 14, undefined, { order: 0.5 });
    b.spot('whiteboard', 11, 2, 'up', { dx: 8, dy: 2 });
    deskSeat(b, 2, look, 0);
    b.furn('printer', 12, 4, undefined, { order: 0.34 });
    b.furn('filing_cabinet', 14, 3, undefined, { order: 0.32 });
    b.furn('binder_shelf', 14, 4, undefined, { order: 0.31 });
    b.furn('plant_small', 1, 9, 'fern', { order: 0.21 });
    b.furn('floor_lamp', 10, 9, undefined, { order: 0.22 });
  } else if (id === 'grok:conferencia') {
    b.wall('poster', 1.4, 'candles', { order: 0.46 });
    b.wall('poster', 12.2, 'eth', { order: 0.47 });
    b.wall('tv', 4.4, undefined, { order: 0.5 });
    b.wall('tv', 8.2, undefined, { order: 0.51 });
    b.wall('clock', 14.2, undefined, { order: 0.7 });
    deskSeat(b, 4, look, 0);
    b.furn('filing_cabinet', 12, 4, undefined, { order: 0.3 });
    b.furn('filing_cabinet', 13, 4, undefined, { order: 0.31 });
    b.furn('filing_cabinet', 14, 4, undefined, { order: 0.32 });
    b.furn('binder_shelf', 14, 8, undefined, { order: 0.33 });
    b.furn('plant_tall', 1, 9, look.plant, { order: 0.2 });
  } else {
    b.wall('poster', 1.3, look.posters[0] ?? POSTERS[seed % POSTERS.length], { order: 0.48 });
    b.wall('tv', 11.3, undefined, { order: 0.5 });
    b.wall('tv', 13.7, undefined, { order: 0.51 });
    deskSeat(b, 3, look, 0);
    b.furn('plant_tall', 1, 9, look.plant, { order: 0.2 });
  }
  if (cell.rect.h > CELL_H) {
    b.furn('plant_tall', 2, 12, look.plant, { order: 0.24 });
    b.furn('bookshelf', 12, 12, undefined, { order: 0.28 });
    b.furn('floor_lamp', 4, 13, undefined, { order: 0.29 });
  }
  return b.build();
}

function layoutMeeting(cell: Cell, seed: number, look: Look): AreaLayout {
  const b = shell(cell, seed, look);
  b.rug(8.2, 4.2, 6, 4.2, look.rug, seed);
  b.wall('whiteboard', 3.2, undefined, { order: 0.6 });
  b.wall('tv', 12.4, undefined, { order: 0.5 });
  b.wall('poster', 1.3, 'bull', { order: 0.48 });
  b.wall('clock', 15, undefined, { order: 0.7 });
  b.spot('whiteboard', 3, 2, 'up', { dx: 8, dy: 2 });
  deskSeat(b, 2, look, 0);
  b.furn('meeting_table', 10, 5, undefined, { order: 0.45 });
  b.seat('stool', 'stool', 10, 4, 'down', undefined, { order: 0.65 });
  b.seat('stool', 'stool', 12, 4, 'down', undefined, { order: 0.66 });
  b.seat('stool', 'stool', 10, 7, 'up', undefined, { order: 0.67 });
  b.seat('stool', 'stool', 12, 7, 'up', undefined, { order: 0.68 });
  b.furn('plant_tall', 1, 9, 'ficus', { order: 0.2 });
  b.furn('coffee_table', 14, 8, undefined, { order: 0.44 });
  return b.build();
}

function layoutStudy(cell: Cell, seed: number, look: Look): AreaLayout {
  const b = shell(cell, seed, look);
  b.rug(4.5, 5.2, 7, 3.2, look.rug, seed);
  b.wall('tv', 13.4, undefined, { order: 0.5 });
  b.wall('poster', 10.2, 'btc', { order: 0.48 });
  b.wall('clock', 7.2, undefined, { order: 0.7 });
  b.furn('bookshelf', 1, 2, undefined, { order: 0.25 });
  b.furn('bookshelf', 3, 2, undefined, { order: 0.26 });
  b.furn('bookshelf', 5, 2, undefined, { order: 0.27 });
  b.furn('bookshelf', 11, 3, undefined, { order: 0.28 });
  deskSeat(b, 4, look, 0);
  b.furn('plant_tall', 14, 8, 'bonsai', { order: 0.2 });
  b.furn('plant_small', 1, 9, 'succulent', { order: 0.21 });
  b.furn('floor_lamp', 14, 3, undefined, { order: 0.22 });
  return b.build();
}

/** Escritório escuro: mesa executiva, um sofá com lugares, ouro e quadros. */
function layoutChefe(cell: Cell, seed: number, look: Look): AreaLayout {
  const b = shell(cell, seed, look);
  b.rug(6, 3.2, 16, 6.4, '#3a2e1a', seed);
  b.rug(9, 4.2, 10, 3.4, look.rug, seed + 1);
  b.wall('tv', 3.2, undefined, { order: 0.5 });
  b.wall('tv', 9.2, undefined, { order: 0.51 });
  b.wall('tv', 19.4, undefined, { order: 0.52 });
  b.wall('tv', 24.6, undefined, { order: 0.53 });
  b.wall('poster', 1.6, 'btc', { order: 0.46 });
  b.wall('poster', 17.2, 'candles', { order: 0.48 });
  b.wall('painting', 21.6, undefined, { order: 0.45 });
  b.wall('painting', 26.2, undefined, { order: 0.44 });
  b.wall('clock', 22.4, undefined, { order: 0.7 });
  const desk = b.furn('desk', 16, 5, 'dark', { order: 0.4, seat: 'S0' });
  b.seat('desk', 'office_chair', 16, 6, 'up', 'black', { dx: TILE / 2, deskId: desk, rank: 0, side: 'S', order: 0.6 });
  const sofa = b.furn('sofa', 18, 8, 'up', { order: 0.5 });
  for (let k = 0; k < 3; k++) b.seat('sofa', 'sofa', 18 + k, 8, 'up', 'up', { noFurniture: true, furnitureId: sofa, order: 0.55 });
  b.furn('coffee_table', 18, 7, undefined, { order: 0.44 });
  b.furn('plant_tall', 1, 3, 'palm', { order: 0.2 });
  b.furn('plant_tall', 1, 9, 'ficus', { order: 0.21 });
  b.furn('plant_tall', 26, 9, 'monstera', { order: 0.22 });
  b.furn('plant_small', 10, 8, 'flower', { order: 0.23 });
  b.furn('floor_lamp', 4, 8, undefined, { order: 0.25 });
  b.furn('floor_lamp', 24, 8, undefined, { order: 0.26 });
  b.furn('bookshelf', 24, 3, undefined, { order: 0.3 });
  b.furn('binder_shelf', 26, 4, undefined, { order: 0.31 });
  return b.build();
}

export function deskSectorIds(): string[] {
  return DESK_SECTORS.map((s) => `grok:${s.id}`);
}
