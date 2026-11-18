// "The Room": a second, read-only view of the same API state.
// It owns no state: render(sessions, reservations) redraws from server data only.
// Booking always goes through the labelled 2D form; clicking a chair only preselects it.
import * as THREE from '/vendor/three.module.min.js';

const C = { ink: 0x141414, paper: 0xf5f4f1, white: 0xffffff, red: 0xe3262f, sun: 0xffd21f, wood: 0xe9e4da, line: 0xdedbd4 };
const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function outlined(geometry, color, parent) {
  const mesh = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({ color }));
  mesh.castShadow = true; mesh.receiveShadow = true;
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 20), new THREE.LineBasicMaterial({ color: C.ink }));
  mesh.add(edges);
  parent.add(mesh);
  return mesh;
}

function labelTexture(text, { size = 64, weight = 800, color = '#141414', bg = null, pad = 18, border = false } = {}) {
  const font = `${weight} ${size}px Bricolage, "Arial Black", system-ui, sans-serif`;
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  ctx.font = font;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2;
  const h = Math.ceil(size * 1.35) + pad;
  c.width = w * 2; c.height = h * 2;
  ctx.scale(2, 2);
  if (bg) { ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h); }
  if (border) { ctx.lineWidth = 4; ctx.strokeStyle = '#141414'; ctx.strokeRect(2, 2, w - 4, h - 4); }
  ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
  ctx.fillText(text, w / 2, h / 2 + 2);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  return { tex, aspect: w / h };
}

function chair(parent) {
  const g = new THREE.Group();
  const seat = outlined(new THREE.BoxGeometry(0.62, 0.08, 0.6), C.white, g); seat.position.y = 0.55;
  const back = outlined(new THREE.BoxGeometry(0.62, 0.62, 0.08), C.white, g); back.position.set(0, 0.9, -0.26);
  for (const [x, z] of [[-0.26, -0.24], [0.26, -0.24], [-0.26, 0.24], [0.26, 0.24]]) {
    const leg = outlined(new THREE.BoxGeometry(0.06, 0.52, 0.06), C.ink, g); leg.position.set(x, 0.26, z);
  }
  parent.add(g);
  return { group: g, parts: [seat, back] };
}

function table(scene, x, seats, id, title) {
  const root = new THREE.Group(); root.position.x = x; scene.add(root);
  const width = Math.max(2.2, seats * 0.95 + 0.5);
  const top = outlined(new THREE.BoxGeometry(width, 0.1, 1.3), C.wood, root); top.position.y = 1.0;
  for (const [lx, lz] of [[-width / 2 + 0.15, -0.5], [width / 2 - 0.15, -0.5], [-width / 2 + 0.15, 0.5], [width / 2 - 0.15, 0.5]]) {
    const leg = outlined(new THREE.BoxGeometry(0.08, 0.95, 0.08), C.ink, root); leg.position.set(lx, 0.48, lz);
  }
  // session id painted on the table top
  const lbl = labelTexture(id, { size: 56 });
  const decal = new THREE.Mesh(new THREE.PlaneGeometry(0.42 * lbl.aspect, 0.42), new THREE.MeshBasicMaterial({ map: lbl.tex, transparent: true }));
  decal.rotation.x = -Math.PI / 2; decal.position.set(0, 1.056, 0.18); root.add(decal);
  // pendant lamp: cord + shade + bulb
  const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.6), new THREE.MeshBasicMaterial({ color: C.ink }));
  cord.position.y = 3.75; root.add(cord);
  const shade = outlined(new THREE.ConeGeometry(0.38, 0.34, 32, 1, true), C.ink, root); shade.position.y = 2.85;
  shade.material.side = THREE.DoubleSide;
  const bulbMat = new THREE.MeshBasicMaterial({ color: 0xcfcac0 });
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.11, 24, 16), bulbMat); bulb.position.y = 2.71; root.add(bulb);
  const glow = new THREE.PointLight(C.sun, 0, 5.5, 1.4); glow.position.y = 2.5; root.add(glow);
  const pool = new THREE.Mesh(new THREE.CircleGeometry(1.5, 48), new THREE.MeshBasicMaterial({ color: C.sun, transparent: true, opacity: 0, depthWrite: false }));
  pool.rotation.x = -Math.PI / 2; pool.position.y = 0.006; root.add(pool);
  // chairs on the far side, facing the viewer
  const chairs = [];
  for (let i = 0; i < seats; i++) {
    const ch = chair(root);
    ch.group.position.set((i - (seats - 1) / 2) * 0.95, 0, -1.0);
    ch.sessionId = id; ch.index = i;
    chairs.push(ch);
  }
  return { id, title, root, chairs, bulbMat, glow, pool, tags: [] };
}

export function mount(container, { onPick } = {}) {
  const canvas = container.querySelector('canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  if (!renderer.getContext()) throw new Error('no WebGL');
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.BasicShadowMap; // crisp, hard shadows like the 2D cards
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ color: C.ink, opacity: 0.16 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d3c8, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(-4, 9, 6); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 30 });
  scene.add(sun);

  const tables = { 'CT-101': table(scene, -2.0, 2, 'CT-101'), 'CT-102': table(scene, 2.35, 3, 'CT-102') };

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  camera.position.set(6.5, 7.2, 9.5); camera.lookAt(0.25, 1.25, -0.4);

  let anim = null;
  function frame() { renderer.render(scene, camera); }
  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    // Fit the two tables (about 7.5 units wide in this projection) with breathing room on any aspect ratio.
    const aspect = w / h, needW = 4.8, needH = 2.8;
    let halfW = needW, halfH = needW / aspect;
    if (halfH < needH) { halfH = needH; halfW = needH * aspect; }
    Object.assign(camera, { left: -halfW, right: halfW, top: halfH, bottom: -halfH });
    camera.updateProjectionMatrix();
    frame();
  }
  new ResizeObserver(resize).observe(container);

  const targets = new Map(); // mesh -> {from,to}
  function animateTo(list) {
    if (anim) cancelAnimationFrame(anim);
    if (REDUCED) { for (const t of list) t.apply(1); frame(); return; }
    const start = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - start) / 320), e = 1 - Math.pow(1 - k, 3);
      for (const t of list) t.apply(e);
      frame();
      anim = k < 1 ? requestAnimationFrame(step) : null;
    };
    anim = requestAnimationFrame(step);
  }

  const white = new THREE.Color(C.white), red = new THREE.Color(C.red);
  function render(sessions, reservations) {
    const tweens = [];
    for (const s of sessions) {
      const t = tables[s.id]; if (!t) continue;
      const active = reservations.filter((r) => r.sessionId === s.id && r.status === 'active');
      for (const tag of t.tags) { t.root.remove(tag); tag.material.map.dispose(); tag.material.dispose(); }
      t.tags = [];
      t.chairs.forEach((ch, i) => {
        const taken = i < s.activeCount;
        for (const part of ch.parts) {
          const from = part.material.color.clone(), to = taken ? red : white;
          if (!from.equals(to)) tweens.push({ apply: (e) => part.material.color.copy(from).lerp(to, e) });
        }
        const who = active[i];
        if (taken && who) {
          const lbl = labelTexture(who.attendeeAlias.slice(0, 18), { size: 40, weight: 700, bg: '#ffffff', border: true, pad: 14 });
          const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: lbl.tex, depthTest: false }));
          sp.scale.set(0.34 * lbl.aspect, 0.34, 1);
          sp.position.set(ch.group.position.x, 1.62, ch.group.position.z);
          sp.renderOrder = 10; t.root.add(sp); t.tags.push(sp);
        }
      });
      const full = s.remainingSeats === 0;
      const wasOn = t.glow.intensity > 0.5;
      if (full !== wasOn) {
        tweens.push({ apply: (e) => {
          const k = full ? e : 1 - e;
          t.glow.intensity = 9 * k; t.pool.material.opacity = 0.38 * k;
          t.bulbMat.color.setHex(k > 0.5 ? C.sun : 0xcfcac0);
        } });
      }
    }
    if (tweens.length) animateTo(tweens); else frame();
  }

  // Pointer: a chair click preselects its session in the real form (no booking from the canvas).
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  canvas.addEventListener('click', (ev) => {
    const r = canvas.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    for (const t of Object.values(tables)) {
      const meshes = t.chairs.flatMap((c) => c.parts).concat([t.root.children[0]]);
      if (ray.intersectObjects(meshes, false).length) { if (onPick) onPick(t.id); return; }
    }
  });
  canvas.style.cursor = 'pointer';

  resize();
  return { render };
}
