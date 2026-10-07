"""Documentation guard: the fidelity minimum-evidence rules of the Setup Discovery pre-registration must stay written down.
(The enforcing code does not exist yet; it is written after the design lock and must implement exactly these rules.)"""
import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "PREREGISTRATION_SETUPS.md"


def text() -> str:
    return re.sub(r"\s+", " ", DOC.read_text(encoding="utf-8"))


def test_precision_has_a_minimum_of_10_audited_trigger_cases():
    t = text()
    assert "precision ≥ 70 %**, evaluated **only if at least 10 recognizer trigger cases were audited**" in t
    assert ("If fewer than 10 trigger cases are available, the candidate is classified "
            "**insufficient evidence → NOT CODEABLE FAITHFULLY**") in t


def test_recall_keeps_its_minimum_and_thresholds_are_unchanged():
    t = text()
    assert "evaluated **only if |E_K| ≥ 10**" in t
    assert "Gate: **recall ≥ 50 %**" in t and "Gate: **precision ≥ 70 %**" in t
    assert "The 70 % / 50 % thresholds are unchanged." in t
