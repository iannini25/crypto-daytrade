import { AGENTS, findAgent, type AgentConfig, type RoomId } from './agents';
import { claimSpot, resetSpots, type Spot } from './office';
import { findPath } from './path';
import { isErrorEvent, poseFor, roomFor, type AgentEvent } from './routing';

export interface Avatar {
  agent: AgentConfig;
  x: number;
  y: number;
  dir: number;
  path: Array<{ x: number; y: number }>;
  room: RoomId;
  pose: 'walk' | 'sit' | 'sleep' | 'read' | 'talk';
  bubble: string;
  error: boolean;
  events: AgentEvent[];
  spot: Spot;
}

const MAX_EVENTS = 12;

export function createAvatars(blocked: Uint8Array, w: number): Avatar[] {
  resetSpots();
  return AGENTS.map((agent) => {
    const spot = claimSpot(agent.home, agent.id);
    return {
      agent,
      x: spot.x,
      y: spot.y,
      dir: 0,
      path: [],
      room: agent.home,
      pose: 'sit' as const,
      bubble: '',
      error: false,
      events: [],
      spot,
    };
  });
}

export function applyEvent(avatars: Avatar[], ev: AgentEvent, blocked: Uint8Array, w: number, h: number): void {
  const agent = findAgent(ev.agent_id) ?? findAgent(ev.agent_name);
  if (!agent) return;
  const av = avatars.find((a) => a.agent.id === agent.id);
  if (!av) return;
  if (av.events.some((e) => e.id === ev.id)) return;
  av.events.unshift(ev);
  av.events = av.events.slice(0, MAX_EVENTS);
  const room = roomFor(agent, ev);
  av.room = room;
  av.error = isErrorEvent(ev);
  av.bubble = ev.summary || ev.kind;
  if (room !== av.spot.room) {
    av.spot = claimSpot(room, agent.id);
  }
  const sx = Math.round(av.x);
  const sy = Math.round(av.y);
  const path = findPath(blocked, w, h, sx, sy, av.spot.x, av.spot.y);
  av.path = path;
  av.pose = poseFor(room, ev, path.length > 0);
}

export function stepAvatars(avatars: Avatar[], dt: number): void {
  const speed = 3.4;
  for (const av of avatars) {
    if (!av.path.length) {
      const latest = av.events[0] ?? null;
      av.pose = poseFor(av.room, latest, false);
      av.x += (av.spot.x - av.x) * Math.min(1, dt * 4);
      av.y += (av.spot.y - av.y) * Math.min(1, dt * 4);
      continue;
    }
    av.pose = 'walk';
    let left = speed * dt;
    while (left > 0 && av.path.length) {
      const n = av.path[0];
      const dx = n.x - av.x;
      const dy = n.y - av.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 0.02) {
        av.x = n.x;
        av.y = n.y;
        av.path.shift();
        continue;
      }
      if (Math.abs(dx) > Math.abs(dy)) av.dir = dx > 0 ? 0 : 1;
      else av.dir = dy > 0 ? 2 : 3;
      const step = Math.min(left, dist);
      av.x += (dx / dist) * step;
      av.y += (dy / dist) * step;
      left -= step;
    }
  }
}
