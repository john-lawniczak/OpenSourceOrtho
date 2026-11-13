# Retainer preparation: first step

**Create Retainer** in the sidebar opens a separate preparation workspace and
preserves the existing sample or movement-plan screen underneath. It accepts a
current STL, an arch, declared units (including Unverified), and an optional scan
date. The user confirms that this is the current scan they want to review.

Prepare reference model validates bounded finite geometry, then displays it with
rotate, pan, view presets and zoom. **Download reference STL** returns the exact
source bytes; no tooth movements, coordinate transforms, scaling or shell offsets
are applied to that output. **Download preparation record** provides the source
and reference SHA-256, file metadata, scan date, declared units, an empty movement
list, zero stages, and `wearable_output: false`.

Changing inputs invalidates the previous result. A stale asynchronous load cannot
replace newer inputs. The draft stays in the current tab when returning to the
main app and reopening this workflow; it does not survive a page reload. Download
the model and record to keep them. This flow does not inherit sample stage rows,
AI movement goals, review approvals or manufacturing settings.

This is a reference for user review, not a wearable retainer. Fit review and
appropriate materials and processing remain necessary for wearable output; shell
design, manufacturing preparation, fit approval and wearable export are not
implemented in this first step.
