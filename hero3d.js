// Escena 3D del hero: portal wireframe + partículas ambientales.
// Se degrada de forma silenciosa si Three.js no carga (red bloqueada, CDN caído, etc.).

(function () {
  if (typeof THREE === 'undefined') return;

  const canvas = document.getElementById('hero-3d');
  const heroSection = document.getElementById('inicio');
  if (!canvas || !heroSection) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COLORS = {
    red: 0xee3b2c,
    orange: 0xfa8523,
    teal: 0x1fc1b8,
    white: 0xeceff6,
  };

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  camera.position.set(0, 0, 9);

  // Portal: anillos concéntricos de wireframe.
  const portalGroup = new THREE.Group();
  const ringGeometries = [
    new THREE.TorusGeometry(2.6, 0.02, 8, 96),
    new THREE.TorusGeometry(2.1, 0.015, 8, 80),
    new THREE.TorusGeometry(3.1, 0.012, 8, 96),
  ];
  const ringColors = [COLORS.orange, COLORS.teal, COLORS.red];

  ringGeometries.forEach((geometry, i) => {
    const material = new THREE.MeshBasicMaterial({
      color: ringColors[i % ringColors.length],
      transparent: true,
      opacity: 0.55,
    });
    const ring = new THREE.Mesh(geometry, material);
    ring.rotation.x = Math.PI / 2 + i * 0.15;
    portalGroup.add(ring);
  });
  scene.add(portalGroup);

  // Núcleo del portal
  const coreGeometry = new THREE.IcosahedronGeometry(0.9, 1);
  const coreMaterial = new THREE.MeshBasicMaterial({
    color: COLORS.teal,
    wireframe: true,
    transparent: true,
    opacity: 0.75,
  });
  const core = new THREE.Mesh(coreGeometry, coreMaterial);
  scene.add(core);

  // Campo de partículas ambientales
  const PARTICLE_COUNT = 260;
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const radius = 4 + Math.random() * 6;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(Math.random() * 2 - 1);
    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.6;
    positions[i * 3 + 2] = radius * Math.cos(phi) - 4;
  }
  const particleGeometry = new THREE.BufferGeometry();
  particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const particleMaterial = new THREE.PointsMaterial({
    color: COLORS.white,
    size: 0.035,
    transparent: true,
    opacity: 0.55,
  });
  const particles = new THREE.Points(particleGeometry, particleMaterial);
  scene.add(particles);

  let targetX = 0;
  let targetY = 0;

  function onPointerMove(event) {
    const rect = heroSection.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
    targetX = x * 0.4;
    targetY = y * 0.25;
  }

  function resize() {
    const rect = heroSection.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function renderFrame() {
    renderer.render(scene, camera);
  }

  resize();
  window.addEventListener('resize', () => {
    resize();
    if (reducedMotion) renderFrame();
  });

  if (reducedMotion) {
    renderFrame();
    return;
  }

  heroSection.addEventListener('pointermove', onPointerMove);

  const clock = new THREE.Clock();

  function animate() {
    const elapsed = clock.getElapsedTime();

    portalGroup.rotation.z = elapsed * 0.08;
    core.rotation.x = elapsed * 0.25;
    core.rotation.y = elapsed * 0.18;
    particles.rotation.y = elapsed * 0.02;

    camera.position.x += (targetX - camera.position.x) * 0.03;
    camera.position.y += (-targetY - camera.position.y) * 0.03;
    camera.lookAt(0, 0, 0);

    renderFrame();
    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
})();
