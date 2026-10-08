import type { RoomId } from './agents';

export interface RoomDef {
  id: RoomId;
  label: string;
  blurb: string;
  x: number;
  y: number;
  w: number;
  h: number;
  floor: string;
  floorAlt: string;
  wall: string;
}

export const MAP_W = 42;
export const MAP_H = 28;

export const ROOMS: RoomDef[] = [
  {
    id: 'trading',
    label: 'Trading Floor',
    blurb: 'Mesas, telas BTC / ETH / SOL',
    x: 1,
    y: 1,
    w: 18,
    h: 12,
    floor: '#143226',
    floorAlt: '#10281e',
    wall: '#0c2418',
  },
  {
    id: 'news',
    label: 'News Room',
    blurb: 'Fios e headlines',
    x: 21,
    y: 1,
    w: 9,
    h: 8,
    floor: '#3a2a16',
    floorAlt: '#2e2212',
    wall: '#24180c',
  },
  {
    id: 'other',
    label: 'Other Business',
    blurb: 'Leads, WhatsApp, IGORMARCHETTI',
    x: 32,
    y: 1,
    w: 8,
    h: 8,
    floor: '#163038',
    floorAlt: '#10262c',
    wall: '#0c2026',
  },
  {
    id: 'library',
    label: 'Research Library',
    blurb: 'Estatística e estudo',
    x: 1,
    y: 15,
    w: 12,
    h: 11,
    floor: '#241838',
    floorAlt: '#1c1230',
    wall: '#160e28',
  },
  {
    id: 'meeting',
    label: 'Whiteboard',
    blurb: 'Relógios do mundo + roteador',
    x: 15,
    y: 15,
    w: 12,
    h: 11,
    floor: '#1a2838',
    floorAlt: '#142030',
    wall: '#101c28',
  },
  {
    id: 'risk',
    label: 'Risk / Compliance',
    blurb: 'O único que diz não',
    x: 29,
    y: 12,
    w: 11,
    h: 7,
    floor: '#3a1820',
    floorAlt: '#2c1218',
    wall: '#240e14',
  },
  {
    id: 'coffee',
    label: 'Coffee',
    blurb: 'Idle > 30 min dorme aqui',
    x: 29,
    y: 20,
    w: 11,
    h: 6,
    floor: '#3a2814',
    floorAlt: '#2e2010',
    wall: '#24180c',
  },
];

export interface Spot {
  room: RoomId;
  x: number;
  y: number;
}

const SPOTS: Record<RoomId, Spot[]> = {
  trading: [
    { room: 'trading', x: 4, y: 6 },
    { room: 'trading', x: 7, y: 6 },
    { room: 'trading', x: 10, y: 6 },
    { room: 'trading', x: 13, y: 6 },
    { room: 'trading', x: 16, y: 6 },
    { room: 'trading', x: 6, y: 9 },
    { room: 'trading', x: 12, y: 9 },
  ],
  news: [
    { room: 'news', x: 24, y: 4 },
    { room: 'news', x: 27, y: 4 },
  ],
  risk: [
    { room: 'risk', x: 32, y: 15 },
    { room: 'risk', x: 36, y: 15 },
  ],
  library: [
    { room: 'library', x: 4, y: 19 },
    { room: 'library', x: 8, y: 19 },
    { room: 'library', x: 6, y: 22 },
  ],
  meeting: [
    { room: 'meeting', x: 18, y: 19 },
    { room: 'meeting', x: 22, y: 19 },
    { room: 'meeting', x: 20, y: 22 },
  ],
  coffee: [
    { room: 'coffee', x: 32, y: 22 },
    { room: 'coffee', x: 35, y: 22 },
    { room: 'coffee', x: 37, y: 22 },
  ],
  other: [
    { room: 'other', x: 34, y: 4 },
    { room: 'other', x: 37, y: 4 },
    { room: 'other', x: 35, y: 6 },
  ],
};

const used = new Map<string, number>();

export function claimSpot(room: RoomId, agentId: string): Spot {
  const list = SPOTS[room];
  const key = room;
  let i = used.get(key) ?? 0;
  // stable assignment: hash agent into a slot, then walk if taken conceptually by increment per call order
  const idx = i % list.length;
  used.set(key, i + 1);
  return list[idx];
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
  return { x: r.x + Math.floor(r.w / 2), y: r.y + r.h - 1 };
}

/** 1 = wall. Hallways between rooms stay open. */
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
  // outer border
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
