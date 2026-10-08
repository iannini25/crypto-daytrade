/** Isometric diamond grid. Tile size is in world pixels before camera zoom. */
export const TW = 64;
export const TH = 32;

export function tileToWorld(tx: number, ty: number): { x: number; y: number } {
  return {
    x: (tx - ty) * (TW / 2),
    y: (tx + ty) * (TH / 2),
  };
}

export function worldToTile(wx: number, wy: number): { tx: number; ty: number } {
  const tx = (wx / (TW / 2) + wy / (TH / 2)) / 2;
  const ty = (wy / (TH / 2) - wx / (TW / 2)) / 2;
  return { tx, ty };
}

export function depthKey(tx: number, ty: number): number {
  return tx + ty;
}
