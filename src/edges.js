// Applica lo stile "ink": superfici lambert + linee crease + linee silhouette
import { EdgesGeometry, LineSegments } from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { ConditionalEdgesGeometry } from './ConditionalEdgesGeometry.js';
import { surfaceMaterial, lineMaterial, makeConditionalMaterial } from './materials.js';

const THRESHOLD_ANGLE = 40;

export function applyInkStyle(root, { skipNames = [] } = {}) {
  const meshes = [];
  root.traverse((child) => {
    if (child.isMesh && !skipNames.includes(child.name)) meshes.push(child);
  });

  for (const mesh of meshes) {
    mesh.material = surfaceMaterial;
    mesh.castShadow = !/cloud/i.test(mesh.name);
    mesh.receiveShadow = true;

    const edgesGeom = new EdgesGeometry(mesh.geometry, THRESHOLD_ANGLE);
    const edges = new LineSegments(edgesGeom, lineMaterial);
    edges.name = `${mesh.name}_edges`;
    mesh.add(edges);

    try {
      // solo POSITION: con normali/uv mergeVertices non salderebbe i vertici
      const bare = mesh.geometry.clone();
      for (const name of Object.keys(bare.attributes)) {
        if (name !== 'position') bare.deleteAttribute(name);
      }
      const indexed = mergeVertices(bare);
      const condGeom = new ConditionalEdgesGeometry(indexed);
      const cond = new LineSegments(condGeom, makeConditionalMaterial());
      cond.name = `${mesh.name}_silhouette`;
      mesh.add(cond);
    } catch (err) {
      console.warn(`conditional edges falliti per ${mesh.name}`, err);
    }
  }
}
