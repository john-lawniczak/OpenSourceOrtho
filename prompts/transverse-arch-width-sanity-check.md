# Transverse arch-width sanity check (iTero / OrthoCAD export)

**What this is:** an example prompt for asking an AI analysis agent to
independently sanity-check whether upper-vs-lower arch widths support a claimed
**maxillary transverse (width) deficiency**, using the files in a typical iTero
intraoral-scanner (OrthoCAD) export.

**What this is not:** a diagnosis, a second opinion, or a recommendation for or
against a palatal expander. It explicitly asks the agent to state its limitations
and to hand the decision back to a licensed provider. Arch width measured off a
surface shell includes gingiva/bone, so absolute numbers run high — only the
upper-vs-lower *comparison* is meaningful, and a crossbite is a clinical/occlusal
finding a mesh cannot establish.

---

## Prompt

```text
I'm attaching a zip exported from an iTero intraoral scanner (OrthoCAD export).
It contains: an Rx in HTML/PDF/XML, a set of intraoral gallery photos
(front, upper occlusal, lower occlusal, left, right), and two STL mesh files
for the upper and lower dental arches.

Context: I'm a 38-year-old adult. A dentist is recommending a palatal expander,
claiming my upper jaw is about 10mm too narrow relative to my lower jaw
(he cited roughly 28mm vs 37mm from a CBCT). I want an independent sanity check
on whether my arches actually show a transverse (width) deficiency, since an
adult expander is a major intervention. I am NOT asking for a diagnosis.

Please do all of the following and show your work:

1. List the zip contents without assuming. Read the Rx (HTML/PDF/XML) and tell me
   the procedure type, ordering dentist, scan date, and whether there are any
   clinical notes or a documented treatment plan.

2. Open the upper-occlusal and front intraoral photos. Describe the arch form
   (broad/U-shaped vs narrow/V-shaped), and note any signs of a posterior
   crossbite, the front-tooth findings, and tooth-size discrepancies.

3. Load both STL files in Python. These are true-scale (mm) meshes. Confirm the
   anterior-posterior orientation, then measure buccal-to-buccal arch width for
   BOTH arches at matched front-to-back positions (canine, premolar, first molar,
   and widest point). Present a table of upper width, lower width, and the
   difference at each position. If possible, also estimate palatal vault depth;
   if the mesh lacks mid-palate data, say so.

4. Interpret: do the measured upper-vs-lower widths support a ~10mm maxillary
   transverse deficiency, or are the arches reasonably matched? Explain what the
   "28 vs 37mm" comparison likely measured and whether subtracting those two
   numbers is a valid way to diagnose a transverse deficiency.

5. State your limitations clearly: that width measured off a shell includes
   gingiva/bone (so absolute numbers run high, but upper-vs-lower comparison is
   valid), that a mesh cannot assess a posterior crossbite (a clinical/occlusal
   finding), and that you are not a dentist. End with the specific questions I
   should put back to the provider before agreeing to an expander.
```
