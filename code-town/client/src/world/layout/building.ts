// Montagem do prédio: núcleo + corredor + salas de projeto -> grade de caminhabilidade e spots.
import { FURNITURE } from '../../art/api';
import { BUILDING_H, COL_W } from '../constants';
import { BLOCKED, FREE, SEAT, WalkGrid } from '../path/grid';
import { furnitureBlocks, furnitureIsSeat } from './builder';
import { layoutCafe, layoutLounge, layoutReception, layoutRestroom } from './core';
import { layoutCorridor } from './corridor';
import { DESK_COLS, emptyCorridor, FLOOR_H, FLOOR_W, layoutDeskLounge } from './desk-floor';
import { buildingRect } from './geometry';
import type { AreaLayout, SpotDef, TileRect } from './types';

export interface BuildingLayout {
  cols: number;
  rect: TileRect;
  core: AreaLayout[];
  corridor: AreaLayout;
  rooms: AreaLayout[];
  grid: WalkGrid;
  spots: SpotDef[];
  /** Planta da mesa: Chefe no centro, sem corredor nem núcleo antigo. */
  desk?: boolean;
}

let coreCache: AreaLayout[] | null = null;

/** Áreas fixas do núcleo (calculadas uma vez). */
export function coreAreas(): AreaLayout[] {
  return (coreCache ??= [layoutReception(), layoutRestroom(), layoutCafe(), layoutLounge()]);
}

/** Marca na grade as células caminháveis de uma área, os bloqueios e os assentos. */
export function paintArea(grid: WalkGrid, area: AreaLayout): void {
  for (const r of area.walkable) grid.fill(r.x, r.y, r.w, r.h, FREE);
  for (const r of area.blocked ?? []) grid.fill(r.x, r.y, r.w, r.h, BLOCKED);
  for (const f of area.furniture) {
    const def = FURNITURE[f.kind];
    if (def.mount !== 'floor') continue;
    const { w, h } = def.footprint;
    if (furnitureBlocks(f.kind)) grid.fill(f.tx, f.ty, w, h, BLOCKED);
    else if (furnitureIsSeat(f.kind)) {
      for (let y = f.ty; y < f.ty + h; y++) for (let x = f.tx; x < f.tx + w; x++) if (grid.get(x, y) === FREE) grid.set(x, y, SEAT);
    }
  }
}

export function buildWalkGrid(cols: number, areas: readonly AreaLayout[], version = 0): WalkGrid {
  return buildWalkGridSized(cols * COL_W, BUILDING_H, areas, version);
}

export function buildWalkGridSized(w: number, h: number, areas: readonly AreaLayout[], version = 0): WalkGrid {
  const grid = new WalkGrid(w, h, version);
  for (const a of areas) paintArea(grid, a);
  return grid;
}

function isDeskFloor(rooms: readonly AreaLayout[]): boolean {
  return rooms.length > 0 && rooms.every((r) => r.id.startsWith('grok:'));
}

export function assembleBuilding(cols: number, rooms: readonly AreaLayout[], version = 0): BuildingLayout {
  if (isDeskFloor(rooms)) return assembleDeskFloor(rooms, version);
  const core = coreAreas();
  const corridor = layoutCorridor(cols);
  const all = [...core, corridor, ...rooms];
  const grid = buildWalkGrid(cols, all, version);
  const spots: SpotDef[] = [];
  for (const a of all) spots.push(...a.spots);
  return { cols, rect: buildingRect(cols), core, corridor, rooms: [...rooms], grid, spots };
}

/** Lounge + salas já posicionadas. A grade cobre a planta inteira, não o prédio antigo. */
function assembleDeskFloor(rooms: readonly AreaLayout[], version: number): BuildingLayout {
  const lounge = layoutDeskLounge();
  const corridor = emptyCorridor();
  const core = [lounge];
  const all = [...core, ...rooms];
  const grid = buildWalkGridSized(FLOOR_W, FLOOR_H, all, version);
  const spots: SpotDef[] = [];
  for (const a of all) spots.push(...a.spots);
  return {
    cols: DESK_COLS,
    rect: { x: 0, y: 0, w: FLOOR_W, h: FLOOR_H },
    core,
    corridor,
    rooms: [...rooms],
    grid,
    spots,
    desk: true,
  };
}
