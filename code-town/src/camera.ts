/**
 * 2D camera: pan, zoom anchored to a screen point, clamp to world bounds.
 * Behavior adapted from Habblaud (MIT) client/src/world/camera.ts
 * Copyright (c) 2026 Márcio Junior — see THIRD_PARTY_NOTICES.md.
 */

export interface Bounds {
  x: number;
  y: number;
  w: number;
  h: number;
}

const ZOOM_MIN = 0.45;
const ZOOM_MAX = 3.2;

export class Camera {
  x = 0;
  y = 0;
  zoom = 1;
  viewW = 800;
  viewH = 600;
  dpr = 1;
  bounds: Bounds = { x: 0, y: 0, w: 800, h: 600 };
  insets = { top: 56, right: 340, bottom: 12, left: 12 };

  setView(w: number, h: number, dpr: number): void {
    this.viewW = Math.max(1, w);
    this.viewH = Math.max(1, h);
    this.dpr = dpr || 1;
  }

  panBy(dx: number, dy: number): void {
    this.x -= dx / this.zoom;
    this.y -= dy / this.zoom;
    this.clamp();
  }

  zoomAt(newZoom: number, sx: number, sy: number): void {
    const z = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, newZoom));
    const wx = this.x + (sx - this.viewW / 2) / this.zoom;
    const wy = this.y + (sy - this.viewH / 2) / this.zoom;
    this.zoom = z;
    this.x = wx - (sx - this.viewW / 2) / z;
    this.y = wy - (sy - this.viewH / 2) / z;
    this.clamp();
  }

  clamp(): void {
    const b = this.bounds;
    const z = this.zoom;
    const ins = this.insets;
    const l = (-this.viewW / 2 + ins.left) / z;
    const r = (this.viewW / 2 - ins.right) / z;
    const t = (-this.viewH / 2 + ins.top) / z;
    const btm = (this.viewH / 2 - ins.bottom) / z;
    if (b.w <= r - l) this.x = b.x + b.w / 2 - (l + r) / 2;
    else this.x = Math.max(b.x - l, Math.min(b.x + b.w - r, this.x));
    if (b.h <= btm - t) this.y = b.y + b.h / 2 - (t + btm) / 2;
    else this.y = Math.max(b.y - t, Math.min(b.y + b.h - btm, this.y));
  }

  transform(): { scale: number; ox: number; oy: number } {
    const scale = this.zoom * this.dpr;
    const ox = Math.round((this.viewW * this.dpr) / 2 - this.x * scale);
    const oy = Math.round((this.viewH * this.dpr) / 2 - this.y * scale);
    return { scale, ox, oy };
  }

  worldToScreen(wx: number, wy: number): { x: number; y: number } {
    const { scale, ox, oy } = this.transform();
    return { x: (wx * scale + ox) / this.dpr, y: (wy * scale + oy) / this.dpr };
  }

  screenToWorld(sx: number, sy: number): { x: number; y: number } {
    const { scale, ox, oy } = this.transform();
    return { x: (sx * this.dpr - ox) / scale, y: (sy * this.dpr - oy) / scale };
  }

  focus(wx: number, wy: number, zoom?: number): void {
    if (zoom) this.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom));
    const c = {
      x: wx - (this.insets.left - this.insets.right) / 2 / this.zoom,
      y: wy - (this.insets.top - this.insets.bottom) / 2 / this.zoom,
    };
    this.x = c.x;
    this.y = c.y;
    this.clamp();
  }
}
