import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const dataElement = document.getElementById('scene-data');
const container = document.getElementById('scene-container');
const loading = document.getElementById('scene-loading');
const selection = document.getElementById('scene-selection');
const resetButton = document.getElementById('scene-reset');

if (!dataElement || !container) {
  throw new Error('3D scene container or scene data is missing.');
}

const data = JSON.parse(dataElement.textContent);
const MM = 0.001;
const COLORS = {
  background: 0xf6f7f9,
  floor: 0xe5e7eb,
  grid: 0x9ca3af,
  fixture: 0x64748b,
  zone: 0x2563eb,
  container: 0x0f766e,
  carton: 0x92400e,
  equipment: 0x4338ca,
  tool: 0x7c3aed,
  other: 0x475569,
  highlight: 0xdc2626,
  edge: 0x334155,
};

function toThreeSize(size) {
  return new THREE.Vector3(size[0] * MM, size[2] * MM, size[1] * MM);
}

function toLocalCenter(origin, size, fixtureOrigin = [0, 0, 0]) {
  return new THREE.Vector3(
    (origin[0] - fixtureOrigin[0] + size[0] / 2) * MM,
    (origin[2] - fixtureOrigin[2] + size[2] / 2) * MM,
    (origin[1] - fixtureOrigin[1] + size[1] / 2) * MM,
  );
}

function isHighlighted(type, code) {
  return Boolean(data.highlight && data.highlight.type === type && data.highlight.code === code);
}

function entityUrl(type, code) {
  if (type === 'unit') return data.links?.units?.[code] || null;
  if (type === 'zone') return data.links?.zones?.[code] || null;
  return null;
}

function unitColor(kind) {
  if (kind === 'CONTAINER') return COLORS.container;
  if (kind === 'CARTON') return COLORS.carton;
  if (kind === 'EQUIPMENT') return COLORS.equipment;
  if (kind === 'TOOL') return COLORS.tool;
  return COLORS.other;
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(COLORS.background);

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true });
} catch (error) {
  loading.textContent = 'このブラウザではWebGL 3D表示を開始できません。通常の検索・在庫操作はそのまま利用できます。';
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.domElement.className = 'scene-canvas';
container.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(48, 1, 0.01, 500);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.screenSpacePanning = true;
controls.minDistance = 0.15;
controls.maxDistance = 80;

scene.add(new THREE.HemisphereLight(0xffffff, 0x64748b, 2.2));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.0);
keyLight.position.set(4, 8, 5);
scene.add(keyLight);

const contentRoot = new THREE.Group();
scene.add(contentRoot);
const interactiveMeshes = [];
const entityMeshes = new Map();
const fixtureGroups = new Map();
const fixtureNodes = new Map(data.fixtures.map((node) => [node.code, node]));
const zoneNodes = new Map(data.zones.map((node) => [node.code, node]));

function registerEntity(mesh, type, node) {
  const entity = {
    type,
    code: node.code,
    name: node.name,
    kind: node.kind,
    url: entityUrl(type, node.code),
    autoGeometry: Boolean(node.auto_geometry),
  };
  mesh.userData.entity = entity;
  interactiveMeshes.push(mesh);
  entityMeshes.set(`${type}:${node.code}`, mesh);
}

function addEdges(mesh, color, opacity = 0.85) {
  const geometry = new THREE.EdgesGeometry(mesh.geometry);
  const material = new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity });
  const edges = new THREE.LineSegments(geometry, material);
  edges.position.copy(mesh.position);
  edges.rotation.copy(mesh.rotation);
  edges.scale.copy(mesh.scale);
  mesh.parent.add(edges);
  return edges;
}

function addLocalBox(
  parent,
  {
    size,
    center,
    color,
    opacity = 1,
    type,
    node,
    highlighted = false,
    rotationY = 0,
  },
) {
  const threeSize = toThreeSize(size);
  const geometry = new THREE.BoxGeometry(threeSize.x, threeSize.y, threeSize.z);
  const material = new THREE.MeshStandardMaterial({
    color: highlighted ? COLORS.highlight : color,
    transparent: opacity < 1,
    opacity,
    depthWrite: opacity >= 0.45,
    roughness: 0.78,
    metalness: 0.03,
  });
  if (highlighted) {
    material.emissive = new THREE.Color(COLORS.highlight);
    material.emissiveIntensity = 0.18;
  }
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(center);
  mesh.rotation.y = rotationY;
  parent.add(mesh);
  addEdges(mesh, highlighted ? COLORS.highlight : COLORS.edge, highlighted ? 1 : 0.65);
  if (type && node) registerEntity(mesh, type, node);
  return mesh;
}

function addFixture(node) {
  const group = new THREE.Group();
  const [x, y, z] = node.origin_mm;
  group.position.set(x * MM, z * MM, y * MM);
  group.rotation.y = -THREE.MathUtils.degToRad(node.rotation_z_deg || 0);
  contentRoot.add(group);
  fixtureGroups.set(node.code, group);

  const highlighted = isHighlighted('fixture', node.code);
  const [width, depth, height] = node.size_mm;

  if (node.kind === 'DESK' || node.kind === 'WORKBENCH') {
    const topThickness = Math.min(45, Math.max(20, height * 0.06));
    const top = addLocalBox(group, {
      size: [width, depth, topThickness],
      center: toLocalCenter([0, 0, height - topThickness], [width, depth, topThickness]),
      color: COLORS.fixture,
      opacity: 0.48,
      type: 'fixture',
      node,
      highlighted,
    });
    top.userData.entity.name = node.name;

    const leg = Math.min(70, Math.max(35, Math.min(width, depth) * 0.08));
    const legHeight = Math.max(20, height - topThickness);
    const legOrigins = [
      [20, 20, 0],
      [Math.max(20, width - leg - 20), 20, 0],
      [20, Math.max(20, depth - leg - 20), 0],
      [Math.max(20, width - leg - 20), Math.max(20, depth - leg - 20), 0],
    ];
    for (const origin of legOrigins) {
      addLocalBox(group, {
        size: [leg, leg, legHeight],
        center: toLocalCenter(origin, [leg, leg, legHeight]),
        color: COLORS.fixture,
        opacity: 0.3,
      });
    }
    return;
  }

  const opacity = node.kind === 'WALL' ? 0.22 : 0.07;
  addLocalBox(group, {
    size: node.size_mm,
    center: toLocalCenter([0, 0, 0], node.size_mm),
    color: COLORS.fixture,
    opacity,
    type: 'fixture',
    node,
    highlighted,
  });
}

for (const fixture of data.fixtures) addFixture(fixture);

function fixtureGroupAndOrigin(fixtureCode) {
  return [fixtureGroups.get(fixtureCode), fixtureNodes.get(fixtureCode)?.origin_mm || [0, 0, 0]];
}

for (const node of data.zones) {
  const [group, fixtureOrigin] = fixtureGroupAndOrigin(node.fixture_code);
  if (!group) continue;
  const highlighted = isHighlighted('zone', node.code);
  addLocalBox(group, {
    size: node.size_mm,
    center: toLocalCenter(node.origin_mm, node.size_mm, fixtureOrigin),
    color: COLORS.zone,
    opacity: highlighted ? 0.3 : 0.09,
    type: 'zone',
    node,
    highlighted,
  });
}

for (const node of data.units) {
  const rootZone = zoneNodes.get(node.root_zone_code);
  if (!rootZone) continue;
  const [group, fixtureOrigin] = fixtureGroupAndOrigin(rootZone.fixture_code);
  if (!group) continue;
  const highlighted = isHighlighted('unit', node.code);
  addLocalBox(group, {
    size: node.size_mm,
    center: toLocalCenter(node.origin_mm, node.size_mm, fixtureOrigin),
    color: unitColor(node.kind),
    opacity: 0.82,
    type: 'unit',
    node,
    highlighted,
    rotationY: -THREE.MathUtils.degToRad(node.rotation_z_deg || 0),
  });
}

const [roomWidth, roomDepth, roomHeight] = data.room.size_mm.map((value) => value * MM);
const floorGeometry = new THREE.PlaneGeometry(roomWidth, roomDepth);
const floorMaterial = new THREE.MeshStandardMaterial({ color: COLORS.floor, roughness: 1, side: THREE.DoubleSide });
const floor = new THREE.Mesh(floorGeometry, floorMaterial);
floor.rotation.x = -Math.PI / 2;
floor.position.set(roomWidth / 2, -0.002, roomDepth / 2);
scene.add(floor);

const gridSize = Math.max(roomWidth, roomDepth);
const divisions = Math.max(8, Math.min(40, Math.round(gridSize / 0.5)));
const grid = new THREE.GridHelper(gridSize, divisions, COLORS.grid, COLORS.grid);
grid.position.set(roomWidth / 2, 0, roomDepth / 2);
const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material];
for (const material of gridMaterials) {
  material.transparent = true;
  material.opacity = 0.23;
}
scene.add(grid);

const roomBox = new THREE.Box3(
  new THREE.Vector3(0, 0, 0),
  new THREE.Vector3(roomWidth, Math.max(roomHeight, 0.5), roomDepth),
);

function fitBox(box, factor = 1.45) {
  if (box.isEmpty()) return;
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  const maxDimension = Math.max(size.x, size.y, size.z, 0.25);
  const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
  const distance = Math.max(0.6, (maxDimension / (2 * Math.tan(halfFov))) * factor);
  const direction = new THREE.Vector3(1, 0.72, 1).normalize();
  camera.position.copy(center).add(direction.multiplyScalar(distance));
  camera.near = Math.max(0.01, distance / 250);
  camera.far = Math.max(100, distance * 30);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

function fitRoom() {
  fitBox(roomBox, 1.35);
}

function setSelection(entity) {
  selection.replaceChildren();
  if (!entity) {
    const text = document.createElement('p');
    text.textContent = '箱・棚などをクリックすると情報を表示します。';
    selection.appendChild(text);
    return;
  }

  const title = document.createElement('strong');
  title.textContent = `${entity.code} — ${entity.name}`;
  const kind = document.createElement('p');
  kind.textContent = entity.kind;
  selection.append(title, kind);

  if (entity.autoGeometry) {
    const warning = document.createElement('p');
    warning.className = 'help';
    warning.textContent = '寸法または位置の一部は3D表示用の仮値です。';
    selection.appendChild(warning);
  }
  if (entity.url) {
    const link = document.createElement('a');
    link.href = entity.url;
    link.textContent = '詳細を開く';
    selection.appendChild(link);
  }
}

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
renderer.domElement.addEventListener('click', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(interactiveMeshes, false)[0];
  if (hit?.object?.userData?.entity) setSelection(hit.object.userData.entity);
});

resetButton?.addEventListener('click', fitRoom);

const highlighted = data.highlight
  ? entityMeshes.get(`${data.highlight.type}:${data.highlight.code}`)
  : null;
if (highlighted) {
  const box = new THREE.Box3().setFromObject(highlighted);
  fitBox(box, 4.0);
  setSelection(highlighted.userData.entity);
} else {
  fitRoom();
}

function resize() {
  const width = Math.max(1, container.clientWidth);
  const height = Math.max(1, container.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

const resizeObserver = new ResizeObserver(resize);
resizeObserver.observe(container);
resize();
loading?.remove();

function animate() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
animate();
