/**
 * Food Waste Prediction – Real 3D Sustainability Scene with Scroll-Driven Motion
 * Powered by Three.js & GSAP ScrollTrigger
 */

(function () {
  'use strict';

  // Check if WebGL is supported
  function isWebGLAvailable() {
    try {
      const canvas = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  }

  // Check user preference for reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Global variables
  let scene, camera, renderer;
  let leafGroup, mainLeafMesh, stemMesh, particlesSystem;
  let secondaryLeaf1, secondaryLeaf2;
  let veinTexture;
  let animFrameId = null;
  let isTabVisible = true;
  let scrollTimeline = null;

  // Base state values interpolated by GSAP
  const leafTransform = {
    x: 2.2,
    y: 0.9,
    z: 0.2,
    rotX: 0.35,
    rotY: 0.45,
    rotZ: -0.15,
    scale: 1.15,
    particleSpeed: 0.008,
    particleDispersion: 1.0
  };

  // Micro-idle floating state
  let clock = null;

  /**
   * Generates a procedural botanical vein texture on a 512x512 canvas.
   * Creates realistic primary midrib and secondary lateral veins.
   */
  function createBotanicalVeinTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    // Base background gradient
    const bgGrad = ctx.createLinearGradient(0, 0, 0, 512);
    bgGrad.addColorStop(0, '#10b981');
    bgGrad.addColorStop(0.5, '#059669');
    bgGrad.addColorStop(1, '#047857');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 512, 512);

    // Primary central midrib vein
    ctx.strokeStyle = 'rgba(167, 243, 208, 0.85)';
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(256, 500);
    ctx.bezierCurveTo(256, 360, 256, 160, 256, 20);
    ctx.stroke();

    // Secondary lateral veins (branching naturally at ~45 degrees)
    const veinPairs = 12;
    for (let i = 0; i < veinPairs; i++) {
      const t = 0.12 + (i / veinPairs) * 0.76;
      const yAnchor = 490 - t * 470;
      const length = Math.sin(t * Math.PI) * 160;
      const curveUp = 28;

      ctx.lineWidth = Math.max(2, 6 * (1 - t * 0.5));
      ctx.strokeStyle = `rgba(167, 243, 208, ${0.45 + (1 - t) * 0.35})`;

      // Right branching vein
      ctx.beginPath();
      ctx.moveTo(256, yAnchor);
      ctx.quadraticCurveTo(256 + length * 0.55, yAnchor - curveUp * 0.6, 256 + length, yAnchor - curveUp);
      ctx.stroke();

      // Left branching vein
      ctx.beginPath();
      ctx.moveTo(256, yAnchor);
      ctx.quadraticCurveTo(256 - length * 0.55, yAnchor - curveUp * 0.6, 256 - length, yAnchor - curveUp);
      ctx.stroke();

      // Fine sub-vein branches (reticulations)
      if (i > 1 && i < veinPairs - 1) {
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = 'rgba(209, 250, 229, 0.3)';
        ctx.beginPath();
        ctx.moveTo(256 + length * 0.45, yAnchor - curveUp * 0.4);
        ctx.lineTo(256 + length * 0.75, yAnchor - curveUp * 0.9);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(256 - length * 0.45, yAnchor - curveUp * 0.4);
        ctx.lineTo(256 - length * 0.75, yAnchor - curveUp * 0.9);
        ctx.stroke();
      }
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  /**
   * Constructs the realistic 3D Leaf mesh with botanical shape,
   * 3D curvature (spine arch & midrib V-fold), and tapering petiole stem.
   */
  function create3DLeaf() {
    const group = new THREE.Group();

    // 1. Organic Leaf Blade Shape
    const shape = new THREE.Shape();
    // Petiole junction at base
    shape.moveTo(0, -1.8);
    // Right contour: curves outward into blade, then sharpens towards tip
    shape.bezierCurveTo(0.55, -1.5, 1.35, -0.4, 1.35, 0.4);
    shape.bezierCurveTo(1.35, 1.1, 0.75, 1.75, 0, 2.35); // Sharp apex
    // Left contour: symmetrical natural curve back to base
    shape.bezierCurveTo(-0.75, 1.75, -1.35, 1.1, -1.35, 0.4);
    shape.bezierCurveTo(-1.35, -0.4, -0.55, -1.5, 0, -1.8);

    // Extrude geometry with bevel to give realistic organic thickness
    const extrudeSettings = {
      depth: 0.035,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 2,
      bevelSize: 0.02,
      bevelThickness: 0.02
    };

    const leafGeo = new THREE.ExtrudeGeometry(shape, extrudeSettings);

    // 2. Deform geometry in 3D: natural spine arch, V-curl along midrib, and edge waves
    const pos = leafGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const z = pos.getZ(i);

      // Spine arch along Y: curves backwards slightly near tip and base
      const normalizedY = (y + 1.8) / 4.15; // 0 to 1
      const arch = Math.sin(normalizedY * Math.PI) * 0.38;

      // Midrib V-fold: parabolic cross-sectional curl along X
      const vFold = (x * x) * 0.22;

      // Organic edge ripples
      const ripple = Math.sin(y * 5.5) * 0.035 * Math.abs(x);

      pos.setZ(i, z + arch + vFold + ripple);
    }
    leafGeo.computeVertexNormals();

    // Leaf Blade Material (MeshPhysicalMaterial with clearcoat & silky botanical sheen)
    veinTexture = createBotanicalVeinTexture();
    const leafMaterial = new THREE.MeshPhysicalMaterial({
      color: 0x10b981,
      roughness: 0.28,
      metalness: 0.04,
      clearcoat: 0.65,
      clearcoatRoughness: 0.18,
      sheen: 0.75,
      sheenColor: new THREE.Color(0xa7f3d0),
      sheenRoughness: 0.25,
      bumpMap: veinTexture,
      bumpScale: 0.04,
      side: THREE.DoubleSide
    });

    mainLeafMesh = new THREE.Mesh(leafGeo, leafMaterial);
    mainLeafMesh.castShadow = true;
    mainLeafMesh.receiveShadow = true;
    group.add(mainLeafMesh);

    // 3. Central Stem (Petiole + Midrib)
    const stemCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, -2.4, -0.08), // Base petiole
      new THREE.Vector3(0, -1.8, 0.0),
      new THREE.Vector3(0, -0.5, 0.32),
      new THREE.Vector3(0, 0.8, 0.36),
      new THREE.Vector3(0, 1.8, 0.22),
      new THREE.Vector3(0, 2.3, 0.05)   // Near apex tip
    ]);

    const stemGeo = new THREE.TubeGeometry(stemCurve, 36, 0.045, 10, false);
    // Taper the stem so it is thicker at base and slender at tip
    const stemPos = stemGeo.attributes.position;
    for (let i = 0; i < stemPos.count; i++) {
      const y = stemPos.getY(i);
      const taper = Math.max(0.25, 1.0 - (y + 2.4) / 4.7 * 0.72);
      stemPos.setX(i, stemPos.getX(i) * taper);
      stemPos.setZ(i, stemPos.getZ(i) * taper);
    }
    stemGeo.computeVertexNormals();

    const stemMat = new THREE.MeshStandardMaterial({
      color: 0x047857,
      roughness: 0.45,
      metalness: 0.04
    });

    stemMesh = new THREE.Mesh(stemGeo, stemMat);
    group.add(stemMesh);

    return group;
  }

  /**
   * Constructs secondary smaller decorative floating leaves in the distance
   * for enhanced depth and multi-layer parallax.
   */
  function createSecondaryLeaf(scale = 0.45, color = 0x34d399) {
    const shape = new THREE.Shape();
    shape.moveTo(0, -1.5);
    shape.bezierCurveTo(0.6, -1.0, 1.0, 0.0, 1.0, 0.5);
    shape.bezierCurveTo(1.0, 1.1, 0.5, 1.5, 0, 2.0);
    shape.bezierCurveTo(-0.5, 1.5, -1.0, 1.1, -1.0, 0.5);
    shape.bezierCurveTo(-1.0, 0.0, -0.6, -1.0, 0, -1.5);

    const geo = new THREE.ShapeGeometry(shape, 16);
    const mat = new THREE.MeshStandardMaterial({
      color: color,
      roughness: 0.5,
      metalness: 0.05,
      transparent: true,
      opacity: 0.75,
      side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.scale.set(scale, scale, scale);
    return mesh;
  }

  /**
   * Constructs the orbiting green / dew particles field
   */
  function createOrbitingParticles() {
    const particleCount = 48;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);
    const angles = new Float32Array(particleCount);
    const radii = new Float32Array(particleCount);
    const heights = new Float32Array(particleCount);
    const speeds = new Float32Array(particleCount);

    const colorPalette = [
      new THREE.Color(0x10b981), // Emerald
      new THREE.Color(0x6ee7b7), // Mint
      new THREE.Color(0xa7f3d0), // Light jade
      new THREE.Color(0xfef08a)  // Dew golden highlight
    ];

    for (let i = 0; i < particleCount; i++) {
      angles[i] = Math.random() * Math.PI * 2;
      radii[i] = 1.4 + Math.random() * 2.2;
      heights[i] = (Math.random() - 0.5) * 4.0;
      speeds[i] = 0.4 + Math.random() * 0.8;
      scales[i] = 0.035 + Math.random() * 0.055;

      const c = colorPalette[Math.floor(Math.random() * colorPalette.length)];
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;

      positions[i * 3] = Math.cos(angles[i]) * radii[i];
      positions[i * 3 + 1] = heights[i];
      positions[i * 3 + 2] = Math.sin(angles[i]) * radii[i];
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Particle sprite using procedural soft radial circle
    const pCanvas = document.createElement('canvas');
    pCanvas.width = 64;
    pCanvas.height = 64;
    const pCtx = pCanvas.getContext('2d');
    const grad = pCtx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.3, 'rgba(167, 243, 208, 0.85)');
    grad.addColorStop(0.7, 'rgba(16, 185, 129, 0.4)');
    grad.addColorStop(1, 'rgba(16, 185, 129, 0)');
    pCtx.fillStyle = grad;
    pCtx.fillRect(0, 0, 64, 64);

    const pTexture = new THREE.CanvasTexture(pCanvas);

    const material = new THREE.PointsMaterial({
      size: 0.16,
      map: pTexture,
      transparent: true,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const points = new THREE.Points(geometry, material);
    points.userData = { angles, radii, heights, speeds, particleCount };
    return points;
  }

  /**
   * Updates particle positions in the animation loop
   */
  function updateParticles(elapsedTime) {
    if (!particlesSystem) return;
    const { angles, radii, heights, speeds, particleCount } = particlesSystem.userData;
    const pos = particlesSystem.geometry.attributes.position;
    const spd = leafTransform.particleSpeed;
    const disp = leafTransform.particleDispersion;

    for (let i = 0; i < particleCount; i++) {
      angles[i] += speeds[i] * spd;
      const currentRadius = radii[i] * disp;
      const x = Math.cos(angles[i]) * currentRadius;
      const z = Math.sin(angles[i]) * currentRadius;
      const y = heights[i] + Math.sin(elapsedTime * 1.5 + angles[i]) * 0.2;

      pos.setXYZ(i, x, y, z);
    }
    pos.needsUpdate = true;
  }

  /**
   * Initializes the Three.js 3D scene, lights, and objects
   */
  function initThreeScene() {
    const container = document.getElementById('three-scene-container');
    const canvas = document.getElementById('three-canvas');
    if (!container || !canvas) return;

    if (!isWebGLAvailable()) {
      console.warn('WebGL not available, activating fallback leaf.');
      const fallback = document.getElementById('webgl-fallback-leaf');
      if (fallback) fallback.style.display = 'block';
      return;
    }

    clock = new THREE.Clock();

    // Scene
    scene = new THREE.Scene();

    // Camera
    const aspect = window.innerWidth / window.innerHeight;
    camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
    camera.position.set(0, 0, 7.2);

    // Renderer
    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xf0fdf4, 1.4);
    dirLight.position.set(5, 7, 5);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    // Rim point light for glowing emerald silhouette
    const rimLight = new THREE.PointLight(0x10b981, 2.0, 18);
    rimLight.position.set(-4, -1, 4);
    scene.add(rimLight);

    const accentLight = new THREE.PointLight(0x34d399, 1.2, 14);
    accentLight.position.set(3, 4, 3);
    scene.add(accentLight);

    // Create 3D Leaf
    leafGroup = create3DLeaf();
    scene.add(leafGroup);

    // Create Orbiting Particles
    particlesSystem = createOrbitingParticles();
    leafGroup.add(particlesSystem);

    // Secondary floating depth elements (parallax background)
    secondaryLeaf1 = createSecondaryLeaf(0.5, 0x34d399);
    secondaryLeaf1.position.set(-3.6, 2.0, -2.5);
    secondaryLeaf1.rotation.set(0.4, 0.2, 0.8);
    scene.add(secondaryLeaf1);

    secondaryLeaf2 = createSecondaryLeaf(0.38, 0x10b981);
    secondaryLeaf2.position.set(3.8, -2.5, -3.0);
    secondaryLeaf2.rotation.set(-0.3, 0.5, -0.6);
    scene.add(secondaryLeaf2);

    // Check if on Auth Page (login/register) vs Dashboard/Analysis Page
    const isAuthPage = document.body.classList.contains('auth-page');
    if (isAuthPage) {
      setupAuthPageTransform();
    } else {
      setupScrollTriggerTimelines();
    }

    // Attach Event Listeners
    window.addEventListener('resize', onWindowResize);
    document.addEventListener('visibilitychange', onVisibilityChange);

    // Start RAF loop
    tick();
  }

  /**
   * Dedicated transform & mouse tracking for Auth pages (Login & Register)
   */
  function setupAuthPageTransform() {
    // Initial hero pose on auth page
    leafTransform.x = 1.9;
    leafTransform.y = 0.2;
    leafTransform.z = 0.3;
    leafTransform.scale = 1.25;
    leafTransform.rotX = 0.2;
    leafTransform.rotY = 0.6;
    leafTransform.rotZ = -0.1;

    // Responsive position on smaller screens
    if (window.innerWidth < 900) {
      leafTransform.x = 0;
      leafTransform.y = 1.8;
      leafTransform.scale = 0.85;
    }

    // Subtle interactive tilt responding to mouse move on auth page
    if (!prefersReducedMotion && window.matchMedia('(hover: hover)').matches) {
      document.addEventListener('mousemove', (e) => {
        const mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        const mouseY = -(e.clientY / window.innerHeight) * 2 + 1;

        if (window.gsap) {
          gsap.to(leafTransform, {
            rotY: 0.6 + mouseX * 0.45,
            rotX: 0.2 - mouseY * 0.35,
            duration: 0.8,
            ease: 'power2.out'
          });
        }
      });
    }

    // If there is any scrollable height, tie subtle scrub
    if (window.gsap && window.ScrollTrigger) {
      gsap.to(leafTransform, {
        scrollTrigger: {
          trigger: document.body,
          start: 'top top',
          end: 'bottom bottom',
          scrub: 1.2
        },
        y: -0.5,
        rotY: Math.PI * 0.8,
        rotZ: 0.3
      });
    }
  }

  /**
   * Sets up cinematic GSAP ScrollTrigger timeline for continuous 3D transformations
   * tied directly to scroll progress and fully bidirectional.
   */
  function setupScrollTriggerTimelines() {
    if (!window.gsap || !window.ScrollTrigger) {
      console.warn('GSAP or ScrollTrigger not loaded, running idle 3D mode.');
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    const isMobile = window.innerWidth <= 768;
    const screenAspect = window.innerWidth / window.innerHeight;
    const desktopX = Math.min(3.6, Math.max(2.5, screenAspect * 1.75));
    const baseTargetX = isMobile ? 1.0 : desktopX;

    // Set initial hero state
    leafTransform.x = baseTargetX;
    leafTransform.y = 1.05;
    leafTransform.z = 0.2;
    leafTransform.scale = isMobile ? 0.8 : 1.15;
    leafTransform.rotX = 0.25;
    leafTransform.rotY = 0.5;
    leafTransform.rotZ = -0.15;

    // Master Scroll-Driven 3D Scrub Timeline
    scrollTimeline = gsap.timeline({
      scrollTrigger: {
        trigger: '.content-container',
        start: 'top top+=80',
        end: 'bottom bottom',
        scrub: 1.2,
        invalidateOnRefresh: true
      }
    });

    // Stage 1: As user scrolls into Stat Metrics
    // Leaf rotates around multiple axes, glides smoothly sideways to frame content, adjusts scale for depth
    scrollTimeline.to(leafTransform, {
      x: isMobile ? 1.2 : desktopX + 0.35,
      y: 0.25,
      z: -0.4,
      scale: isMobile ? 0.7 : 1.0,
      rotX: 0.85,
      rotY: Math.PI * 0.75, // Rotates 135 degrees to reveal spine & veins
      rotZ: 0.3,
      particleSpeed: 0.016,
      particleDispersion: 1.35,
      duration: 1.5,
      ease: 'power1.inOut'
    });

    // Stage 2: As user reaches Charts & Data Visualizations
    // Leaf glides gracefully across, turns to showcase curved midrib and 3D surface
    scrollTimeline.to(leafTransform, {
      x: isMobile ? 0.6 : Math.max(1.8, desktopX - 0.7),
      y: -0.6,
      z: 0.3,
      scale: isMobile ? 0.65 : 0.88,
      rotX: 0.35,
      rotY: Math.PI * 1.5, // 270 degree rotation
      rotZ: -0.4,
      particleSpeed: 0.02,
      particleDispersion: 1.15,
      duration: 2.0,
      ease: 'power1.inOut'
    });

    // Stage 3: As user reaches Food Records table or lower footer
    // Leaf transitions into an elegant smaller decorative element
    scrollTimeline.to(leafTransform, {
      x: isMobile ? 1.0 : desktopX + 0.2,
      y: -1.7,
      z: -0.6,
      scale: isMobile ? 0.5 : 0.68,
      rotX: 0.5,
      rotY: Math.PI * 2.2,
      rotZ: 0.1,
      particleSpeed: 0.01,
      particleDispersion: 0.9,
      duration: 1.5,
      ease: 'power1.inOut'
    });

    // Parallax background secondary leaf movement
    if (secondaryLeaf1 && secondaryLeaf2) {
      gsap.to(secondaryLeaf1.position, {
        scrollTrigger: {
          trigger: '.content-container',
          start: 'top top',
          end: 'bottom bottom',
          scrub: 2.0
        },
        y: -1.0,
        x: -2.8,
        ease: 'none'
      });

      gsap.to(secondaryLeaf2.position, {
        scrollTrigger: {
          trigger: '.content-container',
          start: 'top top',
          end: 'bottom bottom',
          scrub: 1.5
        },
        y: 1.5,
        x: 4.2,
        ease: 'none'
      });
    }

    // Parallax DOM orbs movement
    const orb1 = document.querySelector('.orb-1');
    const orb2 = document.querySelector('.orb-2');
    const orb3 = document.querySelector('.orb-3');

    if (orb1) {
      gsap.to(orb1, {
        scrollTrigger: { trigger: document.body, start: 'top top', end: 'bottom bottom', scrub: 1 },
        y: 240,
        ease: 'none'
      });
    }
    if (orb2) {
      gsap.to(orb2, {
        scrollTrigger: { trigger: document.body, start: 'top top', end: 'bottom bottom', scrub: 1.5 },
        y: -180,
        ease: 'none'
      });
    }
    if (orb3) {
      gsap.to(orb3, {
        scrollTrigger: { trigger: document.body, start: 'top top', end: 'bottom bottom', scrub: 2 },
        y: -300,
        ease: 'none'
      });
    }
  }

  /**
   * Main Render Tick
   */
  function tick() {
    animFrameId = requestAnimationFrame(tick);

    if (!isTabVisible || !renderer || !scene || !camera) return;

    const elapsedTime = clock ? clock.getElapsedTime() : 0;

    // Apply interpolated GSAP transform + gentle idle floating oscillation
    if (leafGroup) {
      const idleFloatY = prefersReducedMotion ? 0 : Math.sin(elapsedTime * 1.6) * 0.08;
      const idleFloatX = prefersReducedMotion ? 0 : Math.cos(elapsedTime * 1.2) * 0.04;
      const idleTilt = prefersReducedMotion ? 0 : Math.sin(elapsedTime * 1.4) * 0.05;

      leafGroup.position.set(
        leafTransform.x + idleFloatX,
        leafTransform.y + idleFloatY,
        leafTransform.z
      );

      leafGroup.rotation.set(
        leafTransform.rotX + idleTilt * 0.5,
        leafTransform.rotY + idleTilt,
        leafTransform.rotZ
      );

      leafGroup.scale.set(
        leafTransform.scale,
        leafTransform.scale,
        leafTransform.scale
      );
    }

    // Update secondary leaves
    if (secondaryLeaf1 && !prefersReducedMotion) {
      secondaryLeaf1.rotation.y += 0.004;
      secondaryLeaf1.rotation.z += 0.002;
    }
    if (secondaryLeaf2 && !prefersReducedMotion) {
      secondaryLeaf2.rotation.y -= 0.003;
      secondaryLeaf2.rotation.x += 0.002;
    }

    // Update particles orbit
    if (!prefersReducedMotion) {
      updateParticles(elapsedTime);
    }

    // Render Scene
    renderer.render(scene, camera);
  }

  /**
   * Window resize handler
   */
  function onWindowResize() {
    if (!camera || !renderer) return;

    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    if (window.ScrollTrigger) {
      ScrollTrigger.refresh();
    }
  }

  /**
   * Visibility change handler (pauses RAF loop when tab is hidden to save battery & GPU)
   */
  function onVisibilityChange() {
    isTabVisible = !document.hidden;
  }

  /**
   * Cleanup and disposal
   */
  function dispose() {
    if (animFrameId) cancelAnimationFrame(animFrameId);
    window.removeEventListener('resize', onWindowResize);
    document.removeEventListener('visibilitychange', onVisibilityChange);

    if (scrollTimeline) scrollTimeline.kill();

    if (leafGroup) {
      leafGroup.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }
      });
    }
    if (veinTexture) veinTexture.dispose();
    if (renderer) renderer.dispose();
  }

  // Initialize once DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThreeScene);
  } else {
    initThreeScene();
  }

  // Expose for external refreshes if needed
  window.FoodWaste3D = {
    refresh: () => {
      if (window.ScrollTrigger) ScrollTrigger.refresh();
    },
    dispose: dispose
  };

})();
