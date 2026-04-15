"""
Pydantic schema validation for cleaned rows.

This is intentionally separate from business expectations: pydantic checks
the cleaned data contract shape/types, while expectations check policy rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from transform.cleaning_rules import ALLOWED_DOC_IDS


class CleanedRowModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    chunk_text: str = Field(min_length=8)
    effective_date: date
    exported_at: datetime

    @field_validator("doc_id")
    @classmethod
    def doc_id_must_be_allowed(cls, value: str) -> str:
        if value not in ALLOWED_DOC_IDS:
            raise ValueError(f"doc_id_not_allowed:{value}")
        return value


@dataclass
class SchemaValidationSummary:
    passed: bool
    rows_checked: int
    errors: List[Dict[str, Any]]

    @property
    def detail(self) -> str:
        if self.passed:
            return f"framework=pydantic rows={self.rows_checked} errors=0"
        return f"framework=pydantic rows={self.rows_checked} errors={len(self.errors)}"


def validate_cleaned_rows(rows: List[Dict[str, Any]]) -> Tuple[List[CleanedRowModel], SchemaValidationSummary]:
    validated: List[CleanedRowModel] = []
    errors: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        try:
            validated.append(CleanedRowModel.model_validate(row))
        except ValidationError as exc:
            for err in exc.errors():
                errors.append(
                    {
                        "row": idx,
                        "field": ".".join(str(part) for part in err.get("loc", ())),
                        "message": err.get("msg", ""),
                    }
                )

    summary = SchemaValidationSummary(
        passed=len(errors) == 0,
        rows_checked=len(rows),
        errors=errors,
    )
    return validated, summary
