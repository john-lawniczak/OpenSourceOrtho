// Upload time is an observation; capture date is optional information from the user.
export function newScanDates(files, uploadedAt = new Date().toISOString()) {
  return Array.from(files, file => ({ name: file.name, size: file.size, lastModified: file.lastModified,
    uploaded_at: uploadedAt, captured_on: null }));
}
export function sameScanFile(a, b) {
  return Boolean(a && b && a.name === b.name && a.size === b.size && a.lastModified === b.lastModified);
}
export function matchScanDates(files, entries = []) {
  return Array.from(files, file => entries.find(entry => sameScanFile(file, entry))
    || { ...newScanDates([file], null)[0] });
}
export function validCaptureDate(value) {
  if (value === "" || value === null) return true;
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value))
    && new Date(value).toISOString().slice(0, 10) === value;
}
