# Getting 3D scans of your own teeth

**Already have a 3D scan? Upload your STL files in OpenSource Ortho's Upload
step.** If you run the app locally, [open OpenSource Ortho](http://127.0.0.1:8000).
If it is not running yet, follow the [setup instructions](HOW_TO.md#1-start-the-app).

The goal is to give the software an accurate starting model of your teeth.
From there, you can review individual teeth, define proposed corrected
positions, preview movement in stages, and export staged model files. Better
input data makes those models and comparisons more useful. The resulting
positions and files still need professional review before treatment or appliance use.

## Have scans? Start here

1. **Upload separate upper and lower STL files**, ideally from the same visit.
   You can start with one arch and add the other when available.
2. **Confirm millimeters and upper/lower labels.** Keep the original files and
   their recorded bite alignment; do not resize or independently reposition them.
3. **Check the 3D preview for missing or distorted teeth.** Review the individual
   tooth segmentation before using it to define proposed corrected positions.
4. **Continue through Review → 3D preview → Print / send** to inspect the
   proposed setup and export model files. Check the reported data gaps and
   whether the output uses actual tooth meshes or schematic proxy geometry.

Photos, viewer links, and PDFs are useful supporting records, but the tooth
mesh upload requires STL files. Preserve other original formats and ask for an
STL export if necessary.

## Need scans? Try the cheaper options first

1. **Ask your dentist or orthodontist for scans they already have.** Request
   downloadable upper and lower STL files; use the request template below.
2. **Get a quote for one scan session or digitizing an existing dental cast.**
   Compare that total with buying equipment, materials, and repeat captures.
3. **If you need frequent captures, compare borrowed scanners and cast scanning
   with owning equipment.** Test a sample file before committing to a pipeline.
4. **Use phone photos for visual records while arranging usable mesh data.**
   A phone-generated 3D model needs dimensional validation before measurements.

For a budget under $100, investigate the first two options before buying a
scanner. The table below covers the alternatives and what each can contribute.

**Source check: September 10, 2026.** Costs below are USD budgeting assumptions,
not verified shopping quotes, except where explicitly identified. Taxes,
shipping, professional fees, and replacement equipment are extra. Product links
are non-affiliate starting points; confirm availability, export access, and
total cost locally before buying. Software cost and data-acquisition cost are
separate, so budget for both.

## Choose by the data you need

- **A visual diary:** consistent ordinary photographs can document appearance.
  Keep original photos; a reconstructed 3D model is optional and experimental.
- **A starting model for proposed corrected positions:** request full-arch intraoral scans, or explore
  a professionally made cast digitized by a dental laboratory. Compare a sample
  export before committing to a recurring service or equipment purchase.
- **Changes over time:** prioritize comparable records and measured repeatability
  over sheer capture frequency. Use existing initial, progress/refinement, and
  final scans before funding a scan at every stage.
- **Root/bone questions:** surface scans do not supply this anatomy. Request
  existing appropriate records through your clinician. Do not obtain CBCT just
  to fill an app's data gaps; FDA guidance limits dental X-rays, including CBCT,
  to clinically necessary examinations. See [FDA guidance](https://www.fda.gov/radiation-emitting-products/medical-x-ray-imaging/dental-cone-beam-computed-tomography)
  and [the repo's CBCT boundaries](docs/cbct-evaluation.md).

## Options and costs

Compare initial expense, repeat costs, and the kind of data you get. Prices
overlap, especially for quoted services. Accuracy depends on the entire capture
process, so the table describes useful data and limits instead of assigning
unsupported scores out of ten.

| Route | Initial budget or quote basis | Recurring expense | Useful data and principal limit |
|---|---|---|---|
| **Request existing intraoral scans** | Ask whether export is included; otherwise request a records/export quote | None for the same files | First choice to investigate. Historical scans represent their capture date, not your teeth today. |
| **1. Phone photos / photogrammetry** | Illustrative $0–40 with an owned phone; app/export charges may be extra | Subscription if required | Visual context and experimental surfaces. Wet reflective teeth, motion, hidden surfaces, and uncertain scale prevent assuming dimensional accuracy. |
| **Digitize an existing dental cast** | Lab/makerspace quote; no new impression if a suitable cast exists | Per cast or scanning session | Avoids buying a scanner. Cast age, damage, original impression quality, and scanner capability still matter. |
| **2. Alginate impression → dental stone → borrowed/paid scan** | Illustrative $50–100 for supplies/access if scanning is inexpensive; professional capture extra | Material, failed captures, scanning, shipping | Potential study-model data. Material-specific storage, impression defects, stone expansion, and scan errors all affect the result. |
| **3. PVS impression → dental stone → borrowed/paid scan** | Illustrative $80–150 for supplies/access; professional capture extra | Same categories as alginate | A dimensionally stable impression material can help, but does not validate the cast or scanner. Borrowing a good scanner is not inherently less accurate than owning one. |
| **4. POP 3 + PVS/stone casts** | Current used/remaining-stock quote + supplies; do not assume a new $300 scanner is available | Every new impression/cast; maintenance and operator time | Experimental bench scanning. Revopoint lists the original POP 3 as sold out; ownership improves access, not demonstrated accuracy. [Availability](https://support.revopoint3d.com/hc/en-us/articles/7854887411739-How-much-do-the-POP-scanner-series-cost) |
| **5. Scan an aligner tray, or a cast made from one** *(add-on)* | Scanner/access cost + quoted coating or casting supplies; a $15–30 allowance is unverified | Per discarded research tray/cast | Appliance geometry only. It is neither an actual tooth scan nor the original digital target setup. See the tray limits below. |
| **6. POP 3 Plus or MINI 2 + PVS/stone casts** | Obtain a current scanner bundle quote, then add supplies and validation; do not assume $850–1,000 covers a whole series | Impressions/casts, failures, maintenance | Candidate bench tools to test on casts. Manufacturer single-frame specifications are not full-arch dental validation. [POP 3 Plus](https://www.revopoint3d.com/products/portable-3d-scanner-pop3), [MINI 2](https://global.revopoint3d.com/products/industry-3d-scanner-mini?variant=43464479834347) |
| **7. Home cast pipeline + occasional professional comparison scans** | Route 4/6 total + individually quoted visits/exports | Home captures plus selected visits | More informative validation design if records are contemporaneous. Two or three comparisons are a study choice, not proof that intermediate scans are accurate. |
| **8. Own a used iTero** | Seller-specific, potentially many thousands. Renew Digital advertised **$9,995** on its homepage at source check; this is one offer, not a market range | Transfer/activation, service, compatible computer, consumables, training; subscription depends on contract | Professional equipment still requires an appropriate operator and usable software/export access. Cheap listings alone do not establish functionality. [Seller](https://www.renewdigital.com/) |
| **9. Professional intraoral scans at every selected stage** *(variable price)* | Written quote for both arches, bite, and downloadable files; may be bundled with existing care | Per visit × number of visits, plus travel/time | Direct surface capture avoids impression/cast errors, but is not error-free or automatically superior in every case. Frequent visits may be impractical; every-tray capture is not required by this repo. |

Ask dental schools, cooperating practices, and laboratories about scan-only or
cast-digitization services; availability and whether a patient can commission a
lab directly vary. iTero is one option, not a repo requirement: ask any provider
whether its system can supply the files below.

### Where to buy materials and scanners

These links are shopping starting points, with no affiliate tags. Amazon links
open searches so you can compare sellers and pack sizes; individual listings,
stock, and prices have not been verified. Manufacturer links identify the
product or provide a direct store. Match impression materials to your dental
professional's requirements and check expiry dates and included quantities.

| Item | Shopping links | What to check |
|---|---|---|
| **Alginate dental impression material** | [Amazon: dental alginate](https://www.amazon.com/s?k=dental+alginate+impression+material) · [Zhermack Hydrogum 5](https://www.zhermack.com/en/product/hydrogum-5/) | Dental impression material, pack quantity, storage and pouring instructions; avoid confusing it with craft/lifecasting alginate. |
| **PVS dental impression material** | [Amazon: dental PVS impression material](https://www.amazon.com/s?k=dental+PVS+impression+material) · [Zhermack Elite HD+](https://www.zhermack.com/en/product/elite-hd-tray-material/) | Confirm the required material consistency and whether trays, dispenser, and mixing tips are included or sold separately. |
| **Dental impression trays** | [Amazon: upper and lower dental impression trays](https://www.amazon.com/s?k=upper+lower+dental+impression+trays) | Have your dental professional select the appropriate size and material-compatible tray. |
| **Dental model stone** | [Amazon: Type III dental stone](https://www.amazon.com/s?k=type+III+dental+stone) · [Whip Mix model stones and supplier options](https://whipmix.com/our-products/gypsum/) | Dental model stone with published mixing and expansion specifications; check bag weight and shipping cost. |
| **Cast-making accessories** | [Amazon: dental mixing bowl and spatula](https://www.amazon.com/s?k=dental+mixing+bowl+spatula) · [Amazon: digital gram scale](https://www.amazon.com/s?k=digital+gram+scale) | Buy only what your cast-making setup needs; follow the stone manufacturer's measuring requirements. |
| **POP 3 / POP 3 Plus scanner** | [Buy POP 3 Plus from Revopoint](https://www.revopoint3d.com/products/portable-3d-scanner-pop3) · [Amazon: Revopoint POP 3](https://www.amazon.com/s?k=Revopoint+POP+3) | The official linked store page sells **POP 3 Plus**. Check the exact model, seller, bundle, and warranty when comparing original POP 3 listings. |
| **MINI 2 scanner** | [Buy MINI 2 from Revopoint](https://global.revopoint3d.com/products/industry-3d-scanner-mini?variant=43464479834347) | Confirm regional availability, computer compatibility, and included turntable/calibration accessories. |
| **Scanning spray for bench specimens** *(optional)* | [Amazon: AESUB blue](https://www.amazon.com/s?k=AESUB+blue+scanning+spray) · [AESUB product and safety information](https://aesub.com/prod/aesub-blue-2/) | Only for bench objects that will not return to the mouth; see the tray limits below. An opaque stone cast may not need spray. |

For a first cast-scanning session, price the impression material, required trays
and accessories, dental stone, and borrowed or paid scanning together. Buy a
scanner only after checking that a sample cast produces usable STL data.

### Budget a series, not just a scanner

Use this worksheet with actual quotes:

```text
total = equipment + setup/accessories
      + capture_count × (both-arch materials + capture/lab/export fee + shipping)
      + validation visits + replacement/failed-capture allowance + subscriptions
```

For illustration only, $600 equipment + 13 captures at $40 per upper/lower pair
is **$1,120**, before validation, fees, and failures. At 38 captures it is
**$2,120**. A 38-week observation period does not specify the capture count, and
one “kit” does not necessarily cover both arches. Compare this with quoted
service costs before deciding that ownership is cheaper. Capture timing should
match the comparisons you need and your existing care schedule.

## What to request from an office or lab

Copy and adapt this request:

> I would like copies of my existing 3D dental surface records for personal
> use in OpenSource Ortho. Can you provide separate upper and lower full-arch STL
> files, with units confirmed in millimeters, and preserve their recorded bite
> alignment? Please include the bite scan or registration information if
> available, capture date, scanner model, and any known missing areas or edits.
> If available, I would also like the original color PLY/OBJ files and earlier
> progress scans. Please distinguish actual scans from simulated target setups.
> Before I book or pay, please confirm export availability, the total fee, and
> whether the files are downloadable meshes rather than a viewer link or PDF.

For iTero, ask staff to confirm the workflow for their software and account.
Do not insist that “iCast/non-Invisalign mode” is universally required or that
every existing case can be exported. A published [3M iTero export guide](https://multimedia.3m.com/mws/media/2319172O/attaching-a-digital-impression-for-3m-oral-care-portal-from-the-itero-intraoral-scanner.pdf)
shows STL export with separate arches in their bite relationship. This supports
asking for that output; it does not guarantee access under every current plan.

Before purchasing a used unit, obtain written confirmation from the manufacturer
and seller for the specific serial number, region, intended operator/account,
transfer eligibility, activation/service charges, supported software/computer,
and mesh export. Ask for a live capture-to-export demonstration and return
terms. [Align's EMEA transfer policy](https://assets.ctfassets.net/hq0f2w4ejqlf/l4dlsB01xtPbJRaWpTtI9/567bd7d03c13cd06ab20c3f97168f872/English_-_EMEA_iTero_Transfer_Policy.pdf)
describes transfer obligations and possible activation charges; confirm the
applicable regional policy rather than treating this as a universal contract.

## Material, scanner, and tray limits

**Phone capture:** consumer photogrammetry apps, phone depth/LiDAR capture,
Gaussian splats, and specialized dental monitoring systems are different
technologies. A viewable 3D scene is not necessarily an exportable measurement
mesh. A [2024 full-arch smartphone study](https://pubmed.ncbi.nlm.nih.gov/39077296/)
evaluates specific applications and setups in vitro; it is not validation of
arbitrary handheld scans inside a mouth. Check [Polycam's current plans](https://poly.cam/pricing)
and [Scaniverse's current destination](https://www.nianticspatial.com/products/capture)
for device support, actual mesh export, processing location, and charges. Do not
assume free capture includes STL export or that a photo-derived mesh has scale.

**Impressions and stone:** arrange impressions with a dental professional,
especially with attachments, braces, loose teeth, or restorations. This is a
data-acquisition comparison, not an instruction for self-impression taking.
Follow the exact material's instructions for use, storage, disinfection, and
pouring. Alginate does not have a universal 10–15 minute expiry: for example,
[Hydrogum 5](https://www.zhermack.com/en/product/hydrogum-5/) advertises five-day
dimensional stability under its specified conditions. That claim cannot be
generalized to every alginate or to a completed home scan. [PVS/addition silicone](https://www.zhermack.com/en/product/elite-hd-tray-material/)
also has product-specific handling requirements. [Dental model stones](https://whipmix.com/our-products/gypsum/)
have specified properties; material selection and processing belong in the record.
Errors arise at each step, but do not automatically accumulate from one time
point to the next when each capture is independently made.

**Consumer scanners:** use these for bench objects/casts, not as improvised
intraoral scanners. POP 3 Plus advertises up to **0.08 mm single-frame accuracy**;
MINI 2 advertises **0.02 mm single-frame precision** and separately **0.05 mm
single-frame accuracy**. Those quantities are not interchangeable, and neither
establishes accuracy after impression, casting, stitching, and processing.
See the [POP specification](https://www.revopoint3d.com/products/portable-3d-scanner-pop3),
[MINI precision specification](https://www.revopoint3d.com/pages/industry-3d-scanner-mini2),
and [MINI accuracy description](https://www.revopoint3d.com/blogs/news/introducing-the-revopoint-mini-2-3d-scanner-capture-every-tiny-detail?msged=1).

**Tray scans:** distinguish the tray's outside surface, inside surface, and a
cast poured into it. None directly recovers the manufacturer's target tooth
positions: thickness, forming, clearance, attachments, wear, deformation, and
casting introduce differences. Label tray-derived geometry as an appliance
proxy. It may support appliance research, but is not automatically a reliable
planned-versus-actual training pair; request a legitimately available digital
target setup and matching actual scan for that purpose.

Industrial scanning spray such as [AESUB blue](https://aesub.com/prod/aesub-blue-2/)
is for bench scanning; its product page links the safety data sheet. Do not spray
it into the mouth or onto an appliance that will return to the mouth. Restrict
coating/casting experiments to discarded research specimens that will not be
worn again. Coating thickness and cast removal can also alter measured geometry.

## Check the data before collecting more

Use these checks to decide whether your files support the measurements and
model comparisons you want to make.

1. **Keep the source.** Preserve untouched exports and make edits on copies.
   Record arch, capture time, method, operator, scanner/software version, and
   export settings. Label actual scan, cast scan, tray proxy, and simulated setup
   separately. Keep original source hashes with the private record.
2. **Verify coverage.** Inspect chewing, cheek-facing, and tongue-facing surfaces,
   last molars, gum margins, holes, doubled surfaces, and missing areas. A smooth
   or watertight mesh can contain invented hole fills. Do not fill missing tooth
   anatomy and relabel it as measured data.
3. **Verify scale and bite.** STL does not encode a reliable unit declaration.
   Obtain units from the exporter and an independent dimensional check on a
   bench reference/cast where appropriate. Do not resize to an average tooth
   width. Keep both arches in their shared coordinate frame; independently
   centering them loses the recorded bite. Missing bite evidence stays missing.
4. **Measure repeatability.** For a bench experiment, acquire at least three
   independent scans of the same unchanged cast, repositioning between scans.
   Compare agreed landmarks and local surface deviations. This tests scanning
   repeatability only; it does not measure impression/casting error or trueness.
5. **Compare against a reference.** Where feasible, compare contemporaneous
   professional and cast records, documenting time separation and the reference's
   uncertainty. Use rigid alignment with a declared reference region; record
   deviations by tooth/region as well as a global statistic. Whole-arch best fit
   can hide local errors or true movement. Do not deform or rescale meshes to
   force agreement. Periodic comparisons are validation evidence, not automatic
   “calibration” of every intervening record.
6. **Set an uncertainty rule.** State the intended measurement and its error
   budget before analysis. Changes comparable to capture/registration error are
   inconclusive. Keep rejected captures and reasons; repeat acquisition rather
   than letting an LLM infer missing geometry. This repo provides no universal
   dental accuracy threshold for these home pipelines.

## Use the records in OpenSource Ortho

The current surface intake path uses **STL**. Preserve PLY/OBJ originals if
provided; requesting them does not imply the app imports them. Record any
conversion separately and confirm that it preserved scale and geometry.

After [installation](HOW_TO.md), an optional local inspection is:

```bash
orthoplan inspect-stl /path/to/initial-upper.stl
```

Inspection reports mesh metadata with units unverified; it does not certify
accuracy. Upload your arches through the guided workflow, confirm units and
arch labels, and inspect the Review workspace's **What can I trust here?**
report. [Intake readiness](docs/INTAKE_READINESS.md) distinguishes recorded
metadata from independently verified evidence; declared bite availability does
not establish a persisted bite registration. Review proposed tooth segmentation
explicitly. Missing roots, bone, periodontal context, and bite remain data gaps.

For repeated records, follow the [contribution filenames and specimen IDs](docs/DATA_CONTRIBUTION.md)
even if the data stays private. Keep a private acquisition log with capture dates,
material/batch and processing times for casts, scan settings, edits, costs,
uncertainty observations, and rejected captures. This log is a companion record,
not a new app manifest schema. For public contributions, use relative time points
and redact identifying metadata. Dental geometry can remain identifying even
after names are removed. Do not commit personal scans to the public repository;
check cloud processing, retention, and consent before uploading to an app or LLM.

## Context to give your LLM

Copy this alongside your actual acquisition log:

> Read GETTING_YOUR_TEETH_SCANNED.md and docs/INTAKE_READINESS.md first.
> Help me identify the least expensive way to acquire the data needed for my
> intended model or comparison in OpenSource Ortho. Ask what records I already have, my budget/location,
> export availability, and whether I need visual context or measurements.
> Distinguish measured intraoral surfaces, cast-derived surfaces, tray proxies,
> simulated setups, and inferred geometry. Do not assign unsupported accuracy
> scores, turn scanner marketing specifications into full-pipeline accuracy,
> or infer millimeter scale, bite, roots, or bone from appearance. Report unknowns
> and capture/registration uncertainty. More files do not necessarily mean
> better evidence. Recommend contemporaneous reference comparisons when useful,
> not routine every-stage scans or CBCT solely for this app. Do not diagnose,
> prescribe tooth movement, or treat scan quality as physical-use authorization.

This text is user/assistant guidance; it does not change runtime provider
behavior. Model-generated findings displayed or exported by the application
must still pass `lint_finding()`.
