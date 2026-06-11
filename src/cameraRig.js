// Orbita dall'alto: auto-rotazione + drag con easing (parametri stile adidas)
import { PerspectiveCamera, Vector3 } from 'three';

const AUTO_SPEED = 0.07;       // rad/s
const DRAG_SPEED = 0.0025 * 2; // rad/px (adidas: dragSpeed * speed)
const EASE = 0.04;
const RESUME_DELAY = 2.0;      // s senza input prima di riprendere l'auto-orbita

export class CameraRig {
  constructor(dom, { radius = 120, elevation = 0.62, target = new Vector3(0, 4, 0) } = {}) {
    this.camera = new PerspectiveCamera(26, 1, 1, 800);
    this.dom = dom;
    this.radius = radius;
    this.elevation = elevation;
    this.target = target;

    this.azimuth = Math.PI * 0.42; // inquadratura iniziale sul fronte del palazzo
    this.dragTarget = 0;
    this.dragCurrent = 0;
    this.idleTime = 0;
    this.dragging = false;
    this._lastX = 0;

    dom.addEventListener('pointerdown', (e) => {
      this.dragging = true;
      this._lastX = e.clientX;
      dom.classList.add('dragging');
      dom.setPointerCapture(e.pointerId);
    });
    dom.addEventListener('pointermove', (e) => {
      if (!this.dragging) return;
      this.dragTarget += (e.clientX - this._lastX) * DRAG_SPEED;
      this._lastX = e.clientX;
      this.idleTime = 0;
    });
    const end = () => {
      this.dragging = false;
      dom.classList.remove('dragging');
    };
    dom.addEventListener('pointerup', end);
    dom.addEventListener('pointercancel', end);
  }

  update(dt) {
    if (!this.dragging) {
      this.idleTime += dt;
      if (this.idleTime > RESUME_DELAY) this.azimuth += AUTO_SPEED * dt;
    }
    this.dragCurrent += (this.dragTarget - this.dragCurrent) * EASE * (dt * 60);

    const a = this.azimuth + this.dragCurrent;
    const r = this.radius * Math.cos(this.elevation);
    this.camera.position.set(
      this.target.x + r * Math.cos(a),
      this.target.y + this.radius * Math.sin(this.elevation),
      this.target.z + r * Math.sin(a),
    );
    this.camera.lookAt(this.target);
  }

  resize(w, h) {
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }
}
