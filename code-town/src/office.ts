import type { RoomId } from './agents';

/** World pixels per floor tile. Furniture is drawn in this space, several tiles wide. */
export const TILE = 36;

export const MAP_W = 34;
export const MAP_H = 20;

export interface RoomDef {
  id: RoomId;
  label: string;
  plate: string;
  x: number;
  y: number;
  w: number;
  h: number;
  door: 'north' | 'south';
  floor: string;
  floorAlt: string;
  rug: string;
}

export const ROOMS: RoomDef[] = [
  { id: 'charts', label: 'Gráficos', plate: 'GRÁFICOS', x: 1, y: 1, w: 11, h: 8, door: 'south', floor: '#e4c89a', floorAlt: '#d7b888', rug: '#c46a4a' },
  { id: 'news', label: 'Redação', plate: 'REDAÇÃO', x: 12, y: 1, w: 8, h: 8, door: 'south', floor: '#efd3a4', floorAlt: '#e4c492', rug: '#d27b45' },
  { id: 'whales', label: 'On-chain', plate: 'BALEIAS', x: 20, y: 1, w: 7, h: 8, door: 'south', floor: '#d5e2ea', floorAlt: '#c5d5e0', rug: '#3d7ea6' },
  { id: 'risk', label: 'Risco', plate: 'RISCO', x: 27, y: 1, w: 6, h: 8, door: 'south', floor: '#e7d3d6', floorAlt: '#dcc4c8', rug: '#a33b45' },
  { id: 'code', label: 'Código', plate: 'CÓDIGO', x: 1, y: 10, w: 8, h: 9, door: 'north', floor: '#d7e0ea', floorAlt: '#c9d4e2', rug: '#3f6f86' },
  { id: 'talk', label: 'Conversa', plate: 'CONVERSA', x: 9, y: 10, w: 8, h: 9, door: 'north', floor: '#f0d7b0', floorAlt: '#e6c89a', rug: '#c9844a' },
  { id: 'present', label: 'Apresentação', plate: 'APRESENTAÇÃO', x: 17, y: 10, w: 7, h: 9, door: 'north', floor: '#e7dcc8', floorAlt: '#dccfb6', rug: '#6d5b8a' },
  { id: 'library', label: 'Biblioteca', plate: 'ESTUDO', x: 24, y: 10, w: 4, h: 9, door: 'north', floor: '#ead8b8', floorAlt: '#e0cca6', rug: '#7a4e32' },
  { id: 'coffee', label: 'Copa', plate: 'COPA', x: 29, y: 10, w: 4, h: 4, door: 'north', floor: '#f3ddc0', floorAlt: '#e8d0ae', rug: '#c47a4a' },
  { id: 'other', label: 'Outros', plate: 'OUTROS', x: 29, y: 15, w: 4, h: 4, door: 'north', floor: '#d5ebe4', floorAlt: '#c6e0d8', rug: '#2f8f86' },
];

export interface Spot {
  room: RoomId;
  x: number;
  y: number;
}

const SPOTS: Record<RoomId, Spot[]> = {
  charts: [
    { room: 'charts', x: 3, y: 4 },
    { room: 'charts', x: 6, y: 4 },
    { room: 'charts', x: 9, y: 4 },
    { room: 'charts', x: 5, y: 6 },
  ],
  news: [
    { room: 'news', x: 14, y: 4 },
    { room: 'news', x: 17, y: 4 },
    { room: 'news', x: 15, y: 6 },
  ],
  whales: [
    { room: 'whales', x: 22, y: 4 },
    { room: 'whales', x: 24, y: 4 },
  ],
  risk: [
    { room: 'risk', x: 29, y: 5 },
    { room: 'risk', x: 31, y: 5 },
  ],
  code: [
    { room: 'code', x: 3, y: 13 },
    { room: 'code', x: 6, y: 13 },
    { room: 'code', x: 4, y: 16 },
  ],
  talk: [
    { room: 'talk', x: 11, y: 14 },
    { room: 'talk', x: 14, y: 14 },
    { room: 'talk', x: 11, y: 16 },
    { room: 'talk', x: 14, y: 16 },
  ],
  present: [
    { room: 'present', x: 19, y: 15 },
    { room: 'present', x: 21, y: 15 },
  ],
  library: [
    { room: 'library', x: 26, y: 14 },
    { room: 'library', x: 26, y: 16 },
  ],
  coffee: [
    { room: 'coffee', x: 30, y: 12 },
    { room: 'coffee', x: 31, y: 12 },
  ],
  other: [
    { room: 'other', x: 30, y: 16 },
    { room: 'other', x: 31, y: 17 },
    { room: 'other', x: 30, y: 17 },
  ],
};

const used = new Map<string, number>();

export function claimSpot(room: RoomId): Spot {
  const list = SPOTS[room];
  const i = used.get(room) ?? 0;
  used.set(room, i + 1);
  return list[i % list.length];
}

export function resetSpots(): void {
  used.clear();
}

export function roomAt(tx: number, ty: number): RoomDef | null {
  const x = Math.floor(tx);
  const y = Math.floor(ty);
  for (const r of ROOMS) {
    if (x >= r.x && y >= r.y && x < r.x + r.w && y < r.y + r.h) return r;
  }
  return null;
}

export function doorOf(r: RoomDef): { x: number; y: number } {
  return {
    x: r.x + Math.floor(r.w / 2) - 1,
    y: r.door === 'north' ? r.y : r.y + r.h - 1,
  };
}

export function buildBlocked(): Uint8Array {
  const cells = new Uint8Array(MAP_W * MAP_H);
  // interior void outside rooms is the hallway; outer rim is wall
  for (let x = 0; x < MAP_W; x++) {
    cells[x] = 1;
    cells[(MAP_H - 1) * MAP_W + x] = 1;
  }
  for (let y = 0; y < MAP_H; y++) {
    cells[y * MAP_W] = 1;
    cells[y * MAP_W + MAP_W - 1] = 1;
  }
  for (const r of ROOMS) {
    for (let y = r.y; y < r.y + r.h; y++) {
      for (let x = r.x; x < r.x + r.w; x++) {
        const edge = x === r.x || y === r.y || x === r.x + r.w - 1 || y === r.y + r.h - 1;
        if (edge) cells[y * MAP_W + x] = 1;
      }
    }
    const d = doorOf(r);
    cells[d.y * MAP_W + d.x] = 0;
    cells[d.y * MAP_W + d.x + 1] = 0;
  }
  return cells;
}

export function roomCenter(r: RoomDef): { x: number; y: number } {
  return { x: r.x + r.w / 2, y: r.y + r.h / 2 };
}

export function worldOf(tx: number, ty: number): { x: number; y: number } {
  return { x: (tx + 0.5) * TILE, y: (ty + 0.5) * TILE };
}

export function tileOf(wx: number, wy: number): { tx: number; ty: number } {
  return { tx: wx / TILE, ty: wy / TILE };
}

export const EXIT = { x: 2, y: 9 };
