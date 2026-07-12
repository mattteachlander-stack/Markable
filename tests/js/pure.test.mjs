// Unit tests for the browser bundle's pure module — run with: node --test tests/js
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const P = require("../../src/markable/webapp/00-pure.js");

test("answer-leak: strip removes option markers, detector catches residue", () => {
  const md = "## Q1 [mcq, 1]\nPick\n- A) a\n- B) b *\n- C) c\nAnswer: B because…";
  const stripped = P.stripAnswerMarkers(md);
  assert.ok(!/\*\s*$/m.test(stripped.split("\n")[3]), "marker removed");
  const leaks = P.detectAnswerLeaks(stripped);
  assert.equal(leaks.length, 1);            // the Answer: line survives strip
  assert.match(leaks[0], /Answer/);
  assert.equal(P.detectAnswerLeaks("## Q1\n- A) a\n- B) b").length, 0);
});

test("validateResult: clamps, independent confidence floor, duplicates, blanks", () => {
  const r = P.validateResult({ student_label: "S", judgements: [
    { question: "Q1", marks_awarded: 5, marks_available: 1, confidence: 1.7,
      transcription: "C", needs_review: false },
    { question: "Q1", marks_awarded: -2, marks_available: 2, confidence: 0.4,
      transcription: "", needs_review: false },
    { question: "Q2", marks_awarded: 2, marks_available: 2, confidence: 0.95,
      transcription: "ok", needs_review: false },
  ]});
  const [a, b, c] = r.judgements;
  assert.equal(a.marks_awarded, 1);                        // clamped to max
  assert.equal(a.confidence, 1);                           // clamped to 1
  assert.ok(a._review && a._flags.some(f => /clamped/.test(f)));
  assert.equal(b.marks_awarded, 0);                        // negative → 0
  assert.ok(b._flags.some(f => /duplicate question id/.test(f)));
  assert.ok(b._flags.some(f => /blank|transcription/.test(f)));
  assert.ok(b._review);                                    // conf 0.4 < 0.85
  assert.equal(c._review, false);                          // clean item passes
});

test("gridExtents: real extents, capped", () => {
  const g = { 1: { 0: "x" }, 350: { 200: "y" } };
  const e = P.gridExtents(g);
  assert.equal(e.rmax, 350);
  assert.equal(e.cmax, 200);
  assert.equal(P.gridExtents({ 9999: { 600: 1 } }).cmax, 512); // cap
});

test("keyYaml round-trips through parseKeyYaml", () => {
  const key = { test_id: "T-1", total_marks: 3, questions: [
    { id: "Q1", type: "mcq", marks: 1, correct: "C",
      distractor_notes: { A: "sign confusion" }, review_threshold: 0.85 },
    { id: "Q2", type: "numerical", marks: 2,
      criteria: [{ point: "uses n = m/M", marks: 1 }, { point: "final answer", marks: 1 }],
      accept: ["2 mol"], reject: ["36"], final_answer: "2 mol", tolerance: 0.01,
      review_threshold: 0.85 },
  ]};
  const parsed = P.parseKeyYaml(P.keyYaml(key));
  assert.equal(parsed.test_id, "T-1");
  assert.equal(parsed.questions.length, 2);
  assert.equal(parsed.questions[0].correct, "C");
  assert.equal(parsed.questions[1].criteria.length, 2);
  assert.equal(parsed.questions[1].tolerance, 0.01);
  assert.equal(P.parseKeyYaml("just some prose"), null);
});

test("docx/pdf exporters emit valid magic bytes", () => {
  const docx = P.mdToDocx("# T\nhello");
  assert.deepEqual([...docx.slice(0, 4)], [0x50, 0x4b, 3, 4]);   // PK zip
  const pdf = Buffer.from(P.mdToPdf("# T\nhello — ≥ tricky chars"));
  assert.ok(pdf.subarray(0, 8).toString().startsWith("%PDF-1.4"));
  assert.ok(pdf.toString().includes("%%EOF"));
});

test("crc32 known vector", () => {
  const enc = new TextEncoder();
  assert.equal(P.crc32(enc.encode("123456789")), 0xCBF43926);
});
