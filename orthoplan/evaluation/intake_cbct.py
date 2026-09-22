"""Optional CBCT dependencies, resolved per registration and anatomy object."""
from orthoplan.model.plan import CBCT_RECORD_KINDS, TreatmentPlan
from orthoplan.model.readiness import ReadinessItem
from orthoplan.model.registration_gate import gate_registrations


def cbct_records(plan: TreatmentPlan) -> list[ReadinessItem]:
    records = [record for record in plan.case_records if record.kind in CBCT_RECORD_KINDS]
    items = [ReadinessItem(
        id=f"cbct:{record.id}", label=f"CBCT/DICOM {record.id}", scope="root_bone",
        state="present", detail="Record metadata attached; volume bytes and anatomy are not verified here.",
        action="attach_cbct",
    ) for record in records]
    if not records:
        items.append(ReadinessItem(
            id="cbct", label="CBCT/DICOM", scope="root_bone", state="missing",
            detail="No CBCT/DICOM record attached. Availability flags alone are not record evidence.",
            action="attach_cbct",
        ))
    gates = gate_registrations(plan)
    for gate in gates:
        items.append(ReadinessItem(
            id=f"registration:{gate.registration_id}", label=f"Registration {gate.registration_id}",
            scope="root_bone", state=("present" if gate.verdict.value == "PASS" else
                                      "needs_review" if gate.open else "blocked"),
            detail=f"{gate.verdict.value}: {'; '.join(gate.reasons)}",
            action="review_registration",
        ))
    if not gates:
        items.append(ReadinessItem(
            id="registration", label="STL-to-CBCT registration", scope="root_bone",
            state="missing", detail="No registration with recorded quality metrics is available.",
            action="review_registration",
        ))
    open_ids = {gate.registration_id for gate in gates if gate.open}
    anatomy = plan.derived_anatomy
    for key, label in (("roots", "Root geometry"), ("tooth_axes", "Tooth axes"),
                       ("alveolar_bone", "Alveolar bone")):
        objects = getattr(anatomy, key, []) if anatomy else []
        usable = sum(obj.trusted and obj.registration_id in open_ids for obj in objects)
        items.append(ReadinessItem(
            id=f"anatomy:{key}", label=label, scope="root_bone",
            state="missing" if not objects else "present" if usable == len(objects) else "blocked",
            detail=(f"{usable} of {len(objects)} object(s) reviewed, in field, and linked to an open "
                    "registration gate. This does not establish full anatomical coverage."),
            action="review_anatomy",
        ))
    return items
