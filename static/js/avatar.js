/* ═══════════════════════════════════════════════════
   avatar.js — Ready Player Me Avatar "Alex"
   Correct arm/hand animations — offset from bind pose
═══════════════════════════════════════════════════ */

let _scene, _cam, _ren, _clk;
let _model, _bones = {}, _bindQ = {};
let _av = {
  talking:false, listening:false, waving:false,
  t:0, breathT:0, blinkT:0, jawOpen:0, jawTarget:0, wavePhase:0
};

function initAvatar() {
  const panel = document.getElementById('avPanel');
  if (!panel) return;
  const old = document.getElementById('av-canvas');
  if (old) old.remove();

  const canvas = document.createElement('canvas');
  canvas.id = 'av-canvas';
  canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:2;display:block;';
  panel.insertBefore(canvas, panel.firstChild);

  if (typeof THREE === 'undefined' || typeof THREE.GLTFLoader === 'undefined') {
    console.error('Three.js / GLTFLoader not ready'); showFallback(); return;
  }
  _boot(canvas, panel);
}

function _boot(canvas, panel) {
  _ren = new THREE.WebGLRenderer({ canvas, antialias:true, alpha:true });
  _ren.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  _ren.shadowMap.enabled = true;
  _ren.shadowMap.type    = THREE.PCFSoftShadowMap;
  _ren.outputEncoding    = THREE.sRGBEncoding;
  _ren.toneMapping       = THREE.ACESFilmicToneMapping;
  _ren.toneMappingExposure = 1.25;

  _scene = new THREE.Scene();
  _clk   = new THREE.Clock();

  const W = panel.clientWidth  || 420;
  const H = panel.clientHeight || 600;
  _ren.setSize(W, H);
  _cam = new THREE.PerspectiveCamera(40, W / H, 0.01, 100);
  _cam.position.set(0, 1.6, 3.2);
  _cam.lookAt(0, 0.9, 0);

  /* Lights */
  _scene.add(new THREE.AmbientLight(0xfff0e8, 0.7));
  const sun = new THREE.DirectionalLight(0xfff8f0, 2.2);
  sun.position.set(2, 5, 3); sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024); _scene.add(sun);
  const fill = new THREE.DirectionalLight(0x8090ff, 0.5);
  fill.position.set(-3, 2, 1); _scene.add(fill);
  const rim = new THREE.DirectionalLight(0xff2800, 0.4);
  rim.position.set(0, 3, -5); _scene.add(rim);
  const pt = new THREE.PointLight(0xc8972a, 1.0, 6);
  pt.position.set(0, 0.5, 2); _scene.add(pt);

  /* Floor */
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(1.2, 48),
    new THREE.MeshStandardMaterial({ color:0x160a04, roughness:0.9, metalness:0.05 })
  );
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
  _scene.add(floor);

  /* Gold ring */
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.18, 0.75, 64),
    new THREE.MeshBasicMaterial({ color:0xc8972a, transparent:true, opacity:0.12, side:THREE.DoubleSide })
  );
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.002;
  _scene.add(ring);

  try {
    new ResizeObserver(() => {
      const w = panel.clientWidth, h = panel.clientHeight;
      if (!w || !h) return;
      _cam.aspect = w / h; _cam.updateProjectionMatrix(); _ren.setSize(w, h);
    }).observe(panel);
  } catch(e) {}

  _loadModel();
  _loop();
}

function _loadModel() {
  const ui = _mkLoadUI();
  new THREE.GLTFLoader().load('/static/assets/avatar.glb',
    gltf => {
      ui.remove();
      _model = gltf.scene;

      /* Auto-fit: scale so height ≈ 1.75m, place feet at y=0 */
      const box = new THREE.Box3().setFromObject(_model);
      const sz  = new THREE.Vector3(); box.getSize(sz);
      const sc  = 1.75 / sz.y;
      _model.scale.setScalar(sc);
      _model.position.y = -box.min.y * sc;
      _model.position.x = 0;
      _model.rotation.y = 0;

      _model.traverse(obj => {
        if (obj.isMesh) {
          obj.castShadow = obj.receiveShadow = true;
          (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(m => {
            if (m?.map) m.map.anisotropy = 4;
            if (m) m.depthWrite = true;
          });
        }
      });
      _scene.add(_model);

      /* Re-fit camera */
      const box2 = new THREE.Box3().setFromObject(_model);
      const sz2  = new THREE.Vector3(); box2.getSize(sz2);
      const cy   = box2.min.y + sz2.y * 0.52;
      const cz   = sz2.y * 1.65;
      _cam.position.set(0, cy, cz);
      _cam.lookAt(0, cy * 0.78, 0);
      _cam.updateProjectionMatrix();

      /* Collect bones AND save their bind-pose quaternions */
      _model.traverse(obj => {
        const n = obj.name;
        const key = {
          'Hips':'hips','Spine':'sp1','Spine1':'sp2','Spine2':'sp3',
          'Neck':'neck','Head':'head',
          'LeftEye':'eyeL','RightEye':'eyeR',
          'LeftShoulder':'shlL','LeftArm':'armL','LeftForeArm':'forL','LeftHand':'hnL',
          'LeftHandIndex1':'liI1','LeftHandIndex2':'liI2',
          'LeftHandMiddle1':'liM1','LeftHandRing1':'liR1',
          'LeftHandPinky1':'liP1',
          'LeftHandThumb1':'liT1','LeftHandThumb2':'liT2',
          'RightShoulder':'shlR','RightArm':'armR','RightForeArm':'forR','RightHand':'hnR',
          'RightHandIndex1':'riI1','RightHandIndex2':'riI2',
          'RightHandMiddle1':'riM1','RightHandRing1':'riR1',
          'RightHandPinky1':'riP1',
          'RightHandThumb1':'riT1','RightHandThumb2':'riT2',
        }[n];
        if (key) {
          _bones[key] = obj;
          /* Save bind pose quaternion BEFORE any animation */
          _bindQ[key] = obj.quaternion.clone();
        }
      });

      console.log('Alex loaded. Bones:', Object.keys(_bones).length);

      /* Debug: log bind pose quaternions to find correct axes */
      ['armR','armL','forR','forL'].forEach(k => {
        const b = _bones[k];
        if (b) {
          const wp = new THREE.Vector3();
          b.getWorldPosition(wp);
          console.log(k, 'worldPos:', wp.x.toFixed(3), wp.y.toFixed(3), wp.z.toFixed(3),
            'quatBind:', _bindQ[k].x.toFixed(4), _bindQ[k].y.toFixed(4), _bindQ[k].z.toFixed(4), _bindQ[k].w.toFixed(4));
        }
      });

      /* Force arms down from T-pose IMMEDIATELY */
      _forceArmsDown();

      /* Wave on load after short delay */
      setTimeout(() => { _av.waving = true; setTimeout(() => { _av.waving = false; }, 3500); }, 600);

      /* Welcome */
      setTimeout(() => {
        setBubble("Hi! I'm Alex, your liquor expert. How can I help?", 'happy');
        setTimeout(() => speak("Welcome! I'm Alex, your personal liquor expert. How can I help you today?"), 700);
      }, 1000);
    },
    xhr => {
      if (xhr.total > 0) {
        const p = Math.round(xhr.loaded / xhr.total * 100);
        const b = ui.querySelector('.lb'); if (b) b.style.width = p + '%';
        const t = ui.querySelector('.lt'); if (t) t.textContent = 'Loading Alex… ' + p + '%';
      }
    },
    err => { console.error('GLB error:', err); ui.remove(); showFallback(); }
  );
}

/* ── Render loop ── */
function _loop() {
  requestAnimationFrame(_loop);
  if (!_ren || !_scene || !_cam) return;
  const dt = Math.min(_clk.getDelta(), 0.05);
  _av.t += dt; _av.breathT += dt; _av.blinkT += dt;
  if (_model && Object.keys(_bones).length > 0) _animate(dt);
  _cam.position.x = Math.sin(_av.t * 0.18) * 0.04;
  _ren.render(_scene, _cam);
}

/* ── Quaternion helpers ── */
const _TQ  = new THREE.Quaternion();
const _E   = new THREE.Euler();
const _ZERO = new THREE.Quaternion();

/* Apply an OFFSET rotation on top of bind pose */
function _rotOffset(key, x, y, z, s) {
  const bone = _bones[key];
  const bind = _bindQ[key];
  if (!bone || !bind) return;
  _E.set(x, y, z, 'XYZ');
  _TQ.setFromEuler(_E);
  // target = bind * offset
  const target = bind.clone().multiply(_TQ);
  bone.quaternion.slerp(target, s);
}

/* Reset a bone toward its bind pose */
function _rotBind(key, s) {
  const bone = _bones[key];
  const bind = _bindQ[key];
  if (!bone || !bind) return;
  bone.quaternion.slerp(bind, s);
}

/* ── Main animation ── */
function _animate(dt) {
  const t = _av.t;

  /* Breathing */
  const br = Math.sin(_av.breathT * 1.0) * 0.012;
  _rotOffset('sp1', br,       0, 0, 0.06);
  _rotOffset('sp2', br * 0.6, 0, 0, 0.05);
  _rotOffset('sp3', br * 0.3, 0, 0, 0.04);

  /* Head subtle sway */
  const hx = _av.talking ? Math.sin(t * 6.5) * 0.025 : Math.sin(t * 0.5) * 0.012;
  const hy  = Math.sin(t * 0.4) * 0.028;
  _rotOffset('head', hx, hy, Math.sin(t * 0.27) * 0.01, 0.09);
  _rotOffset('neck', Math.sin(t * 0.34) * 0.01, Math.sin(t * 0.4) * 0.015, 0, 0.07);

  /* Eyes */
  _rotOffset('eyeL', Math.sin(t * 0.3) * 0.025, Math.sin(t * 0.22) * 0.018, 0, 0.05);
  _rotOffset('eyeR', Math.sin(t * 0.3) * 0.025, Math.sin(t * 0.22) * 0.018, 0, 0.05);

  /* Jaw / lip sync via head micro-nod */
  _av.jawTarget = _av.talking ? Math.abs(Math.sin(t * 13)) * 0.028 : 0;
  _av.jawOpen   = _av.jawOpen * 0.75 + _av.jawTarget * 0.25;
  if (_av.jawOpen > 0.002) _rotOffset('head', hx + _av.jawOpen, hy, 0, 0.3);

  /* Auto-blink */
  if (_av.blinkT > 4.0 + Math.random() * 2.5) {
    _av.blinkT = 0;
    const eL = _bones.eyeL, eR = _bones.eyeR;
    if (eL) { eL.scale.y = 0.05; eR.scale.y = 0.05; setTimeout(() => { if(eL){eL.scale.y=1;eR.scale.y=1;} }, 110); }
  }

  /* Arms */
  if      (_av.waving)   _wave(t, dt);
  else if (_av.talking)  _talk(t, dt);
  else if (_av.listening) _listen(t);
  else                   _idle(t);
}

/* ── Force arms down from T-pose immediately ── */
function _forceArmsDown() {
  /* 
   * GLB bone analysis: bone chain goes along local Y-axis.
   * Shoulder quaternion orients arms horizontal (T-pose).
   * Positive X rotation swings arms downward.
   */
  _setDirect('armR', 'XYZ', [1.45, 0, 0]);
  _setDirect('armL', 'XYZ', [1.45, 0, 0]);
  _setDirect('forR', 'XYZ', [0, 0, 0]);
  _setDirect('forL', 'XYZ', [0, 0, 0]);
  _setDirect('hnR',  'XYZ', [0, 0, 0]);
  _setDirect('hnL',  'XYZ', [0, 0, 0]);
}

function _setDirect(key, order, angles) {
  const bone = _bones[key], bind = _bindQ[key];
  if (!bone || !bind) return;
  const e = new THREE.Euler(angles[0], angles[1], angles[2], order);
  const q = new THREE.Quaternion().setFromEuler(e);
  bone.quaternion.copy(bind.clone().multiply(q));
}

/* ── Arms-down offset: X rotation of ~-85° brings arm from T-pose to vertical ── */
const _DN = 1.45;  /* radians, ~83° downward pitch (positive X = down) */

/* ── WAVE: raise right arm, hand waves ── */
function _wave(t, dt) {
  _av.wavePhase += dt * 3.8;
  const w = _av.wavePhase;
  const S = 0.22;

  /* Right arm: swing back up from down for wave (1.45 → ~0.3) */
  _rotOffset('armR', 0.3 + Math.sin(w)*0.08, 0, 0, S);
  _rotOffset('forR', -1.3, 0, 0, S);
  _rotOffset('hnR', 0, Math.sin(w*1.4)*0.5, Math.sin(w*1.1)*0.2, 0.25);

  const fw = Math.sin(w*1.6)*0.08;
  _rotOffset('riI1', -0.05+fw, 0, 0, 0.18);
  _rotOffset('riI2', -0.04, 0, 0, 0.18);
  _rotOffset('riM1', -0.05+fw, 0, 0, 0.18);
  _rotOffset('riR1', 0.03+fw, 0, 0, 0.18);
  _rotOffset('riP1', 0.06+fw, 0, 0, 0.18);
  _rotOffset('riT1', 0.08, -0.28, 0, 0.18);
  _rotOffset('riT2', 0.05, 0, 0, 0.18);

  /* Left arm stays down */
  _rotOffset('armL', _DN, 0, 0, 0.15);
  _rotOffset('forL', 0, 0, 0, 0.15);
  _rotOffset('hnL', 0, 0, 0, 0.12);
  _relaxFingers('L', 0.08);
}

/* ── TALK: arms mostly down, subtle gestures ── */
function _talk(t, dt) {
  const S = 0.18;

  /* Right arm: slightly raised from down with gesture */
  _rotOffset('armR', _DN - 0.35 - Math.sin(t*2.1)*0.12, Math.sin(t*1.7)*0.05, 0, S);
  _rotOffset('forR', -0.25 + Math.sin(t*2.4)*0.1, 0, 0, S);
  _rotOffset('hnR', Math.sin(t*2.8)*0.06, Math.sin(t*1.9)*0.05, 0, S);

  const rc = 0.15+Math.sin(t*3.2)*0.06;
  _rotOffset('riI1', rc, 0, 0.02, 0.14);
  _rotOffset('riI2', rc*0.8, 0, 0, 0.14);
  _rotOffset('riM1', rc*0.85, 0, 0, 0.14);
  _rotOffset('riR1', rc*0.9, 0, -0.02, 0.14);
  _rotOffset('riP1', rc, 0, -0.04, 0.14);
  _rotOffset('riT1', 0.12, -0.22, 0.08, 0.14);
  _rotOffset('riT2', 0.08, 0, 0, 0.14);

  /* Left arm: mostly down, slight mirror gesture */
  _rotOffset('armL', _DN - 0.2 - Math.sin(t*2.0)*0.08, Math.sin(t*1.6)*0.04, 0, S);
  _rotOffset('forL', -0.2 + Math.sin(t*2.2)*0.08, 0, 0, S);
  _rotOffset('hnL', Math.sin(t*2.6)*0.05, Math.sin(t*1.8)*0.04, 0, S);

  const lc = 0.12+Math.sin(t*2.8)*0.05;
  _rotOffset('liI1', lc, 0, 0.02, 0.12);
  _rotOffset('liI2', lc*0.8, 0, 0, 0.12);
  _rotOffset('liM1', lc*0.85, 0, 0, 0.12);
  _rotOffset('liR1', lc*0.9, 0, -0.02, 0.12);
  _rotOffset('liP1', lc, 0, -0.04, 0.12);
  _rotOffset('liT1', 0.1, 0.2, 0.07, 0.12);
  _rotOffset('liT2', 0.07, 0, 0, 0.12);
}

/* ── LISTEN: arms down ── */
function _listen(t) {
  const S = 0.18;
  _rotOffset('armR', _DN + Math.sin(t*0.5)*0.02, 0, 0, S);
  _rotOffset('forR', 0, 0, 0, S);
  _rotOffset('armL', _DN + Math.sin(t*0.48)*0.02, 0, 0, S);
  _rotOffset('forL', 0, 0, 0, S);
  _rotOffset('hnR', 0, 0, 0, 0.12);
  _rotOffset('hnL', 0, 0, 0, 0.12);
  _relaxFingers('R', 0.08);
  _relaxFingers('L', 0.08);
}

/* ── IDLE: arms straight down ── */
function _idle(t) {
  const S = 0.25;
  const sw = Math.sin(t*0.55)*0.01;

  _rotOffset('shlR', 0, 0, 0, S);
  _rotOffset('shlL', 0, 0, 0, S);
  _rotOffset('armR', _DN + sw, 0, 0, S);
  _rotOffset('armL', _DN - sw, 0, 0, S);
  _rotOffset('forR', 0, 0, 0, S);
  _rotOffset('forL', 0, 0, 0, S);
  _rotOffset('hnR', 0, 0, 0, 0.15);
  _rotOffset('hnL', 0, 0, 0, 0.15);
  _relaxFingers('R', 0.08);
  _relaxFingers('L', 0.08);
}

/* ── Natural resting finger curl ── */
function _relaxFingers(side, s) {
  const p = side==='R'?'ri':'li';
  const ts = side==='R'?-1:1;
  const c = 0.06;
  _rotOffset(p+'I1', c, 0, 0, s);
  _rotOffset(p+'I2', c*0.8, 0, 0, s);
  _rotOffset(p+'M1', c, 0, 0, s);
  _rotOffset(p+'R1', c, 0, 0, s);
  _rotOffset(p+'P1', c*1.05, 0, 0, s);
  _rotOffset(p+'T1', 0.05, ts*0.14, 0.04, s);
  _rotOffset(p+'T2', 0.03, 0, 0, s);
}

/* ── Loading UI ── */
function _mkLoadUI() {
  const d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;z-index:20;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(8,4,2,0.92)';
  d.innerHTML = `<div style="width:48px;height:48px;border:2.5px solid rgba(200,151,42,0.2);border-top-color:#C8972A;border-radius:50%;animation:avSpin 1s linear infinite;margin-bottom:16px"></div><div class="lt" style="font-size:12px;color:rgba(200,151,42,0.82);font-family:sans-serif;margin-bottom:12px">Loading Alex…</div><div style="width:160px;height:3px;background:rgba(200,151,42,0.14);border-radius:2px"><div class="lb" style="height:100%;width:0%;background:linear-gradient(90deg,#A07820,#E8B84B);border-radius:2px;transition:width .25s ease"></div></div><style>@keyframes avSpin{to{transform:rotate(360deg)}}</style>`;
  document.getElementById('avPanel')?.appendChild(d);
  return d;
}

function showFallback() {
  const p = document.getElementById('avPanel'); if (!p) return;
  const d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;z-index:5;display:flex;flex-direction:column;align-items:center;justify-content:center;color:rgba(245,237,216,0.5);font-family:sans-serif;font-size:13px;text-align:center;padding:1rem';
  d.innerHTML = '<div style="font-size:60px;margin-bottom:14px">🧑‍💼</div><div style="color:#C8972A;font-size:17px;margin-bottom:5px">Alex</div><div>AI Sommelier</div>';
  p.appendChild(d);
}

/* ── Public API ── */
function setAvatarTalking(on) {
  if (on) {
    /* Wave briefly at the start of every reply, then talk */
    _av.waving = true;
    _av.wavePhase = 0;
    _av.listening = false;
    _av.talking = false;
    setTimeout(() => {
      _av.waving = false;
      _av.talking = true;
    }, 2200);
  } else {
    _av.talking = false;
    _av.waving = false;
  }
}
function setAvatarListening(on) {
  _av.listening = on; _av.talking = false; if (on) _av.waving = false;
}
function setEmotion(name) {
  const m = { happy:'😊', excited:'😄', thinking:'🤔', surprised:'😮', cool:'😎' };
  const el = document.getElementById('emoBadge');
  if (el) el.textContent = m[name] || '😊';
  if ((name==='excited'||name==='surprised') && !_av.waving) {
    _av.waving = true; setTimeout(() => { _av.waving = false; }, 2600);
  }
}

function init3D()    { initAvatar(); }
function animate3D() {}
