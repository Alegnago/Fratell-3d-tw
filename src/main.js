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
import { groundShadowMaterial, makeLogoMaterial } from './materials.js';
import { STYLES, applyStyle } from './styles.js';
import { applyInkStyle } from './edges.js';
import { CameraRig } from './cameraRig.js';
import { initPanel } from './panel.js';
import modelV1Url from '../assets/fratelli_city.glb?url';
import modelV2Url from '../assets/fratelli_city_v2.glb?url';
import modelV3Url from '../assets/fratelli_city_v3.glb?url';
import modelV4Url from '../assets/fratelli_city_v4.glb?url';
import logoUrl from '../assets/logo.svg?url';

const MODELS = { v1: modelV1Url, v2: modelV2Url, v3: modelV3Url, v4: modelV4Url };
const DEFAULT_MODEL = 'v4';

const app = document.getElementById('app');
// su mobile il DPR alto rende le linee 1px sottili ma SENZA antialias
// appaiono dure/scalettate (sembrano piu' spesse). AA sempre attivo +
// DPR fino a 3: linee piu' nitide e morbide quando la camera arretra.
const dpr = Math.min(window.devicePixelRatio, 3);

const renderer = new WebGLRenderer({
  precision: 'highp',
  powerPreference: 'high-performance',
  antialias: true,
  stencil: false,
  alpha: true,
});
renderer.setPixelRatio(dpr);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = PCFShadowMap;
app.appendChild(renderer.domElement);

const scene = new Scene();
scene.background = new Color(0xf5f5f3);

const rig = new CameraRig(app);

const ambientLight = new AmbientLight(0xf1e9d9, 2.2);
scene.add(ambientLight);
const directionalLight = new DirectionalLight(0xffffff, 1.6);
directionalLight.position.set(60, 90, -40);
directionalLight.castShadow = true;
directionalLight.shadow.mapSize.set(2048, 2048);
directionalLight.shadow.camera.left = -110;
directionalLight.shadow.camera.right = 110;
directionalLight.shadow.camera.top = 110;
directionalLight.shadow.camera.bottom = -110;
directionalLight.shadow.camera.far = 300;
directionalLight.shadow.bias = -0.0005;
scene.add(directionalLight);

const ground = new Mesh(new PlaneGeometry(500, 500), groundShadowMaterial);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// logo condiviso tra i modelli: SVG rasterizzato su canvas (sfondo trasparente)
let logoMaterial = null;
const logoReady = new Promise((resolve) => {
  const img = new Image();
  img.onload = () => {
    const cnv = document.createElement('canvas');
    cnv.width = cnv.height = 1024;
    cnv.getContext('2d').drawImage(img, 0, 0, 1024, 1024);
    const tex = new CanvasTexture(cnv);
    tex.colorSpace = SRGBColorSpace;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    logoMaterial = makeLogoMaterial(tex);
    resolve();
  };
  img.src = logoUrl;
});

const loader = new GLTFLoader();
const modelCache = {};
let currentRoot = null;
let currentModel = DEFAULT_MODEL;

function setModel(key) {
  currentModel = key;
  if (currentRoot) scene.remove(currentRoot);
  currentRoot = null;
  const attach = (root) => {
    if (currentModel !== key) return; // switch nel frattempo
    currentRoot = root;
    scene.add(root);
  };
  if (modelCache[key]) {
    attach(modelCache[key]);
    return;
  }
  loader.load(MODELS[key], async (gltf) => {
    // applyInkStyle "cuoce" istanze e gruppi in poche mesh: si aggiunge
    // il Group ritornato, non gltf.scene
    const root = applyInkStyle(gltf.scene, { skipNames: ['Logo'] });
    await logoReady;
    const logo = root.getObjectByName('Logo');
    if (logo) logo.material = logoMaterial;
    modelCache[key] = root;
    attach(root);
  });
}
setModel(DEFAULT_MODEL);

const ctx = {
  scene,
  ambientLight,
  directionalLight,
  setModel,
  get currentModel() {
    return currentModel;
  },
};
applyStyle(STYLES.Sabbia, ctx);
initPanel(ctx);

window.__rig = rig;
window.__scene = scene;
window.__ctx = ctx;
window.__renderer = renderer;

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
