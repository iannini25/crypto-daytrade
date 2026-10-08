import { AGENTS, findAgent, helperFromEvent, type AgentConfig, type RoomId } from './agents';
import { EXIT, claimSpot, resetSpots, type Spot } from './office';
import { findPath } from './path';
import { isErrorEvent, poseFor, roomFor, shouldLeave, type AgentEvent, type Pose } from './routing';

export interface Avatar {
  agent: AgentConfig;
  x: number;
  y: number;
  dir: number;
  path: Array<{ x: number; y: number }>;
  room: RoomId;
  pose: Pose;
  bubble: string;
  error: boolean;
  events: AgentEvent[];
  spot: Spot;
  leaving: boolean;
}

const MAX_EVENTS = 12;

function avatarFrom(agent: AgentConfig, blocked: Uint8Array, w: number, h: number): Avatar {
  const spot = claimSpot(agent.home);
  const path = findPath(blocked, w, h, EXIT.x, EXIT.y, spot.x, spot.y);
  return {
    agent,
    x: agent.temporary ? EXIT.x : spot.x,
    y: agent.temporary ? EXIT.y : spot.y,
    dir: 0,
    path: agent.temporary ? path : [],
    room: agent.home,
    pose: 'sit',
    bubble: '',
    error: false,
    events: [],
    spot,
    leaving: false,
  };
}

export function createAvatars(blocked: Uint8Array, w: number, h: number): Avatar[] {
  resetSpots();
  return AGENTS.map((agent) => avatarFrom(agent, blocked, w, h));
}

function resolveAgent(avatars: Avatar[], ev: AgentEvent): AgentConfig | null {
  const known = findAgent(ev.agent_id) ?? findAgent(ev.agent_name);
  if (known) return known;
  const label = (ev.agent_name || ev.agent_id || '').trim();
  if (!label) return null;
  const existing = avatars.find(
    (a) => a.agent.id === ev.agent_id || a.agent.name.toLowerCase() === label.toLowerCase(),
  );
  if (existing) return existing.agent;
  return helperFromEvent(ev.agent_id || label, ev.agent_name || label, ev.summary || '');
}

export function applyEvent(avatars: Avatar[], ev: AgentEvent, blocked: Uint8Array, w: number, h: number): void {
  const agent = resolveAgent(avatars, ev);
  if (!agent) return;
  let av = avatars.find((a) => a.agent.id === agent.id);
  if (!av) {
    av = avatarFrom(agent, blocked, w, h);
    avatars.push(av);
  }
  if (av.events.some((e) => e.id === ev.id)) return;
  av.events.unshift(ev);
  av.events = av.events.slice(0, MAX_EVENTS);
  av.leaving = false;
  av.error = isErrorEvent(ev);
  av.bubble = ev.summary || ev.kind;
  if (shouldLeave(agent, ev)) {
    av.leaving = true;
    av.room = 'coffee';
    av.path = findPath(blocked, w, h, Math.round(av.x), Math.round(av.y), EXIT.x, EXIT.y);
    av.pose = 'walk';
    return;
  }
  const room = roomFor(agent, ev);
  av.room = room;
  if (room !== av.spot.room) av.spot = claimSpot(room);
  const sx = Math.round(av.x);
  const sy = Math.round(av.y);
  av.path = findPath(blocked, w, h, sx, sy, av.spot.x, av.spot.y);
  av.pose = poseFor(room, ev, av.path.length > 0);
}

export function stepAvatars(avatars: Avatar[], dt: number): void {
  const speed = 2.8;
  for (let i = avatars.length - 1; i >= 0; i--) {
    const av = avatars[i];
    if (av.leaving && !av.path.length) {
      avatars.splice(i, 1);
      continue;
    }
    if (!av.path.length) {
      const latest = av.events[0] ?? null;
      av.pose = poseFor(av.room, latest, false);
      av.x += (av.spot.x - av.x) * Math.min(1, dt * 6);
      av.y += (av.spot.y - av.y) * Math.min(1, dt * 6);
      continue;
    }
    av.pose = 'walk';
    let left = speed * dt;
    while (left > 0 && av.path.length) {
      const n = av.path[0];
      const dx = n.x - av.x;
      const dy = n.y - av.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 0.04) {
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
