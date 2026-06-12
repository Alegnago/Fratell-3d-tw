// Preset di stile completi: palette + luci + resa
import { groupMaterials, lineMaterial, setOutlineColor, groundShadowMaterial, GROUPS } from './materials.js';

export const STYLES = {
  Crema: {
    background: '#f5f5f3',
    outline: '#161616',
    shadow: '#ede5db',
    shadowOpacity: 0.75,
    ambientColor: '#f1e9d9',
    ambientIntensity: 2.2,
    directionalIntensity: 1.6,
    emissive: '#efefef',
    emissiveIntensity: 0.75,
    groups: {
      Fratelli_HQ: '#d8d8d8',
      City: '#d8d8d8',
      Roads: '#e2e2e0',
      Poles: '#d8d8d8',
      Clouds: '#e8e8e6',
    },
  },
  Notte: {
    background: '#15161a',
    outline: '#e8e6df',
    shadow: '#08080c',
    shadowOpacity: 0.85,
    ambientColor: '#3a3d4a',
    ambientIntensity: 1.6,
    directionalIntensity: 0.5,
    emissive: '#23252c',
    emissiveIntensity: 0.9,
    groups: {
      Fratelli_HQ: '#2c2e36',
      City: '#26282e',
      Roads: '#1d1f24',
      Poles: '#26282e',
      Clouds: '#2e3038',
    },
  },
  Blueprint: {
    background: '#16356e',
    outline: '#f2f4f8',
    shadow: '#0d2349',
    shadowOpacity: 0.6,
    ambientColor: '#2a4d8f',
    ambientIntensity: 1.8,
    directionalIntensity: 0.4,
    emissive: '#16356e',
    emissiveIntensity: 1.0,
    groups: {
      Fratelli_HQ: '#1a3a76',
      City: '#173770',
      Roads: '#153269',
      Poles: '#173770',
      Clouds: '#1d3d7c',
    },
  },
  Seppia: {
    background: '#f3ead8',
    outline: '#41331f',
    shadow: '#e0cdb0',
    shadowOpacity: 0.8,
    ambientColor: '#f0e2c8',
    ambientIntensity: 2.2,
    directionalIntensity: 1.4,
    emissive: '#ecdfc6',
    emissiveIntensity: 0.75,
    groups: {
      Fratelli_HQ: '#e9dcc3',
      City: '#e4d6ba',
      Roads: '#eee2cb',
      Poles: '#e4d6ba',
      Clouds: '#f0e5d0',
    },
  },
  Sabbia: {
    background: '#f5f0f0',
    outline: '#1e1e28',
    shadow: '#ede5db',
    shadowOpacity: 0.75,
    ambientColor: '#675f4f',
    ambientIntensity: 1.26,
    directionalIntensity: 2.0,
    sunAzimuth: 0.82,
    sunElevation: 0.82,
    emissive: '#efefef',
    emissiveIntensity: 0.75,
    groups: {
      Fratelli_HQ: '#ffffff',
      City: '#cdb59a',
      Roads: '#7e6846',
      Poles: '#1e1e28',
      Clouds: '#e8e8e6',
    },
  },
  Fratelli: {
    background: '#f7f4f1',
    outline: '#e30613',
    shadow: '#f3dcd8',
    shadowOpacity: 0.8,
    ambientColor: '#f6ece8',
    ambientIntensity: 2.2,
    directionalIntensity: 1.5,
    emissive: '#f3eeec',
    emissiveIntensity: 0.78,
    groups: {
      Fratelli_HQ: '#e7e2df',
      City: '#e7e2df',
      Roads: '#efebe8',
      Poles: '#e7e2df',
      Clouds: '#f0ecea',
    },
  },
};

// ctx: { scene, ambientLight, directionalLight }
export function applyStyle(preset, ctx) {
  ctx.scene.background.set(preset.background);
  setOutlineColor(preset.outline);
  groundShadowMaterial.color.set(preset.shadow);
  groundShadowMaterial.opacity = preset.shadowOpacity;
  ctx.ambientLight.color.set(preset.ambientColor);
  ctx.ambientLight.intensity = preset.ambientIntensity;
  ctx.directionalLight.intensity = preset.directionalIntensity;
  if (preset.sunAzimuth !== undefined) {
    const R = 115;
    ctx.directionalLight.position.set(
      R * Math.cos(preset.sunElevation) * Math.cos(preset.sunAzimuth),
      R * Math.sin(preset.sunElevation),
      R * Math.cos(preset.sunElevation) * Math.sin(preset.sunAzimuth),
    );
  }
  for (const name of GROUPS) {
    const m = groupMaterials[name];
    m.color.set(preset.groups[name]);
    m.emissive.set(preset.emissive);
    m.emissiveIntensity = preset.emissiveIntensity;
  }
}
