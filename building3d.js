// Escena 3D real (Three.js) del edificio de servicios: un dron desciende
// pegado a una fachada de cristal, mirando siempre de frente al fondo de
// cada sala (nunca en picado ni cenital — la cámara solo se mueve en
// vertical, con la mirada fija en horizontal). Al pasar de una planta a
// otra se atraviesa un forjado oscuro, con vigas, como el material
// estructural entre plantas. Un ascensor real (parte de la misma escena,
// no un elemento HTML aparte) baja pegado a la cámara, con su propio
// hueco, cabina y marcadores de planta. El contenido de cada planta es un
// panel HTML superpuesto (accesible, legible) que se muestra según la
// planta en la que esté la cámara. Se degrada en silencio si Three.js no
// carga, y respeta prefers-reduced-motion.

(function () {
  if (typeof THREE === 'undefined') return;

  const canvas = document.getElementById('building-3d');
  const sticky = document.getElementById('building-sticky');
  const view = document.getElementById('building-view');
  const scrollWrap = document.getElementById('building-scroll');
  const readout = document.getElementById('building-readout');
  const hint = document.getElementById('building-hint');
  const contactWrap = document.getElementById('contact-panel-wrap');
  const panels = Array.prototype.slice.call(document.querySelectorAll('.floor-panel'));
  if (!canvas || !sticky || !view || !scrollWrap) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Mismo punto de corte que el resto de la web (nav móvil, etc.). Se
  // calcula una sola vez al cargar: en móvil la sala se construye más
  // estrecha para que las paredes laterales lleguen al borde de la
  // pantalla en vez de quedar fuera de plano (el ancho de escritorio
  // desbordaría un encuadre vertical y estrecho).
  const isMobile = window.matchMedia('(max-width: 720px)').matches;

  const PALETTE = {
    void: 0x030a12,
    navyDeep: 0x071b33,
    navy: 0x0f2c4c,
    navySoft: 0x17395e,
    blue: 0x1c5d99,
    turquoise: 0x2ec4b6,
    turquoiseSoft: 0x8fe9de,
    white: 0xf4f8fb,
  };

  const FLOOR_COUNT = panels.length || 5;

  // ---------- Geometría vertical: cada planta es una sala con suelo,
  // techo, pared de fondo y paredes laterales; entre salas hay un forjado
  // oscuro que se atraviesa. Las salas son lo bastante anchas como para
  // que la pared lateral llegue al borde de la pantalla en escritorio. ----------
  const ROOM_WIDTH = isMobile ? 4.6 : 16;
  const ROOM_HEIGHT = 9; // alto libre de cada sala
  const SLAB_THICK = 1; // grosor del forjado entre plantas
  const SPACING = ROOM_HEIGHT + SLAB_THICK;
  const ROOM_DEPTH = 9; // de la fachada de cristal a la pared del fondo
  const CAMERA_Z = 7.5; // el dron vuela pegado a la fachada, fuera de la sala

  function roomCenterY(i) {
    return -i * SPACING;
  }
  function roomTopY(i) {
    return roomCenterY(i) + ROOM_HEIGHT / 2;
  }
  function roomBottomY(i) {
    return roomCenterY(i) - ROOM_HEIGHT / 2;
  }

  const START_Y = roomTopY(0) + 2.6; // empieza por encima de la azotea
  const FINAL_Y = roomCenterY(FLOOR_COUNT - 1); // el descenso termina en el centro de la última planta

  // El descenso ocupa el primer 80% del recorrido; el 20% final es el
  // "giro" hacia el panel de contacto (ver applyProgress). Empieza justo
  // al llegar a la última planta, no después.
  const P_TURN_START = 0.8;
  const VIEW_MIN_WIDTH = 0.56; // ancho de la vista del edificio una vez completado el giro

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(PALETTE.navyDeep, 9, 32);

  // La cámara solo se traslada en Y: al dejar la rotación en su valor por
  // defecto (mirando hacia -Z), la mirada queda siempre horizontal y de
  // frente al fondo de la sala — nunca en picado.
  const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 100);
  camera.position.set(0, START_Y, CAMERA_Z);

  // ---------- Textura procedural, oscura, para los forjados: de cerca se
  // ve el material real (vigas y veta oscura) al atravesarlos. ----------
  function makeSlabTexture() {
    const size = 256;
    const c = document.createElement('canvas');
    c.width = size;
    c.height = size;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#040a12';
    ctx.fillRect(0, 0, size, size);

    // Vigas horizontales oscuras, apenas más claras que el fondo.
    ctx.fillStyle = 'rgba(15, 44, 76, 0.55)';
    for (let i = 0; i < 4; i++) {
      const y = (i + 0.5) * (size / 4);
      ctx.fillRect(0, y - 6, size, 12);
    }

    for (let i = 0; i < 500; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = Math.random() * 1.3 + 0.2;
      const tone = Math.random();
      ctx.fillStyle = tone > 0.9
        ? 'rgba(143, 233, 222, 0.22)'
        : tone > 0.7
          ? 'rgba(28, 93, 153, 0.28)'
          : 'rgba(3, 10, 18, 0.5)';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    const texture = new THREE.CanvasTexture(c);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(3, 2);
    return texture;
  }

  const slabTexture = makeSlabTexture();

  // ---------- Azotea: lo primero que se ve, antes de bajar a la planta 1. ----------
  const roofGroup = new THREE.Group();
  const roofBeamMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.5 });
  const roofBeamGeom = new THREE.BoxGeometry(ROOM_WIDTH + 2, 0.16, 0.16);
  [-2.4, 0, 2.4].forEach((offsetZ) => {
    const beam = new THREE.Mesh(roofBeamGeom, roofBeamMat);
    beam.position.set(0, START_Y - 0.6, -offsetZ - 1);
    roofGroup.add(beam);
  });
  const roofGlowGeom = new THREE.CircleGeometry(4.6, 40);
  const roofGlowMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoise, transparent: true, opacity: 0.22 });
  const roofGlow = new THREE.Mesh(roofGlowGeom, roofGlowMat);
  roofGlow.position.set(0, START_Y - 1.4, -ROOM_DEPTH * 0.55);
  roofGroup.add(roofGlow);
  scene.add(roofGroup);

  // ---------- Una sala por planta: suelo, techo, pared de fondo y
  // paredes laterales, como una casa de muñecas con la fachada de cristal
  // hacia la cámara. ----------
  const FLOOR_TINTS = [PALETTE.turquoise, PALETTE.blue, PALETTE.turquoiseSoft, PALETTE.blue, PALETTE.turquoise];

  function buildRoom(i) {
    const group = new THREE.Group();
    const cy = roomCenterY(i);
    const tint = FLOOR_TINTS[i % FLOOR_TINTS.length];

    const slabMatSolid = new THREE.MeshBasicMaterial({ color: PALETTE.navySoft });
    const plateGeom = new THREE.BoxGeometry(ROOM_WIDTH, 0.2, ROOM_DEPTH);

    const floorMesh = new THREE.Mesh(plateGeom, slabMatSolid);
    floorMesh.position.set(0, roomBottomY(i), -ROOM_DEPTH / 2);
    group.add(floorMesh);

    const ceilingMesh = new THREE.Mesh(plateGeom, slabMatSolid);
    ceilingMesh.position.set(0, roomTopY(i), -ROOM_DEPTH / 2);
    group.add(ceilingMesh);

    // Pared de fondo: lo que siempre se ve de frente al mirar hacia -Z.
    const backWallMat = new THREE.MeshBasicMaterial({ color: PALETTE.navy });
    const backWallGeom = new THREE.PlaneGeometry(ROOM_WIDTH, ROOM_HEIGHT);
    const backWall = new THREE.Mesh(backWallGeom, backWallMat);
    backWall.position.set(0, cy, -ROOM_DEPTH);
    group.add(backWall);

    // Paredes laterales, bien opacas: cierran la sala y llegan hasta el
    // borde de la pantalla en la parte más próxima a la cámara.
    const sideMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.68 });
    const sideGeom = new THREE.BoxGeometry(0.15, ROOM_HEIGHT, ROOM_DEPTH);
    [-1, 1].forEach((dir) => {
      const side = new THREE.Mesh(sideGeom, sideMat);
      side.position.set(dir * (ROOM_WIDTH / 2), cy, -ROOM_DEPTH / 2);
      group.add(side);
    });

    // Acento luminoso en la pared de fondo, propio de cada planta.
    const glowGeom = new THREE.CircleGeometry(2.1, 32);
    const glowMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.4 });
    const glow = new THREE.Mesh(glowGeom, glowMat);
    glow.position.set(1.6, cy, -ROOM_DEPTH + 0.05);
    group.add(glow);

    scene.add(group);
  }

  for (let i = 0; i < FLOOR_COUNT; i++) buildRoom(i);

  // ---------- Forjados: el bloque oscuro con vigas que se atraviesa entre
  // planta y planta. ----------
  const slabMat = new THREE.MeshBasicMaterial({ map: slabTexture, side: THREE.DoubleSide });
  const slabGeom = new THREE.BoxGeometry(ROOM_WIDTH + 2, SLAB_THICK, ROOM_DEPTH + CAMERA_Z);

  function buildSlab(y) {
    const slab = new THREE.Mesh(slabGeom, slabMat);
    slab.position.set(0, y, (CAMERA_Z - ROOM_DEPTH) / 2 - 1);
    scene.add(slab);
  }

  for (let i = 0; i < FLOOR_COUNT - 1; i++) {
    buildSlab((roomBottomY(i) + roomTopY(i + 1)) / 2);
  }

  // ---------- Ascensor real: un hueco integrado en el propio edificio,
  // pegado a la pared izquierda de cada sala, con su cabina bajando junto
  // a la cámara. Se construye una sola vez, como una estructura continua
  // que recorre todo el edificio. ----------
  const SHAFT_X = -(ROOM_WIDTH / 2) + 1.7;
  const SHAFT_Z = -1.3;
  const CABIN_HEIGHT = 1.9;
  // El hueco del ascensor (raíles y cabina) se limita al techo y al suelo
  // reales del edificio (con un pequeño margen) para que nunca sobresalga.
  const RAIL_TOP = roomTopY(0) - 0.1;
  const RAIL_BOTTOM = roomBottomY(FLOOR_COUNT - 1) + 0.1;
  const SHAFT_TOP = RAIL_TOP - CABIN_HEIGHT / 2;
  const SHAFT_BOTTOM = RAIL_BOTTOM + CABIN_HEIGHT / 2;

  const elevatorGroup = new THREE.Group();

  const shaftBackMat = new THREE.MeshBasicMaterial({ color: PALETTE.void });
  const shaftBack = new THREE.Mesh(
    new THREE.BoxGeometry(1.9, RAIL_TOP - RAIL_BOTTOM, 0.2),
    shaftBackMat
  );
  shaftBack.position.set(SHAFT_X, (RAIL_TOP + RAIL_BOTTOM) / 2, SHAFT_Z - 0.7);
  elevatorGroup.add(shaftBack);

  const railMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.55 });
  const railGeom = new THREE.BoxGeometry(0.08, RAIL_TOP - RAIL_BOTTOM, 0.08);
  [-0.85, 0.85].forEach((dx) => {
    const rail = new THREE.Mesh(railGeom, railMat);
    rail.position.set(SHAFT_X + dx, (RAIL_TOP + RAIL_BOTTOM) / 2, SHAFT_Z);
    elevatorGroup.add(rail);
  });

  // Un pequeño marcador por planta, a la altura de cada sala, como los
  // indicadores de piso de un ascensor real.
  for (let i = 0; i < FLOOR_COUNT; i++) {
    const tint = FLOOR_TINTS[i % FLOOR_TINTS.length];
    const markMat = new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.75 });
    const mark = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.08, 0.08), markMat);
    mark.position.set(SHAFT_X, roomCenterY(i), SHAFT_Z + 0.15);
    elevatorGroup.add(mark);
  }

  const cabinMat = new THREE.MeshBasicMaterial({ color: PALETTE.navy, transparent: true, opacity: 0.85 });
  const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.4, CABIN_HEIGHT, 1.1), cabinMat);
  cabin.position.set(SHAFT_X, THREE.MathUtils.clamp(START_Y, SHAFT_BOTTOM, SHAFT_TOP), SHAFT_Z);
  elevatorGroup.add(cabin);

  const cabinEdges = new THREE.LineSegments(
    new THREE.EdgesGeometry(cabin.geometry),
    new THREE.LineBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.9 })
  );
  cabin.add(cabinEdges);

  const cabinGlowMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoise, transparent: true, opacity: 0.3 });
  const cabinGlow = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.6), cabinGlowMat);
  cabinGlow.position.set(0, 0, 0.56);
  cabin.add(cabinGlow);

  scene.add(elevatorGroup);

  function resize() {
    // El ancho de referencia es el de `.building-view` (no el de toda
    // `.building-sticky`): durante el giro final se encoge hacia la
    // izquierda, y el lienzo tiene que reencuadrarse a juego.
    const rect = view.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    // El ascensor solo cabe en el encuadre en pantallas anchas; en
    // vertical/móvil (o ya encogido por el giro) el propio campo de
    // visión lo deja fuera de plano.
    elevatorGroup.visible = width / height > 0.9;
  }

  let lastTurnEased = -1; // fuerza el primer resize() de la vista del edificio

  function applyProgress(progress) {
    const descentP = clamp01(progress / P_TURN_START);
    const y = THREE.MathUtils.lerp(START_Y, FINAL_Y, descentP);
    camera.position.y = y;
    cabin.position.y = THREE.MathUtils.clamp(y, SHAFT_BOTTOM, SHAFT_TOP);

    let nearestIndex = 0;
    let nearestDistance = Infinity;
    for (let i = 0; i < FLOOR_COUNT; i++) {
      const d = Math.abs(y - roomCenterY(i));
      if (d < nearestDistance) {
        nearestDistance = d;
        nearestIndex = i;
      }
      const panel = panels[i];
      if (panel) panel.classList.toggle('building-hidden', d >= ROOM_HEIGHT / 2 + 0.35);
    }

    if (readout && panels[nearestIndex]) {
      readout.textContent = panels[nearestIndex].dataset.code || '';
    }

    // Giro final: al llegar a la última planta, el edificio encoge hacia
    // la izquierda y el panel de contacto entra desde la derecha, sin
    // soltar el scroll-jacking (el edificio se queda siempre a la vista).
    const turnP = clamp01((progress - P_TURN_START) / (1 - P_TURN_START));
    const turnEased = 1 - Math.pow(1 - turnP, 3);

    // El redimensionado del lienzo (resize()) fuerza un layout síncrono,
    // así que solo se repite mientras el ancho esté realmente cambiando
    // (el tramo del giro), no en cada scroll de los otros tramos.
    if (turnEased !== lastTurnEased) {
      view.style.width = (1 - turnEased * (1 - VIEW_MIN_WIDTH)) * 100 + '%';
      resize();
      lastTurnEased = turnEased;
    }

    if (contactWrap) {
      contactWrap.style.transform = `translateX(${(1 - turnEased) * 100}%)`;
      contactWrap.style.opacity = String(0.25 + turnEased * 0.75);
    }
    if (hint) {
      hint.style.opacity = String(1 - turnEased);
    }
  }

  function renderFrame() {
    renderer.render(scene, camera);
  }

  resize();

  if (reducedMotion) {
    // Estado estático representativo: primera planta, sin scrollytelling.
    applyProgress(0);
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
