from __future__ import annotations

from pathlib import Path

from orthoplan.model.assets import ArchName

MAXILLARY_ARCH: ArchName = "maxillary"
MANDIBULAR_ARCH: ArchName = "mandibular"
ENGINE_ARCHES: tuple[ArchName, ArchName] = (MAXILLARY_ARCH, MANDIBULAR_ARCH)

_MAXILLARY_TOKENS = ("upper", "top", "maxilla", "maxillary", "maxill", "-u.", "_u.")
_MANDIBULAR_TOKENS = ("lower", "bottom", "mandible", "mandibular", "mandib", "-l.", "_l.")


def normalize_arch_label(value: object) -> ArchName | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in {"upper", "maxillary"}:
        return MAXILLARY_ARCH
    if lowered in {"lower", "mandibular"}:
        return MANDIBULAR_ARCH
    return None


def infer_arch_from_name(name: str | Path) -> ArchName | None:
    text = Path(name).name.lower()
    maxillary_match = any(token in text for token in _MAXILLARY_TOKENS)
    mandibular_match = any(token in text for token in _MANDIBULAR_TOKENS)
    if maxillary_match and mandibular_match:
        return None
    if maxillary_match:
        return MAXILLARY_ARCH
    if mandibular_match:
        return MANDIBULAR_ARCH
    return None


def arch_from_tooth_value(tooth_value: str) -> ArchName:
    if (
        not isinstance(tooth_value, str)
        or len(tooth_value) != 2
        or not tooth_value.isdigit()
        or tooth_value[0] not in "12345678"
        or tooth_value[1] not in "12345678"
    ):
        raise ValueError(f"Tooth value must be canonical FDI, got {tooth_value!r}")
    return MAXILLARY_ARCH if tooth_value[0] in {"1", "2", "5", "6"} else MANDIBULAR_ARCH
