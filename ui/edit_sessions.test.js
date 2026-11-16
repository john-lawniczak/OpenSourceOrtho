import test from "node:test";
import assert from "node:assert/strict";
import { state } from "./state.js";
import { pushEditUndo, travelEdit, validateEditSession } from "./edit_sessions.js";
const row = x => ({tooth:"11",stage:0,x,y:0,z:0,tip:0,torque:0,rotation:0});
test("undo and redo preserve applied rows; a new branch clears redo",()=>{
  state.manualEdit={}; state.goalPreview=null; state.goalBusy=false; state.rows=[row(0)];
  pushEditUndo();state.rows=[row(.2)];
  assert.equal(travelEdit("undo"),true);assert.equal(state.rows[0].x,0);
  assert.equal(travelEdit("redo"),true);assert.equal(state.rows[0].x,.2);
  travelEdit("undo");pushEditUndo();state.rows=[row(.4)];
  assert.equal(travelEdit("redo"),false);
  state.goalPreview={};assert.equal(travelEdit("undo"),false);state.goalPreview=null;
});
test("recovery validates all history before changing the workspace",()=>{
  const valid={rows:[row(.2)],held:["11"],undo:[[row(0)]],redo:[]};
  const restored=validateEditSession(valid,["11"]);
  restored.rows[0].x=.5;assert.equal(valid.rows[0].x,.2);
  for(const change of [{held:["12"]},{rows:[row(NaN)]},{redo:[[{...row(0),tooth:"12"}]]},{undo:null}]) {
    assert.throws(()=>validateEditSession({...valid,...change},["11"]));
  }
});
