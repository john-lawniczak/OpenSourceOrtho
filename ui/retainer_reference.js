import { meshHash, sourcePositions } from "./surface_repair_mesh.js";

export async function prepareRetainerReference(bytes, options) {
  if (!(bytes instanceof ArrayBuffer) || !bytes.byteLength || bytes.byteLength>50_000_000) throw new Error("Choose an STL of up to 50 MB.");
  if (!options.currentScan) throw new Error("Confirm that this is the current scan you want to review.");
  if (!["upper","lower"].includes(options.arch)) throw new Error("Choose the scan's arch.");
  if (!["unverified","mm","cm","inch","meter"].includes(options.units)) throw new Error("Choose the scan units or Unverified.");
  const date=options.captureDate||null;
  const parsedDate=date?new Date(`${date}T00:00:00Z`):null;
  if(date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(parsedDate.getTime()) || parsedDate.toISOString().slice(0,10)!==date)) throw new Error("Enter a valid scan date.");
  const positions=sourcePositions(bytes),count=positions.length/9;
  if(!Number.isInteger(count)||count<1||count>1_000_000||positions.some(v=>!Number.isFinite(v))) throw new Error("The STL needs 1–1,000,000 finite triangles.");
  const sha256=await meshHash(bytes);
  return {
    schema:"ortho-retainer-preparation-v1",created_at:new Date().toISOString(),
    purpose:"retainer-reference-review",review_status:"unreviewed-reference-only",
    source:{filename:String(options.filename||"scan.stl").split(/[\\/]/).at(-1),sha256,byte_length:bytes.byteLength,face_count:count,
      arch:options.arch,declared_units:options.units,capture_date:date,current_scan_confirmed:true},
    reference_model:{filename:`${options.arch}-retainer-reference.stl`,sha256,geometry:"unchanged-source-coordinates"},
    proposed_movements:[],stage_count:0,wearable_output:false,
    next_review:["scan completeness and scale","fit review","appropriate materials","appropriate processing"],
    scope:"Reference model only. No retainer shell, fit approval, or wearable output has been produced.",
  };
}
