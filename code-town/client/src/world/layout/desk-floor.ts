// Planta da mesa: o escritório do Chefe no centro, uma sala por agente em volta,
// e um lounge largo embaixo. Sem corredor, recepção, banheiro ou copa.
//
//   [ PumpFun ] [ Monitor X ] [ Trending ] [ Caçador ]
//   [ Holders ] [     Chefe (2 colunas)  ] [ Risco   ]
//   [ Estat.  ] [ Reunião   ] [ Estudos  ] [ Confer. ]
//   [ ============== Lounge ============== ]
import type { RoomTheme, WallStyle } from '../../art/api';
import { COL_W, TILE } from '../constants';
import { AreaBuilder } from './builder';
import { LOUNGE_ID } from './core';
import { DESK_SECTORS } from './desk-rooms';
import type { AreaLayout, TileRect } from './types';

export const CELL = 16;
export const CELL_H = 12;
export const LOUNGE_H = 14;
export const FLOOR_W = CELL * 4;
export const FLOOR_H = CELL_H * 3 + LOUNGE_H;
export const DESK_COLS = FLOOR_W / COL_W;

const POSTERS = ['btc', 'eth', 'candles', 'bull'] as const;
const PLANTS = ['palm', 'ficus', 'monstera', 'bonsai'] as const;

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

const R = (x: number, y: number, w = CELL, h = CELL_H): TileRect => ({ x, y, w, h });

/** Porta padrão, alinhada entre a sala de cima e a de baixo. */
const DOOR = 7;

export const DESK_CELLS: Cell[] = [
  { id: 'grok:pumpfun', rect: R(0, 0), doors: { north: [], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:monitor-x', rect: R(CELL, 0), doors: { north: [], south: [DOOR], west: true, east: true }, kind: 'trade', seats: 2 },
  { id: 'grok:trending', rect: R(CELL * 2, 0), doors: { north: [], south: [DOOR], west: true, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:cacador', rect: R(CELL * 3, 0), doors: { north: [], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
  { id: 'grok:whales', rect: R(0, CELL_H), doors: { north: [DOOR], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:chefe', rect: R(CELL, CELL_H, CELL * 2, CELL_H), doors: { north: [DOOR, CELL + DOOR], south: [DOOR, CELL + DOOR], west: true, east: true }, kind: 'chefe', seats: 1 },
  { id: 'grok:risk', rect: R(CELL * 3, CELL_H), doors: { north: [DOOR], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
  { id: 'grok:stats', rect: R(0, CELL_H * 2), doors: { north: [DOOR], south: [DOOR], west: false, east: true }, kind: 'trade', seats: 1 },
  { id: 'grok:talk', rect: R(CELL, CELL_H * 2), doors: { north: [DOOR], south: [DOOR], west: true, east: true }, kind: 'meeting', seats: 1 },
  { id: 'grok:library', rect: R(CELL * 2, CELL_H * 2), doors: { north: [DOOR], south: [DOOR], west: true, east: true }, kind: 'study', seats: 1 },
  { id: 'grok:conferencia', rect: R(CELL * 3, CELL_H * 2), doors: { north: [DOOR], south: [DOOR], west: true, east: false }, kind: 'trade', seats: 1 },
];

const CELL_BY_ID = new Map(DESK_CELLS.map((c) => [c.id, c]));

export function layoutDeskRoom(id: string, seed: number, theme: RoomTheme): AreaLayout | null {
  const cell = CELL_BY_ID.get(id);
  if (!cell) return null;
  if (cell.kind === 'chefe') return layoutChefe(cell, seed, theme);
  if (cell.kind === 'meeting') return layoutMeeting(cell, seed, theme);
  if (cell.kind === 'study') return layoutStudy(cell, seed, theme);
  return layoutTrading(cell, seed, theme);
}

export function layoutDeskLounge(): AreaLayout {
  const b = new AreaBuilder(LOUNGE_ID, 'lounge', { x: 0, y: CELL_H * 3, w: FLOOR_W, h: LOUNGE_H });
  const wall: WallStyle = { base: '#e6e2ea', trim: '#8f8aa3', pattern: 'plain' };
  b.floor('wood', 0, 0, FLOOR_W, LOUNGE_H, 401);
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
  b.area.door = { x: 7, y: CELL_H * 3, w: 2, h: 2 };

  // Entrada: dois elevadores nas pontas da face norte, fora dos vãos das salas.
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

  // Corredor livre nas colunas das portas (7–8, 23–24, 39–40, 55–56).
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
  // Papo entre quem está ocioso: só no lounge.
  for (const [i, x] of [9, 28, 44].entries()) {
    b.spot('talk', x, 3, 'right', { group: `talk:lounge:${i}`, dx: -1 });
    b.spot('talk', x + 1, 3, 'left', { group: `talk:lounge:${i}`, dx: 1 });
  }
  return b.build();
}

export function emptyCorridor(): AreaLayout {
  return {
    id: 'core:corredor',
    kind: 'corridor',
    rect: { x: 0, y: 0, w: 0, h: 0 },
    floors: [],
    rugs: [],
    walls: [],
    wallItems: [],
    furniture: [],
    spots: [],
    walkable: [],
  };
}

function shell(cell: Cell, seed: number, theme: RoomTheme, floor: 'marble' | 'wood'): AreaBuilder {
  const { rect, doors } = cell;
  const b = new AreaBuilder(cell.id, 'room', rect);
  const wall = theme.wall;
  b.floor(floor, 0, 0, rect.w, rect.h, seed);
  b.area.floorTint = theme.carpet;
  const northDoors = doors.north.map((lx) => ({ lx, w: 2 }));
  const southDoors = doors.south.map((lx) => ({ lx, w: 2 }));
  if (northDoors.length) b.face(0.5, rect.w - 1, wall, northDoors);
  else b.face(0.5, rect.w - 1, wall);
  const southStyle = cell.rect.y + cell.rect.h >= CELL_H * 3 ? { ...wall, exterior: false as const } : wall;
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
  // A placa fica fora do vão da porta (x 7–8) e fora das TVs.
  const signCx = rect.w > 20 ? 15.2 : doors.north.length ? 5.1 : 8.4;
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

function layoutTrading(cell: Cell, seed: number, theme: RoomTheme): AreaLayout {
  const b = shell(cell, seed, theme, 'marble');
  const n = seed % POSTERS.length;
  b.rug(3, 4.5, 9, 4.2, theme.carpet, seed);
  b.wall('whiteboard', cell.doors.north.length ? 2.2 : 3.4, undefined, { order: 0.6 });
  b.wall('tv', 11.3, undefined, { order: 0.5 });
  b.wall('tv', 13.7, undefined, { order: 0.51 });
  b.wall('poster', 1.3, POSTERS[n], { order: 0.48 });
  b.wall('clock', 15, undefined, { order: 0.7 });
  b.spot('whiteboard', 3, 2, 'up', { dx: 8, dy: 2 });
  // Dois monitores na mesa; a cadeira é de quem trabalha. O vão central (x 7–8) fica livre.
  const desk = b.furn('desk', 3, 6, theme.deskVariant, { order: 0.4, seat: 'S0' });
  b.seat('desk', 'office_chair', 3, 7, 'up', theme.chairVariant, { dx: TILE / 2, deskId: desk, rank: 0, side: 'S', order: 0.6 });
  const extra = b.furn('desk', 10, 6, theme.deskVariant, { order: 0.42, seat: 'S1' });
  if (cell.seats > 1) b.seat('desk', 'office_chair', 10, 7, 'up', theme.chairVariant, { dx: TILE / 2, deskId: extra, rank: 1, side: 'S', order: 0.61 });
  b.seat('stool', 'stool', 12, 8, 'up', undefined, { order: 0.66 });
  b.furn('desk_back', 3, 4, theme.deskVariant, { order: 0.36 });
  // Racks encostados na parede leste, fora da porta lateral (y 6–7).
  b.furn('binder_shelf', 14, 2, undefined, { order: 0.3 });
  b.furn('binder_shelf', 14, 3, undefined, { order: 0.31 });
  b.furn('filing_cabinet', 14, 4, undefined, { order: 0.32 });
  b.furn('filing_cabinet', 13, 9, undefined, { order: 0.33 });
  b.furn('printer', 1, 4, undefined, { order: 0.34 });
  b.furn('plant_tall', 1, 9, PLANTS[n % PLANTS.length], { order: 0.2 });
  b.furn('plant_small', 5, 9, 'fern', { order: 0.21 });
  b.furn('trash_bin', 11, 9, undefined, { order: 0.7 });
  b.furn('floor_lamp', 1, 2, undefined, { order: 0.22 });
  return b.build();
}

function layoutMeeting(cell: Cell, seed: number, theme: RoomTheme): AreaLayout {
  const b = shell(cell, seed, theme, 'marble');
  b.rug(8.5, 4.2, 6, 4.5, theme.carpet2 || theme.carpet, seed);
  b.wall('whiteboard', 3.2, undefined, { order: 0.6 });
  b.wall('tv', 11.2, undefined, { order: 0.5 });
  b.wall('tv', 13.8, undefined, { order: 0.51 });
  b.wall('poster', 1.3, 'candles', { order: 0.48 });
  b.wall('clock', 15, undefined, { order: 0.7 });
  b.spot('whiteboard', 3, 2, 'up', { dx: 8, dy: 2 });
  const desk = b.furn('desk', 2, 6, theme.deskVariant, { order: 0.4, seat: 'S0' });
  b.seat('desk', 'office_chair', 2, 7, 'up', theme.chairVariant, { dx: TILE / 2, deskId: desk, rank: 0, side: 'S', order: 0.6 });
  b.furn('meeting_table', 10, 5, undefined, { order: 0.45 });
  b.seat('stool', 'stool', 10, 4, 'down', undefined, { order: 0.65 });
  b.seat('stool', 'stool', 12, 4, 'down', undefined, { order: 0.66 });
  b.seat('stool', 'stool', 10, 7, 'up', undefined, { order: 0.67 });
  b.seat('stool', 'stool', 12, 7, 'up', undefined, { order: 0.68 });
  b.seat('stool', 'stool', 13, 5, 'left', undefined, { order: 0.69 });
  b.seat('stool', 'stool', 9, 6, 'right', undefined, { order: 0.7 });
  b.furn('binder_shelf', 14, 2, undefined, { order: 0.3 });
  b.furn('filing_cabinet', 14, 3, undefined, { order: 0.31 });
  b.furn('plant_tall', 1, 9, 'ficus', { order: 0.2 });
  b.furn('trash_bin', 14, 9, undefined, { order: 0.33 });
  return b.build();
}

function layoutStudy(cell: Cell, seed: number, theme: RoomTheme): AreaLayout {
  const b = shell(cell, seed, theme, 'wood');
  b.rug(2.5, 4.5, 8, 4, theme.carpet, seed);
  b.wall('whiteboard', 11.5, undefined, { order: 0.6 });
  b.wall('tv', 14, undefined, { order: 0.5 });
  b.wall('poster', 1.3, 'btc', { order: 0.48 });
  b.wall('clock', 8.5, undefined, { order: 0.7 });
  b.spot('whiteboard', 11, 2, 'up', { dx: 8, dy: 2 });
  b.furn('bookshelf', 1, 2, undefined, { order: 0.25 });
  b.furn('bookshelf', 3, 2, undefined, { order: 0.26 });
  b.furn('bookshelf', 11, 2, undefined, { order: 0.27 });
  const desk = b.furn('desk', 3, 6, theme.deskVariant, { order: 0.4, seat: 'S0' });
  b.seat('desk', 'office_chair', 3, 7, 'up', theme.chairVariant, { dx: TILE / 2, deskId: desk, rank: 0, side: 'S', order: 0.6 });
  b.furn('desk', 10, 6, theme.deskVariant, { order: 0.42, seat: 'S1' });
  b.seat('stool', 'stool', 12, 8, 'up', undefined, { order: 0.66 });
  b.furn('filing_cabinet', 14, 4, undefined, { order: 0.3 });
  b.furn('plant_tall', 1, 9, 'bonsai', { order: 0.2 });
  b.furn('plant_small', 14, 9, 'succulent', { order: 0.21 });
  b.furn('floor_lamp', 14, 2, undefined, { order: 0.22 });
  return b.build();
}

/** Um sofá, uma mesa, uma cadeira. O resto é decoração de mesa cripto. */
function layoutChefe(cell: Cell, seed: number, theme: RoomTheme): AreaLayout {
  const b = shell(cell, seed, theme, 'marble');
  b.rug(8, 3.4, 16, 6.2, '#1d3b2a', seed);
  b.rug(10, 4.2, 8, 3.2, theme.carpet, seed + 1);
  b.wall('tv', 4, undefined, { order: 0.5 });
  b.wall('tv', 12, undefined, { order: 0.51 });
  b.wall('tv', 18, undefined, { order: 0.52 });
  b.wall('tv', 28, undefined, { order: 0.53 });
  b.wall('poster', 1.4, 'btc', { order: 0.46 });
  b.wall('poster', 15.2, 'eth', { order: 0.47 });
  b.wall('poster', 21, 'candles', { order: 0.48 });
  b.wall('poster', 30.2, 'bull', { order: 0.49 });
  b.wall('whiteboard', 20, undefined, { order: 0.6 });
  b.wall('clock', 26, undefined, { order: 0.7 });
  b.wall('painting', 9.2, undefined, { order: 0.45 });
  b.spot('whiteboard', 19, 2, 'up', { dx: 8, dy: 2 });
  // Mesa única, uma cadeira. Os vãos das portas (x 7–8 e 23–24) ficam livres.
  const desk = b.furn('desk', 13, 6, theme.deskVariant, { order: 0.4, seat: 'S0' });
  b.seat('desk', 'office_chair', 13, 7, 'up', theme.chairVariant, { dx: TILE / 2, deskId: desk, rank: 0, side: 'S', order: 0.6 });
  b.furn('sofa', 16, 8, 'down', { order: 0.5 });
  b.furn('coffee_table', 16, 4, undefined, { order: 0.44 });
  b.furn('plant_tall', 2, 3, 'palm', { order: 0.2 });
  b.furn('plant_tall', 2, 9, 'ficus', { order: 0.21 });
  b.furn('plant_tall', 29, 3, 'monstera', { order: 0.22 });
  b.furn('plant_small', 10, 8, 'flower', { order: 0.23 });
  b.furn('plant_small', 21, 9, 'succulent', { order: 0.24 });
  b.furn('floor_lamp', 5, 8, undefined, { order: 0.25 });
  b.furn('floor_lamp', 26, 8, undefined, { order: 0.26 });
  b.furn('bookshelf', 26, 3, undefined, { order: 0.3 });
  b.furn('binder_shelf', 28, 3, undefined, { order: 0.31 });
  b.furn('filing_cabinet', 29, 8, undefined, { order: 0.32 });
  return b.build();
}

export function deskSectorIds(): string[] {
  return DESK_SECTORS.map((s) => `grok:${s.id}`);
}
