// Applica lo stile "ink": superfici lambert + linee crease + linee silhouette.
// Le geometrie condivise (istanze v4) vengono lavorate una volta sola e poi
// "cotte" in una mesh + due LineSegments per categoria: pochi draw call
// qualunque sia il numero di istanze. v1-v3 (mega-mesh singole) passano dallo
// stesso percorso con matrix identity.
import { BufferGeometry, EdgesGeometry, Group, LineSegments, Matrix3, Mesh } from 'three';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { ConditionalEdgesGeometry } from './ConditionalEdgesGeometry.js';
import { GROUPS, getGroupMaterial, lineMaterial, makeConditionalMaterial } from './materials.js';

const THRESHOLD_ANGLE = 40;

// cache per geometria sorgente: con le istanze il costo è per-asset unico
const inkCache = new Map(); // geometry.uuid -> { surf, edges, cond }

function inkFor(geometry) {
  let entry = inkCache.get(geometry.uuid);
  if (entry) return entry;

  const surf = geometry.clone();
  for (const name of Object.keys(surf.attributes)) {
    if (name !== 'position' && name !== 'normal') surf.deleteAttribute(name);
  }

  const edges = new EdgesGeometry(geometry, THRESHOLD_ANGLE);

  let cond = null;
  try {
    // solo POSITION: con normali/uv mergeVertices non salderebbe i vertici
    const bare = geometry.clone();
    for (const name of Object.keys(bare.attributes)) {
      if (name !== 'position') bare.deleteAttribute(name);
    }
    cond = new ConditionalEdgesGeometry(mergeVertices(bare));
  } catch (err) {
    console.warn('conditional edges falliti', err);
  }

  entry = { surf, edges, cond };
  inkCache.set(geometry.uuid, entry);
  return entry;
}

// l'exporter GLTF sanitizza "Trees.014" in "Trees014": si strippano le
// cifre finali (con o senza separatore); risale gli antenati se serve
function resolveGroup(node) {
  for (let n = node; n; n = n.parent) {
    const base = n.name.replace(/[._]?\d+$/, '');
    if (GROUPS.includes(base)) return base;
  }
  return 'City';
}

// gli attributi delle conditional edges sono punti (position/control*) e un
// vettore (direction): trasformati di conseguenza
function transformedCond(cond, matrix) {
  // niente cond.clone(): il costruttore di ConditionalEdgesGeometry
  // richiede una geometria sorgente — si copia in una BufferGeometry piatta
  const g = new BufferGeometry();
  for (const name of ['position', 'direction', 'control0', 'control1']) {
    g.setAttribute(name, cond.attributes[name].clone());
  }
  g.attributes.position.applyMatrix4(matrix);
  g.attributes.control0.applyMatrix4(matrix);
  g.attributes.control1.applyMatrix4(matrix);
  // direction è un vettore in spazio modello e nel shader fa
  // p1 = position + direction: serve la parte lineare pura della world
  // matrix (rotazione*scala), NON la normal matrix (= R/s con la scala)
  g.attributes.direction.applyMatrix3(new Matrix3().setFromMatrix4(matrix));
  return g;
}

export function applyInkStyle(root, { skipNames = [] } = {}) {
  root.updateMatrixWorld(true);
  const out = new Group();
  const buckets = new Map();

  root.traverse((child) => {
    if (!child.isMesh) return;
    if (skipNames.includes(child.name)) {
      // es. Logo: preservato com'è, in coordinate mondo
      const kept = new Mesh(child.geometry.clone().applyMatrix4(child.matrixWorld), child.material);
      kept.name = child.name;
      out.add(kept);
      return;
    }
    const group = resolveGroup(child);
    let bucket = buckets.get(group);
    if (!bucket) buckets.set(group, (bucket = { surf: [], edge: [], cond: [] }));

    const { surf, edges, cond } = inkFor(child.geometry);
    const m = child.matrixWorld;
    bucket.surf.push(surf.clone().applyMatrix4(m));
    bucket.edge.push(edges.clone().applyMatrix4(m));
    if (cond) bucket.cond.push(transformedCond(cond, m));
  });

  for (const [group, b] of buckets) {
    const mesh = new Mesh(mergeGeometries(b.surf), getGroupMaterial(group));
    mesh.name = group;
    mesh.castShadow = !/cloud/i.test(group);
    mesh.receiveShadow = true;
    out.add(mesh);

    const edges = new LineSegments(mergeGeometries(b.edge), lineMaterial);
    edges.name = `${group}_edges`;
    out.add(edges);

    if (b.cond.length) {
      const cond = new LineSegments(mergeGeometries(b.cond), makeConditionalMaterial());
      cond.name = `${group}_silhouette`;
      out.add(cond);
    }
  }
  return out;
}
