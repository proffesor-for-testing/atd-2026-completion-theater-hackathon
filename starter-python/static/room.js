// "The Room": a read-only view, redrawn from each server snapshot on refresh (fixed two-table layout).
// It owns no booking state. render(sessions, reservations) diffs successive SERVER snapshots:
// a reservation that appears drops into its chair; one that is cancelled leaves as a ghost.
// Booking always goes through the labelled 2D form; clicking the room only preselects a session.
import * as THREE from '/vendor/three.module.min.js';

const C = { ink: 0x141414, white: 0xffffff, red: 0xe3262f, sun: 0xffd21f, wood: 0xf3eee4, plinth: 0xffffff, bulbOff: 0xcfcac0 };
const REDUCED = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
const LIFT = 0.2;          // everything stands on a 0.2-high plinth
const CHAIR_Z = -1.0, SEAT_TOP = 0.59, CORD_TOP = 4.3;

// ---------- toon helpers ----------
function outlined(geometry, color, parent, { edges = true } = {}) {
  const mesh = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({ color }));
  mesh.castShadow = true; mesh.receiveShadow = true;
  if (edges) mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 20), new THREE.LineBasicMaterial({ color: C.ink })));
  parent.add(mesh);
  return mesh;
}
function hull(geometry, color, parent, thickness) {
  // Inverted-hull ink outline for round shapes (edge lines would draw every facet).
  const g = new THREE.Group();
  const body = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({ color, transparent: true }));
  body.castShadow = true;
  const line = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: C.ink, side: THREE.BackSide, transparent: true }));
  line.scale.setScalar(thickness);
  g.add(line, body); parent.add(g);
  return { group: g, body, line };
}
function textTexture(text, { size = 56, weight = 800, color = '#141414', bg = null } = {}) {
  const font = `${weight} ${size}px Bricolage, "Arial Black", system-ui, sans-serif`;
  const c = document.createElement('canvas'); const ctx = c.getContext('2d');
  ctx.font = font;
  const pad = bg ? 12 : 12;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2, h = Math.ceil(size * 1.4);
  c.width = w * 2; c.height = h * 2; ctx.scale(2, 2);
  if (bg) { ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h); }
  ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
  ctx.fillText(text, w / 2, h / 2 + 2);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  return { tex, aspect: w / h };
}
function svgTexture(svgMarkup, onReady) {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  if (svgMarkup) {
    const img = new Image();
    img.onload = () => { c.getContext('2d').drawImage(img, 0, 0, 256, 256); tex.needsUpdate = true; onReady(); };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgMarkup);
  }
  return tex;
}

// ---------- furniture ----------
function chair(parent) {
  const g = new THREE.Group();
  const seat = outlined(new THREE.BoxGeometry(0.62, 0.08, 0.6), C.white, g); seat.position.y = 0.55;
  const back = outlined(new THREE.BoxGeometry(0.62, 0.62, 0.08), C.white, g); back.position.set(0, 0.9, -0.26);
  for (const [x, z] of [[-0.26, -0.24], [0.26, -0.24], [-0.26, 0.24], [0.26, 0.24]]) {
    const leg = outlined(new THREE.BoxGeometry(0.06, 0.52, 0.06), C.ink, g, { edges: false }); leg.position.set(x, 0.26, z);
  }
  parent.add(g);
  return { group: g };
}

function table(scene, x, seats, id) {
  const root = new THREE.Group(); root.position.set(x, LIFT, 0); scene.add(root);
  const width = Math.max(2.2, seats * 0.95 + 0.5);
  const top = outlined(new THREE.BoxGeometry(width, 0.1, 1.3), C.wood, root); top.position.y = 1.0;
  for (const [lx, lz] of [[-width / 2 + 0.15, -0.5], [width / 2 - 0.15, -0.5], [-width / 2 + 0.15, 0.5], [width / 2 - 0.15, 0.5]]) {
    const leg = outlined(new THREE.BoxGeometry(0.08, 0.95, 0.08), C.ink, root, { edges: false }); leg.position.set(lx, 0.48, lz);
  }
  const lbl = textTexture(id, { size: 56 });
  const decal = new THREE.Mesh(new THREE.PlaneGeometry(0.42 * lbl.aspect, 0.42), new THREE.MeshBasicMaterial({ map: lbl.tex, transparent: true }));
  decal.rotation.x = -Math.PI / 2; decal.position.set(0, 1.056, 0.22); root.add(decal);
  // pendant lamp
  const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, CORD_TOP - 3.4), new THREE.MeshBasicMaterial({ color: C.ink }));
  cord.position.y = (CORD_TOP + 3.4) / 2; root.add(cord);
  const shade = outlined(new THREE.ConeGeometry(0.38, 0.34, 32, 1, true), C.ink, root, { edges: false }); shade.position.y = 3.25;
  shade.material.side = THREE.DoubleSide;
  const bulbMat = new THREE.MeshBasicMaterial({ color: C.bulbOff });
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.11, 24, 16), bulbMat); bulb.position.y = 3.11; root.add(bulb);
  const glow = new THREE.PointLight(C.sun, 0, 5.5, 1.4); glow.position.y = 2.9; root.add(glow);
  const pool = new THREE.Mesh(new THREE.CircleGeometry(1.55, 64), new THREE.MeshBasicMaterial({ color: C.sun, transparent: true, opacity: 0, depthWrite: false }));
  pool.rotation.x = -Math.PI / 2; pool.position.y = 0.006; root.add(pool);
  const chairs = [];
  for (let i = 0; i < seats; i++) {
    const ch = chair(root);
    ch.group.position.set((i - (seats - 1) / 2) * 0.95, 0, CHAIR_Z);
    chairs.push(ch);
  }
  return { id, root, chairs, bulbMat, glow, pool, lit: false };
}

// ---------- people ----------
function person(alias, color, svgMarkup, redraw) {
  const g = new THREE.Group();
  const fadeExtra = [], bodies = [];
  const body = hull(new THREE.CapsuleGeometry(0.21, 0.26, 6, 20), color, g, 1.12);
  body.group.position.y = 0.36;
  for (const side of [-1, 1]) {
    const arm = hull(new THREE.CapsuleGeometry(0.065, 0.42, 4, 12), color, g, 1.22);
    arm.group.rotation.x = Math.PI / 2 - 0.12;
    arm.group.position.set(side * 0.2, 0.5, 0.3);
    fadeExtra.push(arm.body.material, arm.line.material);
    bodies.push(arm.body.material);
  }
  const face = new THREE.Sprite(new THREE.SpriteMaterial({ map: svgTexture(svgMarkup, redraw), transparent: true }));
  face.scale.set(0.52, 0.52, 1); face.position.y = 0.93;
  const tagT = textTexture(alias.slice(0, 16), { size: 34, weight: 700, color: '#ffffff', bg: '#141414' });
  const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map: tagT.tex, transparent: true, depthTest: false }));
  tag.scale.set(0.24 * tagT.aspect, 0.24, 1); tag.position.y = 1.36; tag.renderOrder = 20;
  g.add(face, tag);
  bodies.push(body.body.material);
  return { group: g, body, bodies, fade: [body.body.material, body.line.material, face.material, tag.material, ...fadeExtra] };
}

export function mount(container, { onPick, onPerson, avatar, onLayout } = {}) {
  const canvas = container.querySelector('canvas');
  // Throws when WebGL is unavailable; the page catches that and keeps the room hidden.
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.BasicShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  // diorama plinth with a hard ink offset shadow, like the 2D cards
  const plinth = outlined(new THREE.BoxGeometry(10.4, LIFT, 4.4), C.plinth, scene); plinth.position.set(0.15, LIFT / 2, -0.3);
  plinth.castShadow = false;
  const drop = new THREE.Mesh(new THREE.PlaneGeometry(10.4, 4.4), new THREE.MeshBasicMaterial({ color: C.ink }));
  drop.rotation.x = -Math.PI / 2; drop.position.set(0.15 + 0.24, 0.0, -0.3 + 0.24); scene.add(drop);
  const shadowCatcher = new THREE.Mesh(new THREE.PlaneGeometry(10.4, 4.4), new THREE.ShadowMaterial({ color: C.ink, opacity: 0.14 }));
  shadowCatcher.rotation.x = -Math.PI / 2; shadowCatcher.position.set(0.15, LIFT + 0.002, -0.3); shadowCatcher.receiveShadow = true; scene.add(shadowCatcher);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d3c8, 2.3));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(-4, 9, 6); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 30 });
  scene.add(sun);

  const tables = { 'CT-101': table(scene, -2.1, 2, 'CT-101'), 'CT-102': table(scene, 2.35, 3, 'CT-102') };

  // camera: orthographic; it only moves when the visitor moves the pointer
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  const FULL = container.dataset.fit === 'full';
  const target = new THREE.Vector3(0.15, FULL ? 2.05 : 1.45, -0.3);
  const base = new THREE.Spherical().setFromVector3(new THREE.Vector3(6.5, 7.2, 9.5));
  const look = { yaw: 0, pitch: 0, ty: 0, tp: 0 };
  function placeCamera() {
    const s = base.clone(); s.theta += look.yaw; s.phi = Math.min(1.2, Math.max(0.55, s.phi + look.pitch));
    camera.position.setFromSpherical(s).add(target);
    camera.lookAt(target);
  }
  placeCamera();

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    const aspect = w / h, needW = 6.0, needH = FULL ? 5.4 : 3.35;
    let halfW = needW, halfH = needW / aspect;
    if (halfH < needH) { halfH = needH; halfW = needH * aspect; }
    Object.assign(camera, { left: -halfW, right: halfW, top: halfH, bottom: -halfH });
    camera.updateProjectionMatrix();
    kick();
  }

  // ---------- on-demand animation loop (idle = no frames) ----------
  const anims = new Set();
  let raf = 0, last = 0;
  function loop(now) {
    const dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
    look.yaw += (look.ty - look.yaw) * Math.min(1, dt * 6);
    look.pitch += (look.tp - look.pitch) * Math.min(1, dt * 6);
    placeCamera();
    for (const a of [...anims]) if (a(now, dt) === false) anims.delete(a);
    renderer.render(scene, camera);
    layout();
    const settling = Math.abs(look.ty - look.yaw) > 1e-4 || Math.abs(look.tp - look.pitch) > 1e-4;
    raf = anims.size || settling ? requestAnimationFrame(loop) : 0;
    if (!raf) last = 0;
  }
  const tmp = new THREE.Vector3();
  function layout() {
    if (!onLayout) return;
    const w = container.clientWidth, h = container.clientHeight, out = {};
    for (const t of Object.values(tables)) {
      tmp.set(t.root.position.x, LIFT + CORD_TOP, 0).project(camera);
      out[t.id] = { x: (tmp.x + 1) / 2 * w, y: (1 - tmp.y) / 2 * h };
    }
    onLayout(out);
  }
  function kick() { if (!raf) raf = requestAnimationFrame(loop); }
  function animate(fn) { anims.add(fn); kick(); }
  new ResizeObserver(resize).observe(container);

  if (!REDUCED) {
    container.addEventListener('pointermove', (ev) => {
      const r = container.getBoundingClientRect();
      look.ty = ((ev.clientX - r.left) / r.width - 0.5) * 0.3;
      look.tp = ((ev.clientY - r.top) / r.height - 0.5) * -0.14;
      kick();
    });
    container.addEventListener('pointerleave', () => { look.ty = 0; look.tp = 0; kick(); });
  }

  // ---------- effects ----------
  function bounce(k) {
    const n = 7.5625, d = 2.75;
    if (k < 1 / d) return n * k * k;
    if (k < 2 / d) { k -= 1.5 / d; return n * k * k + 0.75; }
    if (k < 2.5 / d) { k -= 2.25 / d; return n * k * k + 0.9375; }
    k -= 2.625 / d; return n * k * k + 0.984375;
  }
  function confetti(at) {
    const bits = [], colors = [C.sun, C.red, 0x1e7bff, 0x2db665, C.ink];
    for (let i = 0; i < 40; i++) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.1), new THREE.MeshBasicMaterial({ color: colors[i % colors.length], side: THREE.DoubleSide, transparent: true }));
      m.position.copy(at);
      const a = Math.random() * Math.PI * 2, sp = 1.2 + Math.random() * 1.6;
      m.userData.v = new THREE.Vector3(Math.cos(a) * sp * 0.7, 2.4 + Math.random() * 2, Math.sin(a) * sp * 0.7);
      m.userData.spin = new THREE.Vector3(4 + Math.random() * 10, 4 + Math.random() * 10, 0);
      scene.add(m); bits.push(m);
    }
    const start = performance.now();
    animate((now, dt) => {
      const t = (now - start) / 1000;
      for (const m of bits) {
        m.userData.v.y -= 8 * dt;
        m.position.addScaledVector(m.userData.v, dt);
        m.rotation.x += m.userData.spin.x * dt; m.rotation.y += m.userData.spin.y * dt;
        m.material.opacity = Math.max(0, 1 - Math.max(0, t - 0.55) / 0.4);
      }
      if (t > 1.0) { for (const m of bits) { scene.remove(m); m.geometry.dispose(); m.material.dispose(); } return false; }
    });
  }
  function dropIn(p, delay, withConfetti) {
    const g = p.group, endY = g.position.y;
    g.position.y = endY + 3.4; g.visible = false;
    const start = performance.now() + delay;
    animate((now) => {
      if (now < start) return;
      g.visible = true;
      const k = Math.min(1, (now - start) / 700);
      g.position.y = endY + 3.4 * (1 - bounce(k));
      const sq = k > 0.33 && k < 0.55 ? 1 - Math.sin(((k - 0.33) / 0.22) * Math.PI) * 0.16 : 1;
      g.scale.set(1 / Math.sqrt(sq), sq, 1 / Math.sqrt(sq));
      if (k >= 1) {
        g.scale.set(1, 1, 1); g.position.y = endY;
        if (withConfetti) confetti(g.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.8, 0)));
        return false;
      }
    });
  }
  function ghostAway(p, root) {
    const g = p.group, y0 = g.position.y, x0 = g.position.x, start = performance.now();
    for (const m of p.bodies) m.color.set(0xd9d4ca);
    animate((now) => {
      const k = Math.min(1, (now - start) / 1500), e = 1 - Math.pow(1 - k, 2);
      g.position.y = y0 + e * 2.6;
      g.position.x = x0 + Math.sin(k * Math.PI * 3) * 0.14;
      for (const m of p.fade) m.opacity = 1 - k * k;
      if (k >= 1) {
        root.remove(g);
        g.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); } });
        return false;
      }
    });
  }
  function setLamp(t, on, withMotion) {
    if (t.lit === on) return; t.lit = on;
    const apply = (k) => { t.glow.intensity = 9 * k; t.pool.material.opacity = 0.42 * k; t.bulbMat.color.setHex(k > 0.5 ? C.sun : C.bulbOff); };
    if (!withMotion) { apply(on ? 1 : 0); kick(); return; }
    const start = performance.now();
    animate((now) => {
      const k = Math.min(1, (now - start) / 480);
      const f = on ? k : 1 - k; // smooth fade: no flashing (WCAG 2.3.1)
      apply(f);
      if (k >= 1) { apply(on ? 1 : 0); return false; }
    });
  }

  // ---------- render from server snapshots ----------
  const people = new Map(); // reservation id -> person
  let first = true;
  function render(sessions, reservations) {
    const motion = !REDUCED;
    const live = new Set();
    const activeIds = new Set(reservations.filter((r) => r.status === 'active').map((r) => r.id));
    for (const [id, p] of people) {
      if (activeIds.has(id)) continue;
      people.delete(id);
      const t = tables[p.sessionId];
      if (motion) ghostAway(p, t.root); else t.root.remove(p.group);
    }
    let stagger = 0;
    for (const s of sessions) {
      const t = tables[s.id]; if (!t) continue;
      const active = reservations.filter((r) => r.sessionId === s.id && r.status === 'active').slice(0, t.chairs.length);
      // stable seating: people keep their chair; newcomers take the lowest free chair
      const taken = new Set(active.map((r) => people.get(r.id)).filter(Boolean).map((p) => p.seat));
      active.forEach((res) => {
        live.add(res.id);
        if (people.has(res.id)) return;
        let seat = 0; while (taken.has(seat)) seat++;
        if (seat >= t.chairs.length) return;
        taken.add(seat);
        const chairPos = t.chairs[seat].group.position;
        const av = avatar ? avatar(res.attendeeAlias) : { color: '#ffd21f', svg: '' };
        const p = person(res.attendeeAlias, new THREE.Color(av.color), av.svg, kick);
        p.sessionId = s.id; p.seat = seat;
        p.group.position.set(chairPos.x, SEAT_TOP - 0.02, chairPos.z + 0.05);
        p.alias = res.attendeeAlias; p.group.userData.person = p;
        t.root.add(p.group); people.set(res.id, p);
        if (motion) dropIn(p, first ? 140 * stagger++ : 0, !first);
      });
      setLamp(t, s.capacity > 0 && s.remainingSeats === 0, motion && !first);
    }
    first = false;
    kick();
  }

  // clicking a table, chair or person preselects that session in the real form (no booking here)
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  canvas.addEventListener('click', (ev) => {
    const r = canvas.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    // a character: hop + spin, then open their profile
    for (const p of people.values()) {
      if (!ray.intersectObject(p.group, true).length) continue;
      if (!REDUCED && !p.hopping) {
        p.hopping = true;
        const g = p.group, y0 = g.position.y, start = performance.now();
        animate((now) => {
          const k = Math.min(1, (now - start) / 520);
          g.position.y = y0 + Math.sin(k * Math.PI) * 0.55;
          g.rotation.y = k * Math.PI * 2;
          if (k >= 1) { g.position.y = y0; g.rotation.y = 0; p.hopping = false; return false; }
        });
      }
      if (onPerson) setTimeout(() => onPerson(p.alias), REDUCED ? 0 : 450);
      return;
    }
    for (const t of Object.values(tables)) {
      if (ray.intersectObject(t.root, true).length) { if (onPick) onPick(t.id); return; }
    }
  });
  canvas.style.cursor = 'pointer';

  resize();
  renderer.render(scene, camera);
  layout();
  return { render, relayout: () => { resize(); } };
}
