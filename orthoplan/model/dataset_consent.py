"""Publication scope records, distinct from private signed consent documents."""

from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from orthoplan.model.dataset import DatasetManifest


class DatasetConsent(BaseModel):
    model_config = {"extra": "forbid", "populate_by_name": True}

    schema_id: Literal["opensource-ortho-dataset-consent-v1"] = Field(
        default="opensource-ortho-dataset-consent-v1", alias="schema"
    )
    specimen_id: str
    consent_acknowledged: bool
    phi_removed: bool
    authorization_basis: str
    publication_scope: list[str]
    exact_dates_retained: bool = False
    date_retention_basis: str | None = None
    public_assets: list[str]
    third_party_reference_rights: Literal["unverified", "confirmed", "not-applicable"]
    rights_note: str

    @field_validator("public_assets")
    @classmethod
    def safe_relative_assets(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("Published asset paths must be unique")
        for value in values:
            path = PurePosixPath(value)
            if (not value or path.is_absolute() or "\\" in value or "%" in value
                    or "\x00" in value or str(path) != value
                    or any(p.startswith(".") for p in path.parts)):
                raise ValueError("Published assets must be explicit, non-hidden relative paths")
            if "records" in path.parts or path.suffix.lower() in {".dcm", ".dicom"}:
                raise ValueError("Raw local records are not public dataset assets")
        return values

    def matches_manifest(self, manifest: DatasetManifest) -> bool:
        return (self.specimen_id == manifest.specimen_id
                and self.consent_acknowledged and manifest.consent_acknowledged
                and self.phi_removed and manifest.phi_removed)


def read_consent(path: Path) -> DatasetConsent:
    return DatasetConsent.model_validate_json(path.read_text(encoding="utf-8"))
