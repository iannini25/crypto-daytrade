/**
 * 4-direction A* with a small turn penalty so paths prefer straight runs.
 * Approach adapted from Habblaud (MIT) client/src/world/path/astar.ts
 * Copyright (c) 2026 Márcio Junior — see THIRD_PARTY_NOTICES.md.
 */

const DX = [1, -1, 0, 0];
const DY = [0, 0, 1, -1];

export function findPath(
  blocked: Uint8Array,
  w: number,
  h: number,
  sx: number,
  sy: number,
  gx: number,
  gy: number,
): Array<{ x: number; y: number }> {
  const inside = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h;
  if (!inside(sx, sy) || !inside(gx, gy)) return [];
  if (blocked[gy * w + gx]) return [];
  if (sx === gx && sy === gy) return [];

  const n = w * h;
  const g = new Float32Array(n).fill(Infinity);
  const from = new Int32Array(n).fill(-1);
  const dirIn = new Int8Array(n).fill(-1);
  const closed = new Uint8Array(n);
  const start = sy * w + sx;
  const goal = gy * w + gx;
  g[start] = 0;

  const heap: number[] = [start];
  const key = (i: number) => g[i] + (Math.abs((i % w) - gx) + Math.abs(Math.floor(i / w) - gy)) * 1.001;

  const push = (i: number) => {
    heap.push(i);
    let p = heap.length - 1;
    while (p > 0) {
      const parent = (p - 1) >> 1;
      if (key(heap[parent]) <= key(heap[p])) break;
      [heap[parent], heap[p]] = [heap[p], heap[parent]];
      p = parent;
    }
  };
  const pop = () => {
    const top = heap[0];
    const last = heap.pop()!;
    if (heap.length) {
      heap[0] = last;
      let p = 0;
      while (true) {
        const l = p * 2 + 1;
        if (l >= heap.length) break;
        const r = l + 1;
        const c = r < heap.length && key(heap[r]) < key(heap[l]) ? r : l;
        if (key(heap[c]) >= key(heap[p])) break;
        [heap[p], heap[c]] = [heap[c], heap[p]];
        p = c;
      }
    }
    return top;
  };

  push(start);
  while (heap.length) {
    const cur = pop();
    if (cur === goal) {
      const out: Array<{ x: number; y: number }> = [];
      for (let i = goal; i !== start && i >= 0; i = from[i]) {
        out.push({ x: i % w, y: Math.floor(i / w) });
      }
      out.reverse();
      return out;
    }
    if (closed[cur]) continue;
    closed[cur] = 1;
    const cx = cur % w;
    const cy = Math.floor(cur / w);
    for (let k = 0; k < 4; k++) {
      const nx = cx + DX[k];
      const ny = cy + DY[k];
      if (!inside(nx, ny)) continue;
      const ni = ny * w + nx;
      if (blocked[ni] && ni !== goal) continue;
      if (closed[ni]) continue;
      let cost = 1;
      if (dirIn[cur] >= 0 && dirIn[cur] !== k) cost += 0.35;
      const ng = g[cur] + cost;
      if (ng >= g[ni]) continue;
      g[ni] = ng;
      from[ni] = cur;
      dirIn[ni] = k;
      push(ni);
    }
  }
  return [];
}
