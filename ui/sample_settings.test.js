import test from 'node:test';
import assert from 'node:assert/strict';
import { isolateSampleSettings } from './sample_settings.js';
import { state } from './state.js';

test('sample controls and generation are isolated, then restored including DOM fields', (t) => {
  const fields = new Map();
  const original = globalThis.document;
  t.after(() => { globalThis.document = original; });
  globalThis.document = { getElementById(id) {
    if (!fields.has(id)) fields.set(id, { value: `personal-${id}`, checked: true });
    return fields.get(id);
  } };
  const controls = state.clinicalControls = { fixedTeeth: '21', iprContacts: { '11-21': .2 } };
  const generation = state.generation = { busy: true, landmarks: { personal: true }, result: { source: 'personal' } };
  const restore = isolateSampleSettings();
  assert.deepEqual(state.clinicalControls.iprContacts, {});
  assert.equal(state.generation.busy, false);
  assert.equal(state.generation.landmarks, null);
  assert.equal(fields.get('fixedTeeth').value, '');
  assert.equal(fields.get('printSafety').checked, false);
  state.clinicalControls.iprContacts['11-21'] = .9;
  fields.get('capLinear').value = '.9';
  restore();
  assert.equal(state.clinicalControls, controls);
  assert.equal(controls.iprContacts['11-21'], .2);
  assert.equal(state.generation, generation);
  assert.equal(fields.get('capLinear').value, 'personal-capLinear');
  assert.equal(fields.get('printSafety').checked, true);
});
