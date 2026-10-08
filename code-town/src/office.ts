import type { RoomId } from './agents';

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
  wall: string;
  trim: string;
}

export const MAP_W = 54;
export const MAP_H = 36;

/** Open corridor between the north row and the south row. */
export const HALL_Y = 16;

export const ROOMS: RoomDef[] = [
  { id: 'charts', label: 'Gráficos', plate: 'SALA DE GRÁFICOS', x: 1, y: 1, w: 16, h: 15, door: 'south', floor: '#163528', floorAlt: '#122c22', wall: '#0c2418', trim: '#3ecf8e' },
  { id: 'news', label: 'Redação', plate: 'REDAÇÃO', x: 18, y: 1, w: 12, h: 15, door: 'south', floor: '#3a2c18', floorAlt: '#2e2414', wall: '#24180e', trim: '#f0a050' },
  { id: 'whales', label: 'On-chain', plate: 'BALEIAS', x: 31, y: 1, w: 12, h: 15, door: 'south', floor: '#143044', floorAlt: '#102838', wall: '#0c2030', trim: '#7fd3ff' },
  { id: 'risk', label: 'Risco', plate: 'SALA DE RISCO', x: 44, y: 1, w: 9, h: 15, door: 'south', floor: '#3a1822', floorAlt: '#2c121a', wall: '#240e16', trim: '#ff5570' },
  { id: 'code', label: 'Código', plate: 'SALA DE CÓDIGO', x: 1, y: 18, w: 12, h: 16, door: 'north', floor: '#1a2430', floorAlt: '#141c28', wall: '#101820', trim: '#8fd3c8' },
  { id: 'talk', label: 'Conversa', plate: 'MESA DE CONVERSA', x: 14, y: 18, w: 10, h: 16, door: 'north', floor: '#3a2e22', floorAlt: '#2e241c', wall: '#241c14', trim: '#e8d5a3' },
  { id: 'present', label: 'Apresentação', plate: 'APRESENTAÇÃO', x: 25, y: 18, w: 12, h: 16, door: 'north', floor: '#1c2038', floorAlt: '#161a30', wall: '#121628', trim: '#f5c542' },
  { id: 'library', label: 'Biblioteca', plate: 'ESTUDO', x: 38, y: 18, w: 8, h: 16, door: 'north', floor: '#2a1c38', floorAlt: '#221430', wall: '#1a1028', trim: '#c9a0ff' },
  { id: 'coffee', label: 'Copa', plate: 'COPA', x: 47, y: 18, w: 6, h: 8, door: 'north', floor: '#3a301c', floorAlt: '#302814', wall: '#241c10', trim: '#d4a056' },
  { id: 'other', label: 'Outros', plate: 'OUTROS', x: 47, y: 27, w: 6, h: 7, door: 'north', floor: '#163038', floorAlt: '#10262c', wall: '#0c2026', trim: '#46d6c2' },
];

export type PropKind =
  | 'desk'
  | 'screens'
  | 'tv'
  | 'ticker'
  | 'papers'
  | 'whale'
  | 'vault'
  | 'table'
  | 'code'
  | 'projector'
  | 'shelf'
  | 'book'
  | 'coffee'
  | 'plant';

export interface Prop {
  x: number;
  y: number;
  kind: PropKind;
  room: RoomId;
}

export const PROPS: Prop[] = [
  { room: 'charts', x: 4, y: 4, kind: 'screens' },
  { room: 'charts', x: 4, y: 5, kind: 'desk' },
  { room: 'charts', x: 8, y: 4, kind: 'screens' },
  { room: 'charts', x: 8, y: 5, kind: 'desk' },
  { room: 'charts', x: 12, y: 4, kind: 'screens' },
  { room: 'charts', x: 12, y: 5, kind: 'desk' },
  { room: 'charts', x: 6, y: 10, kind: 'screens' },
  { room: 'charts', x: 6, y: 11, kind: 'desk' },
  { room: 'charts', x: 14, y: 12, kind: 'plant' },
  { room: 'news', x: 21, y: 3, kind: 'tv' },
  { room: 'news', x: 24, y: 3, kind: 'tv' },
  { room: 'news', x: 27, y: 3, kind: 'tv' },
  { room: 'news', x: 22, y: 6, kind: 'ticker' },
  { room: 'news', x: 25, y: 8, kind: 'desk' },
  { room: 'news', x: 25, y: 9, kind: 'papers' },
  { room: 'news', x: 21, y: 11, kind: 'papers' },
  { room: 'whales', x: 34, y: 4, kind: 'whale' },
  { room: 'whales', x: 38, y: 4, kind: 'whale' },
  { room: 'whales', x: 34, y: 5, kind: 'desk' },
  { room: 'whales', x: 38, y: 5, kind: 'desk' },
  { room: 'whales', x: 36, y: 10, kind: 'screens' },
  { room: 'risk', x: 48, y: 4, kind: 'vault' },
  { room: 'risk', x: 46, y: 8, kind: 'desk' },
  { room: 'risk', x: 46, y: 7, kind: 'screens' },
  { room: 'code', x: 4, y: 22, kind: 'code' },
  { room: 'code', x: 4, y: 23, kind: 'desk' },
  { room: 'code', x: 8, y: 22, kind: 'code' },
  { room: 'code', x: 8, y: 23, kind: 'desk' },
  { room: 'code', x: 6, y: 28, kind: 'code' },
  { room: 'code', x: 6, y: 29, kind: 'desk' },
  { room: 'talk', x: 18, y: 24, kind: 'table' },
  { room: 'talk', x: 19, y: 25, kind: 'table' },
  { room: 'talk', x: 17, y: 25, kind: 'table' },
  { room: 'talk', x: 18, y: 26, kind: 'table' },
  { room: 'present', x: 30, y: 21, kind: 'projector' },
  { room: 'present', x: 28, y: 28, kind: 'desk' },
  { room: 'present', x: 32, y: 28, kind: 'desk' },
  { room: 'library', x: 40, y: 20, kind: 'shelf' },
  { room: 'library', x: 42, y: 20, kind: 'shelf' },
  { room: 'library', x: 44, y: 20, kind: 'shelf' },
  { room: 'library', x: 41, y: 26, kind: 'book' },
  { room: 'library', x: 41, y: 27, kind: 'desk' },
  { room: 'coffee', x: 49, y: 20, kind: 'coffee' },
  { room: 'coffee', x: 50, y: 22, kind: 'plant' },
  { room: 'other', x: 49, y: 29, kind: 'desk' },
];

export interface Spot {
  room: RoomId;
  x: number;
  y: number;
}

const SPOTS: Record<RoomId, Spot[]> = {
  charts: [
    { room: 'charts', x: 4, y: 6 },
    { room: 'charts', x: 8, y: 6 },
    { room: 'charts', x: 12, y: 6 },
    { room: 'charts', x: 6, y: 12 },
  ],
  news: [
    { room: 'news', x: 22, y: 8 },
    { room: 'news', x: 26, y: 8 },
    { room: 'news', x: 24, y: 11 },
  ],
  whales: [
    { room: 'whales', x: 34, y: 6 },
    { room: 'whales', x: 38, y: 6 },
    { room: 'whales', x: 36, y: 11 },
  ],
  risk: [
    { room: 'risk', x: 46, y: 9 },
    { room: 'risk', x: 48, y: 11 },
  ],
  code: [
    { room: 'code', x: 4, y: 24 },
    { room: 'code', x: 8, y: 24 },
    { room: 'code', x: 6, y: 30 },
  ],
  talk: [
    { room: 'talk', x: 16, y: 24 },
    { room: 'talk', x: 20, y: 24 },
    { room: 'talk', x: 16, y: 27 },
    { room: 'talk', x: 20, y: 27 },
  ],
  present: [
    { room: 'present', x: 28, y: 26 },
    { room: 'present', x: 32, y: 26 },
    { room: 'present', x: 30, y: 30 },
  ],
  library: [
    { room: 'library', x: 41, y: 28 },
    { room: 'library', x: 43, y: 24 },
  ],
  coffee: [
    { room: 'coffee', x: 49, y: 22 },
    { room: 'coffee', x: 50, y: 23 },
    { room: 'coffee', x: 48, y: 23 },
  ],
  other: [
    { room: 'other', x: 49, y: 30 },
    { room: 'other', x: 50, y: 30 },
    { room: 'other', x: 48, y: 31 },
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
  for (const r of ROOMS) {
    if (tx >= r.x && ty >= r.y && tx < r.x + r.w && ty < r.y + r.h) return r;
  }
  return null;
}

export function doorOf(r: RoomDef): { x: number; y: number } {
  const x = r.x + Math.floor(r.w / 2);
  const y = r.door === 'north' ? r.y : r.y + r.h - 1;
  return { x, y };
}

export function buildBlocked(): Uint8Array {
  const cells = new Uint8Array(MAP_W * MAP_H);
  for (const r of ROOMS) {
    for (let y = r.y; y < r.y + r.h; y++) {
      for (let x = r.x; x < r.x + r.w; x++) {
        const edge = x === r.x || y === r.y || x === r.x + r.w - 1 || y === r.y + r.h - 1;
        if (edge) cells[y * MAP_W + x] = 1;
      }
    }
    const d = doorOf(r);
    cells[d.y * MAP_W + d.x] = 0;
    if (d.x + 1 < r.x + r.w - 1) cells[d.y * MAP_W + d.x + 1] = 0;
  }
  for (let x = 0; x < MAP_W; x++) {
    cells[x] = 1;
    cells[(MAP_H - 1) * MAP_W + x] = 1;
  }
  for (let y = 0; y < MAP_H; y++) {
    cells[y * MAP_W] = 1;
    cells[y * MAP_W + MAP_W - 1] = 1;
  }
  return cells;
}

export function roomCenter(r: RoomDef): { x: number; y: number } {
  return { x: r.x + r.w / 2, y: r.y + r.h / 2 };
}

/** Tile just outside the building where temporary helpers walk off. */
export const EXIT = { x: 2, y: HALL_Y };
