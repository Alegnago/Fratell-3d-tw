import {
  AmbientLight,
  CanvasTexture,
  Color,
  DirectionalLight,
  Mesh,
  PCFShadowMap,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  WebGLRenderer,
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { COLORS, groundShadowMaterial, makeLogoMaterial } from './materials.js';
import { applyInkStyle } from './edges.js';
import { CameraRig } from './cameraRig.js';
import modelUrl from '../assets/fratelli_city.glb?url';
import logoUrl from '../assets/logo.svg?url';

const app = document.getElementById('app');
const dpr = Math.min(window.devicePixelRatio, 2);

const renderer = new WebGLRenderer({
  precision: 'highp',
  powerPreference: 'high-performance',
  antialias: dpr < 2,
  stencil: false,
  alpha: true,
});
renderer.setPixelRatio(dpr);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = PCFShadowMap;
app.appendChild(renderer.domElement);

const scene = new Scene();
scene.background = new Color(COLORS.background);

const rig = new CameraRig(app);
window.__rig = rig;
window.__scene = scene;
window.__renderer = renderer;

// luci — palette adidas
scene.add(new AmbientLight(COLORS.ambientLight, 2.2));
const sun = new DirectionalLight(COLORS.directionalLight, 1.6);
sun.position.set(60, 90, -40);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -110;
sun.shadow.camera.right = 110;
sun.shadow.camera.top = 110;
sun.shadow.camera.bottom = -110;
sun.shadow.camera.far = 300;
sun.shadow.bias = -0.0005;
scene.add(sun);

// terreno: riceve solo ombre beige
const ground = new Mesh(new PlaneGeometry(500, 500), groundShadowMaterial);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

new GLTFLoader().load(modelUrl, (gltf) => {
  const root = gltf.scene;
  applyInkStyle(root, { skipNames: ['Logo'] });

  // SVG rasterizzato su canvas: sfondo trasparente garantito
  const logo = root.getObjectByName('Logo');
  if (logo) {
    const img = new Image();
    img.onload = () => {
      const cnv = document.createElement('canvas');
      cnv.width = cnv.height = 1024;
      cnv.getContext('2d').drawImage(img, 0, 0, 1024, 1024);
      const tex = new CanvasTexture(cnv);
      tex.colorSpace = SRGBColorSpace;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      logo.material = makeLogoMaterial(tex);
    };
    img.src = logoUrl;
  }

  scene.add(root);
  renderer.domElement.classList.add('ready');
});

function resize() {
  const w = app.clientWidth;
  const h = app.clientHeight;
  renderer.setSize(w, h);
  rig.resize(w, h);
}
window.addEventListener('resize', resize);
resize();

let lastTime = performance.now();
renderer.setAnimationLoop((time) => {
  const dt = Math.min((time - lastTime) / 1000, 0.05);
  lastTime = time;
  rig.update(dt);
  renderer.render(scene, rig.camera);
});
