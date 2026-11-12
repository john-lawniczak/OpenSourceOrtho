import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { historyFrame, simulationFraction } from "./scan_history.js";
import { proximitySummary } from "./proximity_summary.js";
const path = new URL("../datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/derived/progress-01-motion-upper.json",import.meta.url);
test("all generated timing profiles preserve endpoints and drive actual frame fractions",()=>{
  const motion=JSON.parse(readFileSync(path));
  for(const timing of ["uniform","smooth","delayed"]) {
    assert.equal(simulationFraction(1,motion.simulation,timing),0);
    assert.equal(simulationFraction(7,motion.simulation,timing),1);
    const frame=historyFrame(3,[{},{}],motion,false,timing);
    assert.equal(frame.fraction,motion.simulation.profiles[timing].fractions[2]);
  }
  assert.notEqual(simulationFraction(3,motion.simulation,"uniform"),simulationFraction(3,motion.simulation,"smooth"));
  assert.equal(historyFrame(3,[],null,false,"delayed").kind,"unavailable");
  assert.match(proximitySummary([{arch:"upper",simulation:motion.simulation}],3,"smooth"),/does not establish clearance/);
  assert.throws(()=>simulationFraction(3,{profiles:{uniform:{fractions:[0,.9,.2,.3,.4,.5,1]}}}),/Invalid/);
});
