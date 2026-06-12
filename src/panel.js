// Pannello Tweakpane: stili, modello, colori per materiale, luci
import { Pane } from 'tweakpane';
import { STYLES, applyStyle } from './styles.js';
import { groupMaterials, lineMaterial, setOutlineColor, groundShadowMaterial, GROUPS } from './materials.js';

const GROUP_LABELS = {
  Fratelli_HQ: 'Palazzo Fratelli',
  City: 'Città',
  Roads: 'Strade',
  Poles: 'Pali e cavi',
  Clouds: 'Nuvole',
};

// ctx: { scene, ambientLight, directionalLight, setModel, currentModel }
export function initPanel(ctx) {
  const state = {
    stile: 'Crema',
    modello: ctx.currentModel,
    sfondo: '#f5f5f3',
    outline: '#161616',
    ombra: '#ede5db',
    ombraOpacita: 0.75,
    ambientColore: '#f1e9d9',
    ambientIntensita: 2.2,
    soleIntensita: 1.6,
    soleAzimut: -0.59,
    soleAltezza: 0.9,
    gruppi: {},
  };
  for (const g of GROUPS) state.gruppi[g] = '#d8d8d8';

  const pane = new Pane({ title: 'Fratelli 3D', expanded: true });
  pane.element.parentElement.classList.add('panel-host');

  pane
    .addBinding(state, 'stile', {
      label: 'Stile',
      options: Object.fromEntries(Object.keys(STYLES).map((k) => [k, k])),
    })
    .on('change', (ev) => {
      const preset = STYLES[ev.value];
      applyStyle(preset, ctx);
      syncFromScene();
      pane.refresh();
    });

  pane
    .addBinding(state, 'modello', {
      label: 'Modello',
      options: { 'v3 — contesto': 'v3', 'v2 — denso': 'v2', 'v1 — classico': 'v1' },
    })
    .on('change', (ev) => ctx.setModel(ev.value));

  const fc = pane.addFolder({ title: 'Colori', expanded: true });
  fc.addBinding(state, 'sfondo', { label: 'Sfondo' }).on('change', (ev) => ctx.scene.background.set(ev.value));
  fc.addBinding(state, 'outline', { label: 'Linee' }).on('change', (ev) => setOutlineColor(ev.value));
  fc.addBinding(state, 'ombra', { label: 'Ombre' }).on('change', (ev) => groundShadowMaterial.color.set(ev.value));
  fc.addBinding(state, 'ombraOpacita', { label: 'Ombre op.', min: 0, max: 1 }).on('change', (ev) => {
    groundShadowMaterial.opacity = ev.value;
  });
  for (const g of GROUPS) {
    fc.addBinding(state.gruppi, g, { label: GROUP_LABELS[g] }).on('change', (ev) => {
      groupMaterials[g].color.set(ev.value);
    });
  }

  const setSun = () => {
    const R = 115;
    const az = state.soleAzimut;
    const el = state.soleAltezza;
    ctx.directionalLight.position.set(
      R * Math.cos(el) * Math.cos(az),
      R * Math.sin(el),
      R * Math.cos(el) * Math.sin(az),
    );
  };

  const fl = pane.addFolder({ title: 'Luci', expanded: false });
  fl.addBinding(state, 'soleAzimut', { label: 'Sole rotazione', min: -Math.PI, max: Math.PI })
    .on('change', setSun);
  fl.addBinding(state, 'soleAltezza', { label: 'Sole altezza', min: 0.25, max: 1.45 })
    .on('change', setSun);
  fl.addBinding(state, 'ambientColore', { label: 'Ambiente' }).on('change', (ev) => ctx.ambientLight.color.set(ev.value));
  fl.addBinding(state, 'ambientIntensita', { label: 'Ambiente int.', min: 0, max: 4 }).on('change', (ev) => {
    ctx.ambientLight.intensity = ev.value;
  });
  fl.addBinding(state, 'soleIntensita', { label: 'Sole int.', min: 0, max: 4 }).on('change', (ev) => {
    ctx.directionalLight.intensity = ev.value;
  });

  function syncFromScene() {
    state.sfondo = '#' + ctx.scene.background.getHexString();
    state.outline = '#' + lineMaterial.color.getHexString();
    state.ombra = '#' + groundShadowMaterial.color.getHexString();
    state.ombraOpacita = groundShadowMaterial.opacity;
    state.ambientColore = '#' + ctx.ambientLight.color.getHexString();
    state.ambientIntensita = ctx.ambientLight.intensity;
    state.soleIntensita = ctx.directionalLight.intensity;
    const p = ctx.directionalLight.position;
    const horiz = Math.hypot(p.x, p.z);
    state.soleAzimut = Math.atan2(p.z, p.x);
    state.soleAltezza = Math.atan2(p.y, horiz);
    for (const g of GROUPS) state.gruppi[g] = '#' + groupMaterials[g].color.getHexString();
  }

  // bottone ingranaggio: pannello chiuso di default
  const host = pane.element.parentElement;
  host.style.display = 'none';
  const btn = document.getElementById('panel-toggle');
  btn.addEventListener('click', () => {
    const open = host.style.display === 'none';
    host.style.display = open ? '' : 'none';
    btn.classList.toggle('active', open);
    if (open) {
      syncFromScene();
      pane.refresh();
    }
  });

  syncFromScene();
  pane.refresh();
  return pane;
}
