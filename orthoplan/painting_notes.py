"""Small note summaries for locally saved sample paintings."""

from orthoplan.region_corrections import load_baseline_corrections


def painting_notes_payload() -> dict:
    entries, errors = [], []
    sources = [(visit, week, arch, "original")
               for visit, week in [("initial", 1), ("progress-01", 7), ("progress-02", 18)]
               for arch in ("upper", "lower")]
    sources += [("progress-02", 18, "lower", capture) for capture in ("fusion-h-4", "fusion-h-6")]
    sources += [("progress-02", 18, "upper", "upper-clean")]
    for visit, week, arch, capture in sources:
        title = f"USER_ONE · Week {week} · {arch.title()}"
        suffix = "" if capture == "original" else " · Cleaned version" if capture == "upper-clean" else f" · {capture.upper()}"
        title += suffix
        record = load_baseline_corrections(arch, visit=visit, capture=capture)
        if not record.get("ok"):
            errors.append(f"{title}: could not read saved painting.")
        elif record.get("saved"):
            entries.append({
                "title": title,
                "notes": record.get("notes", ""),
                "saved_at": record.get("saved_at", ""),
                "review_status": record.get("review_status", "draft"),
                "href": f"./region-review.html?baseline={arch}&visit={visit}" + (f"&capture={capture}" if suffix else ""),
            })
    return {"ok": not errors, "entries": entries, "errors": errors}
