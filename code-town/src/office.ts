import type { RoomId } from './agents';

/** World pixels per floor tile. Furniture is drawn in this space, several tiles wide. */
export const TILE = 40;

export const MAP_W = 26;
export const MAP_H = 16;

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
  { id: 'charts', label: 'Análise', plate: 'PAINEL DE ANÁLISE', x: 1, y: 1, w: 8, h: 6, door: 'south', floor: '#e4c89a', floorAlt: '#d7b888', rug: '#c46a4a' },
  { id: 'news', label: 'Redação', plate: 'REDAÇÃO', x: 9, y: 1, w: 6, h: 6, door: 'south', floor: '#efd3a4', floorAlt: '#e4c492', rug: '#d27b45' },
  { id: 'whales', label: 'On-chain', plate: 'BALEIAS', x: 15, y: 1, w: 5, h: 6, door: 'south', floor: '#d5e2ea', floorAlt: '#c5d5e0', rug: '#3d7ea6' },
  { id: 'risk', label: 'Risco', plate: 'RISCO', x: 20, y: 1, w: 5, h: 6, door: 'south', floor: '#e7d3d6', floorAlt: '#dcc4c8', rug: '#a33b45' },
  { id: 'code', label: 'Código', plate: 'CÓDIGO', x: 1, y: 8, w: 4, h: 7, door: 'north', floor: '#d7e0ea', floorAlt: '#c9d4e2', rug: '#3f6f86' },
  { id: 'talk', label: 'Reunião', plate: 'SALA DE REUNIÃO', x: 5, y: 8, w: 6, h: 7, door: 'north', floor: '#e9dcc6', floorAlt: '#dfcfb4', rug: '#5b4a7a' },
  { id: 'present', label: 'Ideias', plate: 'IDEIAS', x: 11, y: 8, w: 5, h: 7, door: 'north', floor: '#f2e6c8', floorAlt: '#e8d9b4', rug: '#e0a43c' },
  { id: 'library', label: 'Estudos', plate: 'SALA DE ESTUDOS', x: 16, y: 8, w: 5, h: 7, door: 'north', floor: '#ead8b8', floorAlt: '#e0cca6', rug: '#4f6b3a' },
  { id: 'coffee', label: 'Copa', plate: 'COPA', x: 21, y: 8, w: 4, h: 7, door: 'north', floor: '#f3ddc0', floorAlt: '#e8d0ae', rug: '#c47a4a' },
];

export interface Spot {
  room: RoomId;
  x: number;
  y: number;
}

const SPOTS: Record<RoomId, Spot[]> = {
  charts: [
    { room: 'charts', x: 3, y: 3 },
    { room: 'charts', x: 5, y: 3 },
    { room: 'charts', x: 7, y: 3 },
    { room: 'charts', x: 4, y: 4 },
  ],
  news: [
    { room: 'news', x: 11, y: 3 },
    { room: 'news', x: 13, y: 3 },
    { room: 'news', x: 12, y: 4 },
  ],
  whales: [
    { room: 'whales', x: 16, y: 3 },
    { room: 'whales', x: 18, y: 3 },
  ],
  risk: [
    { room: 'risk', x: 21, y: 3 },
    { room: 'risk', x: 23, y: 4 },
  ],
  code: [
    { room: 'code', x: 2, y: 11 },
    { room: 'code', x: 3, y: 11 },
    { room: 'code', x: 2, y: 12 },
  ],
  talk: [
    { room: 'talk', x: 6, y: 10 },
    { room: 'talk', x: 9, y: 10 },
    { room: 'talk', x: 6, y: 12 },
    { room: 'talk', x: 9, y: 12 },
    { room: 'talk', x: 6, y: 11 },
    { room: 'talk', x: 9, y: 11 },
  ],
  present: [
    { room: 'present', x: 12, y: 12 },
    { room: 'present', x: 14, y: 12 },
    { room: 'present', x: 13, y: 13 },
  ],
  library: [
    { room: 'library', x: 17, y: 12 },
    { room: 'library', x: 19, y: 12 },
    { room: 'library', x: 18, y: 13 },
  ],
  coffee: [
    { room: 'coffee', x: 22, y: 11 },
    { room: 'coffee', x: 23, y: 11 },
    { room: 'coffee', x: 22, y: 12 },
    { room: 'coffee', x: 23, y: 12 },
  ],
  other: [
    { room: 'other', x: 22, y: 13 },
    { room: 'other', x: 23, y: 13 },
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

export const EXIT = { x: 2, y: 7 };
