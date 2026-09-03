// Escena 3D real (Three.js) del edificio de servicios: la cámara recorre
// un pasillo vertical de "salas" (una por planta), empezando por el techo,
// atravesando el forjado entre planta y planta (como cuando en una
// película la cámara pasa a través de una pared o un suelo, viéndose el
// material de cerca) hasta llegar a la siguiente. El contenido de cada
// planta es un panel HTML superpuesto (accesible, legible) que se muestra
// según la planta en la que esté la cámara. Se degrada en silencio si
// Three.js no carga, y respeta prefers-reduced-motion.

(function () {
  if (typeof THREE === 'undefined') return;

  const canvas = document.getElementById('building-3d');
  const sticky = document.getElementById('building-sticky');
  const scrollWrap = document.getElementById('building-scroll');
  const readout = document.getElementById('building-readout');
  const panels = Array.prototype.slice.call(document.querySelectorAll('.floor-panel'));
  if (!canvas || !sticky || !scrollWrap) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const PALETTE = {
    navyDeep: 0x071b33,
    navy: 0x0f2c4c,
    navySoft: 0x17395e,
    blue: 0x1c5d99,
    turquoise: 0x2ec4b6,
    turquoiseSoft: 0x8fe9de,
    white: 0xf4f8fb,
  };

  const FLOOR_COUNT = panels.length || 5;
  const SPACING = 16;
  const START_Z = 14;
  const END_Z = -((FLOOR_COUNT - 1) * SPACING) - 10;

  function floorZ(i) {
    return -i * SPACING;
  }

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(PALETTE.navyDeep, 12, 46);

  const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 100);
  camera.position.set(0, 0, START_Z);

  // ---------- Textura procedural para los forjados (sin imágenes externas):
  // un material veteado en los tonos de la marca, para que al atravesarlo
  // se vea de cerca como un material real. ----------
  function makeSlabTexture() {
    const size = 256;
    const c = document.createElement('canvas');
    c.width = size;
    c.height = size;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#0f2c4c';
    ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < 900; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = Math.random() * 1.6 + 0.3;
      const tone = Math.random();
      ctx.fillStyle = tone > 0.82
        ? 'rgba(143,233,222,0.5)'
        : tone > 0.6
          ? 'rgba(46,196,182,0.3)'
          : 'rgba(7,27,51,0.4)';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.strokeStyle = 'rgba(143,233,222,0.18)';
    ctx.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      ctx.beginPath();
      const y = (i + 0.5) * (size / 5) + (Math.random() - 0.5) * 14;
      ctx.moveTo(0, y);
      ctx.bezierCurveTo(size * 0.33, y + 18, size * 0.66, y - 18, size, y);
      ctx.stroke();
    }
    const texture = new THREE.CanvasTexture(c);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(3, 3);
    return texture;
  }

  const slabTexture = makeSlabTexture();

  // ---------- Jaula del ascensor: unas barras pegadas a la cámara, para
  // que sientas que vas dentro de un ascensor real mirando hacia fuera. ----------
  const cage = new THREE.Group();
  const cageMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.55 });
  const barGeom = new THREE.BoxGeometry(0.06, 2.4, 0.06);
  [-1.55, 1.55].forEach((x) => {
    const bar = new THREE.Mesh(barGeom, cageMat);
    bar.position.set(x, -0.3, -1.6);
    cage.add(bar);
  });
  const topBarGeom = new THREE.BoxGeometry(3.2, 0.06, 0.06);
  const topBar = new THREE.Mesh(topBarGeom, cageMat);
  topBar.position.set(0, 0.9, -1.6);
  cage.add(topBar);
  const sideRailGeom = new THREE.BoxGeometry(0.04, 0.04, 1.3);
  [-1.55, 1.55].forEach((x) => {
    [0.9, -1.5].forEach((y) => {
      const rail = new THREE.Mesh(sideRailGeom, cageMat);
      rail.position.set(x, y, -2.2);
      cage.add(rail);
    });
  });
  camera.add(cage);
  scene.add(camera);

  // ---------- Techo del edificio: lo primero que aparece ----------
  const roofGroup = new THREE.Group();
  const roofBeamMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.55 });
  const beamGeom = new THREE.BoxGeometry(16, 0.18, 0.18);
  [-0.7, 0, 0.7].forEach((offset, i) => {
    const beam = new THREE.Mesh(beamGeom, roofBeamMat);
    beam.rotation.z = i === 0 ? 0.5 : i === 2 ? -0.5 : 0;
    beam.position.set(0, 4 + offset * 2, START_Z - 1);
    roofGroup.add(beam);
  });
  const roofGlowGeom = new THREE.CircleGeometry(5, 40);
  const roofGlowMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoise, transparent: true, opacity: 0.3 });
  const roofGlow = new THREE.Mesh(roofGlowGeom, roofGlowMat);
  roofGlow.position.set(0, 3, START_Z - 6);
  roofGroup.add(roofGlow);
  scene.add(roofGroup);

  // ---------- Una "sala" en 3D por planta: suelo, techo y cuatro pilares ----------
  const FLOOR_TINTS = [PALETTE.turquoise, PALETTE.blue, PALETTE.turquoiseSoft, PALETTE.blue, PALETTE.turquoise];

  function buildRoom(i) {
    const group = new THREE.Group();
    const z = floorZ(i);
    const tint = FLOOR_TINTS[i % FLOOR_TINTS.length];

    const floorMat = new THREE.MeshBasicMaterial({ color: PALETTE.navySoft });
    const floorGeom = new THREE.BoxGeometry(13, 0.3, SPACING * 0.82);
    const floorMesh = new THREE.Mesh(floorGeom, floorMat);
    floorMesh.position.set(0, -2.6, z);
    group.add(floorMesh);

    const ceilingMesh = new THREE.Mesh(floorGeom, floorMat);
    ceilingMesh.position.set(0, 3.2, z);
    group.add(ceilingMesh);

    const pillarMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.85 });
    const pillarGeom = new THREE.BoxGeometry(0.5, 5.6, 0.5);
    [-5, 5].forEach((x) => {
      [z - 5.5, z + 5.5].forEach((pz) => {
        const pillar = new THREE.Mesh(pillarGeom, pillarMat);
        pillar.position.set(x, 0.2, pz);
        group.add(pillar);
      });
    });

    const glowGeom = new THREE.CircleGeometry(3.2, 32);
    const glowMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.16 });
    const glow = new THREE.Mesh(glowGeom, glowMat);
    glow.position.set(0, 0.4, z - 3.5);
    group.add(glow);

    scene.add(group);
  }

  for (let i = 0; i < FLOOR_COUNT; i++) buildRoom(i);

  // ---------- Forjados: el bloque que se atraviesa entre planta y planta ----------
  const slabMat = new THREE.MeshBasicMaterial({ map: slabTexture, side: THREE.DoubleSide });
  const slabGeom = new THREE.BoxGeometry(20, 16, SPACING * 0.34);

  function buildSlab(z) {
    const slab = new THREE.Mesh(slabGeom, slabMat);
    slab.position.set(0, 0, z);
    scene.add(slab);
  }

  buildSlab(START_Z - 6); // el propio techo se atraviesa para entrar a planta 1
  for (let i = 0; i < FLOOR_COUNT - 1; i++) {
    buildSlab((floorZ(i) + floorZ(i + 1)) / 2);
  }

  function resize() {
    const rect = sticky.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function applyProgress(progress) {
    const z = THREE.MathUtils.lerp(START_Z, END_Z, progress);
    camera.position.z = z;
    camera.lookAt(0, 0, z - 10);

    let nearestIndex = 0;
    let nearestDistance = Infinity;
    for (let i = 0; i < FLOOR_COUNT; i++) {
      const d = Math.abs(z - floorZ(i));
      if (d < nearestDistance) {
        nearestDistance = d;
        nearestIndex = i;
      }
      const panel = panels[i];
      if (panel) panel.classList.toggle('building-hidden', d >= SPACING * 0.32);
    }

    if (readout && panels[nearestIndex]) {
      readout.textContent = panels[nearestIndex].dataset.code || '';
    }
  }

  function renderFrame() {
    renderer.render(scene, camera);
  }

  resize();

  if (reducedMotion) {
    // Estado estático representativo: primera planta, sin scrollytelling.
    applyProgress(clamp01((START_Z - floorZ(0)) / (START_Z - END_Z)));
    renderFrame();
    window.addEventListener('resize', () => {
      resize();
      renderFrame();
    });
    return;
  }

  function getScrollProgress() {
    const rect = scrollWrap.getBoundingClientRect();
    const total = rect.height - window.innerHeight;
    if (total <= 0) return 1;
    return clamp01(-rect.top / total);
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      applyProgress(getScrollProgress());
      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', () => {
    resize();
    onScroll();
  });

  applyProgress(getScrollProgress());

  function animate() {
    renderFrame();
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
})();
