import test from "node:test";
import assert from "node:assert/strict";
import { assignmentEvidenceText } from "./assignment_evidence.js";
import { fitConsistencyText } from "./fit_consistency.js";
import { suggestedMatch } from "./progress_match_review.js";

test("identity ambiguity remains visible even when fit consistency is missing", () => {
  const tooth = {assignment_evidence:{status:"assigned-draft",ambiguous:true,alternative_cost_increase:0,candidates:[{target_tooth:"11"},{target_tooth:"12"}]}};
  assert.match(fitConsistencyText(tooth), /Ambiguous endpoint identity/);
  assert.match(assignmentEvidenceText(tooth), /11, 12/);
  assert.match(assignmentEvidenceText(tooth), /not an identity probability/);
  assert.match(assignmentEvidenceText({assignment_evidence:{status:"unmatched-competing-regions"}}), /needs identity review/);
  assert.equal(assignmentEvidenceText({}), "");
});

test("match review starts with the actual independent candidate, preserving explicit holds", () => {
  const tooth = {tooth:"11",target_tooth:"11",independent_target_label:"12"};
  assert.equal(suggestedMatch(tooth,["11","12"],null), "12");
  assert.equal(suggestedMatch(tooth,["11","12"],{"11":null}), "");
  assert.equal(suggestedMatch({...tooth,independent_target_label:null},["11","12"],null), "");
  assert.equal(suggestedMatch({tooth:"11",target_tooth:"12"},["11","12"],null), "12");
});
