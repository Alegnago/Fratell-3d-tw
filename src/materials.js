// Palette e materiali — valori estratti da adidasarena.com
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

export const COLORS = {
  background: 0xf5f5f3,
  surface: 0xd8d8d8,
  surfaceEmissive: 0xefefef,
  outline: 0x161616,
  shadow: 0xede5db,
  ambientLight: 0xf1e9d9,
  directionalLight: 0xffffff,
};

export const surfaceMaterial = new MeshLambertMaterial({
  precision: 'lowp',
  color: COLORS.surface,
  emissive: COLORS.surfaceEmissive,
  emissiveIntensity: 0.75,
  polygonOffset: true,
  polygonOffsetFactor: 1,
  polygonOffsetUnits: 1,
  side: DoubleSide,
});

export const lineMaterial = new LineBasicMaterial({
  precision: 'lowp',
  color: COLORS.outline,
  linewidth: 1,
});

export function makeConditionalMaterial() {
  const material = new ShaderMaterial(ConditionalEdgesShader);
  material.uniforms.diffuse.value = new Color(COLORS.outline);
  return material;
}

export const groundShadowMaterial = new ShadowMaterial({
  color: COLORS.shadow,
  transparent: true,
  opacity: 0.75,
});

export function makeLogoMaterial(texture) {
  return new MeshBasicMaterial({
    map: texture,
    transparent: true,
    toneMapped: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  });
}
