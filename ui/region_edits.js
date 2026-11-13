// Face-order corrections preserve original mesh bytes and explicit undo history.
export class RegionEdits {
  constructor(labels, arch) {
    this.labels = new Uint8Array(labels); this.arch = arch; this.undoStack = []; this.redoStack = [];
    this.stroke = null; this.provenance = "user-corrected";
  }
  beginStroke() { this.endStroke(); this.stroke = new Map(); }
  endStroke() {
    if (!this.stroke) return;
    const changes = [...this.stroke.values()].filter(([i, before]) => this.labels[i] !== before)
      .map(([i, before]) => [i, before, this.labels[i]]);
    this.stroke = null; this.record(changes);
  }
  record(changes) {
    if (!changes.length) return;
    this.provenance = "user-corrected";
    this.undoStack.push(changes); this.undoStack = this.undoStack.slice(-50); this.redoStack = [];
  }
  valid(id) { return id === 0 || (Number.isInteger(id) && (this.arch === "upper" ? /^[12][1-8]$/ : /^[34][1-8]$/).test(String(id))); }
  paint(faces, target, source = null) {
    if (this.absentTeeth?.includes(target)) throw new Error(`Tooth ${target} is reported removed for this case. Choose a present tooth.`);
    if (!this.valid(target) || (source !== null && !this.valid(source))) throw new Error("Choose a valid tooth number for this arch.");
    const changes = [];
    for (const face of new Set(faces)) {
      if (!Number.isInteger(face) || face < 0 || face >= this.labels.length) throw new Error("Face outside source mesh.");
      const before = this.labels[face];
      if (before !== target && (source === null || before === source)) changes.push([face, before, target]);
    }
    changes.forEach(([i, , after]) => { this.labels[i] = after; });
    if (this.stroke) {
      for (const change of changes) if (!this.stroke.has(change[0])) this.stroke.set(change[0], change);
    } else this.record(changes);
    return changes.length;
  }
  merge(source, target) { return this.paint(Array.from(this.labels.keys()).filter(i => this.labels[i] === source), target, source); }
  undo() { const change = this.undoStack.pop(); if (!change) return; change.forEach(([i, before]) => { this.labels[i] = before; }); this.redoStack.push(change); }
  redo() { const change = this.redoStack.pop(); if (!change) return; change.forEach(([i, , after]) => { this.labels[i] = after; }); this.undoStack.push(change); }
  export(sha256, reviewed = false) {
    let binary = "";
    for (let i = 0; i < this.labels.length; i += 8192) binary += String.fromCharCode(...this.labels.subarray(i, i + 8192));
    return { schema: "ortho-region-corrections-v1", source_sha256: sha256, arch: this.arch,
      face_count: this.labels.length, labels_base64: btoa(binary), reviewed: Boolean(reviewed), provenance: reviewed ? "user-corrected" : this.provenance };
  }
  static restore(record, sha256, count, arch) {
    if (record.schema !== "ortho-region-corrections-v1" || record.source_sha256 !== sha256
      || record.face_count !== count || record.arch !== arch) throw new Error("Correction file belongs to another scan.");
    const labels = Uint8Array.from(atob(record.labels_base64), c => c.charCodeAt(0));
    const edits = new RegionEdits(labels, arch);
    edits.provenance = record.provenance === "automatic-draft" ? "automatic-draft" : "user-corrected";
    if (labels.length !== count || labels.some(id => !edits.valid(id))) throw new Error("Invalid tooth labels.");
    return edits;
  }
}
