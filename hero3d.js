// Escena 3D del hero: una puerta art decó que se abre a medida que haces scroll,
// como si avanzaras hacia ella. Se degrada en silencio si Three.js no carga
// (CDN caído, red bloqueada...) y respeta prefers-reduced-motion.

(function () {
  if (typeof THREE === 'undefined') return;

  const canvas = document.getElementById('hero-3d');
  const sticky = document.getElementById('hero-sticky');
  const scrollWrap = document.getElementById('hero-scroll');
  const heroInner = document.getElementById('hero-inner');
  if (!canvas || !sticky || !scrollWrap) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const PALETTE = {
    navyDeep: 0x08213b,
    navy: 0x123a63,
    blue: 0x1c5d99,
    turquoise: 0x2ec4b6,
    turquoiseSoft: 0x7fe0d6,
    white: 0xf4f8fb,
  };

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.set(0, 0.2, 14);

  // Halo turquesa al fondo, tras la puerta.
  const haloGeometry = new THREE.CircleGeometry(4.2, 48);
  const haloMaterial = new THREE.MeshBasicMaterial({
    color: PALETTE.turquoise,
    transparent: true,
    opacity: 0.25,
  });
  const halo = new THREE.Mesh(haloGeometry, haloMaterial);
  halo.position.z = -3;
  scene.add(halo);

  // Marco de la puerta (arco escalonado art decó).
  const frameGroup = new THREE.Group();
  const frameMaterial = new THREE.MeshBasicMaterial({ color: PALETTE.white, transparent: true, opacity: 0.9 });
  const frameTiers = [
    { w: 5.6, h: 7.6, y: 0 },
    { w: 5.0, h: 8.2, y: 0.3 },
    { w: 4.4, h: 8.7, y: 0.55 },
  ];
  frameTiers.forEach((tier) => {
    const shape = new THREE.Shape();
    const hw = tier.w / 2;
    shape.moveTo(-hw, -tier.h / 2 + tier.y);
    shape.lineTo(-hw, tier.h / 2 - 0.6 + tier.y);
    shape.lineTo(0, tier.h / 2 + tier.y);
    shape.lineTo(hw, tier.h / 2 - 0.6 + tier.y);
    shape.lineTo(hw, -tier.h / 2 + tier.y);
    const points = shape.getPoints(40);
    const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.LineLoop(lineGeom, new THREE.LineBasicMaterial({ color: PALETTE.white, transparent: true, opacity: 0.35 }));
    frameGroup.add(line);
  });
  scene.add(frameGroup);

  // Abanico / sunburst sobre el dintel.
  const sunburstGroup = new THREE.Group();
  const rayCount = 13;
  for (let i = 0; i < rayCount; i++) {
    const t = i / (rayCount - 1);
    const angle = THREE.MathUtils.lerp(Math.PI * 0.12, Math.PI * 0.88, t);
    const rayGeom = new THREE.PlaneGeometry(0.09, 2.6);
    const color = i % 2 === 0 ? PALETTE.turquoiseSoft : PALETTE.white;
    const rayMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
    const ray = new THREE.Mesh(rayGeom, rayMat);
    ray.position.set(Math.cos(angle) * 1.3, 3.9 + Math.sin(angle) * 1.3, -0.2);
    ray.rotation.z = angle - Math.PI / 2;
    sunburstGroup.add(ray);
  }
  scene.add(sunburstGroup);

  // Hojas de la puerta (dos paneles con ojo de buey), cada una pivotando
  // sobre su bisagra exterior: el Group se posiciona en la bisagra (mundo) y
  // todo su contenido se desplaza hacia el centro en espacio local, para que
  // group.rotation.y pivote correctamente al abrir.
  const LEAF_WIDTH = 2.1;

  function buildDoorPanel(sign) {
    const hingeX = sign * (LEAF_WIDTH + 0.1);
    const localCenterX = -sign * (LEAF_WIDTH / 2);

    const group = new THREE.Group();
    group.position.set(hingeX, -0.2, 0.3);

    const panelGeom = new THREE.PlaneGeometry(LEAF_WIDTH, 6.4);
    const panelMat = new THREE.MeshBasicMaterial({ color: PALETTE.navy, transparent: true, opacity: 0.94, side: THREE.DoubleSide });
    const panel = new THREE.Mesh(panelGeom, panelMat);
    panel.position.x = localCenterX;
    group.add(panel);

    const borderGeom = new THREE.EdgesGeometry(new THREE.PlaneGeometry(LEAF_WIDTH - 0.2, 6.1));
    const border = new THREE.LineSegments(borderGeom, new THREE.LineBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.7 }));
    border.position.set(localCenterX, 0, 0.01);
    group.add(border);

    const portholeGeom = new THREE.RingGeometry(0.55, 0.62, 32);
    const portholeMat = new THREE.MeshBasicMaterial({ color: PALETTE.white, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
    const porthole = new THREE.Mesh(portholeGeom, portholeMat);
    porthole.position.set(localCenterX, 1.6, 0.02);
    group.add(porthole);

    for (let i = -1; i <= 1; i++) {
      const fluteGeom = new THREE.PlaneGeometry(0.03, 4.6);
      const fluteMat = new THREE.MeshBasicMaterial({ color: PALETTE.turquoiseSoft, transparent: true, opacity: 0.35 });
      const flute = new THREE.Mesh(fluteGeom, fluteMat);
      flute.position.set(localCenterX + i * 0.5, -0.6, 0.015);
      group.add(flute);
    }

    return group;
  }

  const doorLeft = buildDoorPanel(-1);
  const doorRight = buildDoorPanel(1);
  scene.add(doorLeft, doorRight);

  // Toda la escena (puerta, marco, abanico, halo) se ensancha y se
  // achata: la puerta pasa de proporción "vertical" a una más panorámica,
  // para que quepa a lo ancho de una pantalla de PC sin recortar tanto el
  // alto. Todo lo demás está expresado en coordenadas locales sin escalar.
  const SCALE_X = 1.55;
  const SCALE_Y = 0.62;
  scene.scale.set(SCALE_X, SCALE_Y, 1);
  const LOOK_AT_Y = 0.6 * SCALE_Y;

  // Ancho real (ya escalado) del marco exterior de la puerta — el elemento
  // más ancho de la escena — usado para calcular a qué distancia debe
  // llegar la cámara para que ocupe todo el ancho de la pantalla en PC.
  const FRAME_WIDTH = 5.6 * SCALE_X;
  const DOOR_Z = 0.3;
  const FAR_Z = 14;
  const SAFETY = 0.68; // <1: la puerta rebasa el encuadre con margen, en vez de quedarse justa

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
  }

  function lerpInverse(a, b, t) {
    return 1 / THREE.MathUtils.lerp(1 / a, 1 / b, t);
  }

  // Distancia de cámara, según el aspect ratio actual, a la que la puerta
  // (cerrada) llena el ancho del encuadre sin dejar hueco a los lados.
  let closeZ = 3.2;
  function computeCloseZ() {
    const vFov = THREE.MathUtils.degToRad(camera.fov);
    const halfTan = Math.tan(vFov / 2);
    const exactFitDistance = FRAME_WIDTH / (2 * halfTan * camera.aspect);
    return clamp(exactFitDistance * SAFETY + DOOR_Z, 2.2, 7);
  }

  function resize() {
    const rect = sticky.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    closeZ = computeCloseZ();
  }

  function applyProgress(progress) {
    // La puerta empieza a abrirse casi desde el primer scroll, para que no
    // haga falta "esperar" antes de sentir que entras.
    const t = clamp01(progress / 0.85);
    const openAngle = t * (Math.PI * 0.58);
    doorLeft.rotation.y = openAngle;
    doorRight.rotation.y = -openAngle;

    // Interpolar en distancia inversa (en vez de lineal) para que el
    // acercamiento se note ya desde el primer scroll: en perspectiva, el
    // tamaño aparente crece con 1/distancia, así que una interpolación
    // lineal de la posición se siente "muerta" al principio.
    camera.position.z = lerpInverse(FAR_Z, closeZ, t);
    camera.position.y = THREE.MathUtils.lerp(0.2, 0.4, progress);
    camera.lookAt(0, LOOK_AT_Y, 0);

    haloMaterial.opacity = 0.15 + t * 0.35;
    sunburstGroup.children.forEach((ray, i) => {
      ray.material.opacity = 0.3 + t * 0.5 + (i % 3 === 0 ? 0.1 : 0);
    });

    if (heroInner) {
      const fade = 1 - clamp01(progress / 0.4);
      heroInner.style.opacity = fade.toFixed(2);
      heroInner.style.pointerEvents = fade < 0.05 ? 'none' : 'auto';
    }
  }

  function renderFrame() {
    renderer.render(scene, camera);
  }

  resize();

  if (reducedMotion) {
    // Estado estático: puerta abierta, sin scrollytelling ni animación continua.
    applyProgress(1);
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
