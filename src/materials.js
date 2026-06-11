// Materiali per gruppo + outline condivisi — base palette adidasarena
import {
  Color,
  DoubleSide,
  LineBasicMaterial,
  MeshBasicMaterial,
  MeshLambertMaterial,
  ShaderMaterial,
  ShadowMaterial,
} from 'three';
import { ConditionalEdgesShader } from './ConditionalEdgesShader.js';

export const GROUPS = ['Fratelli_HQ', 'City', 'Roads', 'Poles', 'Clouds'];

// un lambert per gruppo: i color picker agiscono sul singolo gruppo
export const groupMaterials = {};
for (const name of GROUPS) {
  groupMaterials[name] = new MeshLambertMaterial({
    precision: 'lowp',
    color: 0xd8d8d8,
    emissive: 0xefefef,
    emissiveIntensity: 0.75,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
    side: DoubleSide,
  });
  groupMaterials[name].name = name;
}

export function getGroupMaterial(meshName) {
  return groupMaterials[meshName] || groupMaterials.City;
}

export const lineMaterial = new LineBasicMaterial({
  precision: 'lowp',
  color: 0x161616,
  linewidth: 1,
});

// i conditional material vengono creati uno per mesh: tenuti qui per
// aggiornarne il colore in blocco col pannello
export const conditionalMaterials = [];

export function makeConditionalMaterial() {
  const material = new ShaderMaterial({
    uniforms: { diffuse: { value: new Color(lineMaterial.color) }, opacity: { value: 1 } },
    vertexShader: ConditionalEdgesShader.vertexShader,
    fragmentShader: ConditionalEdgesShader.fragmentShader,
  });
  conditionalMaterials.push(material);
  return material;
}

export function setOutlineColor(color) {
  lineMaterial.color.set(color);
  for (const m of conditionalMaterials) m.uniforms.diffuse.value.set(color);
}

export const groundShadowMaterial = new ShadowMaterial({
  color: 0xede5db,
  transparent: true,
  opacity: 0.75,
});

export function makeLogoMaterial(texture) {
  return new MeshBasicMaterial({
    map: texture,
    transparent: true,
    toneMapped: false,
    side: DoubleSide,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  });
}
