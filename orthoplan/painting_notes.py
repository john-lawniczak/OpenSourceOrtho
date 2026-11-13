"""Small note summaries for locally saved sample paintings."""

from orthoplan.region_corrections import load_baseline_corrections


def painting_notes_payload() -> dict:
    entries, errors = [], []
    for visit, week in [("initial", 1), ("progress-01", 7), ("progress-02", 18)]:
        for arch in ("upper", "lower"):
            title = f"USER_ONE · Week {week} · {arch.title()}"
            record = load_baseline_corrections(arch, visit=visit)
            if not record.get("ok"):
                errors.append(f"{title}: could not read saved painting.")
            elif record.get("saved"):
                entries.append({
                    "title": title,
                    "notes": record.get("notes", ""),
                    "saved_at": record.get("saved_at", ""),
                    "review_status": record.get("review_status", "draft"),
                    "href": f"./region-review.html?baseline={arch}&visit={visit}",
                })
    return {"ok": not errors, "entries": entries, "errors": errors}
