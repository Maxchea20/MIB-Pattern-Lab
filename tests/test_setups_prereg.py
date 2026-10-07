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


def test_output_lint_rule_in_the_preregistration_matches_the_code_exactly():
    from src.setups import prompts
    t = text()
    m = re.search(r"Words \(whole-word, case-insensitive\): (.*?)\. Phrases: (.*?)\. The standalone word \"edge\" is \*\*not\*\* forbidden", t)
    assert m, "output-lint sentence not found in the pre-registration"
    words = tuple(x.strip() for x in m.group(1).split(","))
    phrases = tuple(x.strip() for x in m.group(2).split(","))
    assert set(words) == set(prompts.OUTPUT_FORBIDDEN_WORDS) and "edge" not in words
    assert set(phrases) == set(prompts.OUTPUT_FORBIDDEN_PHRASES)
    assert set(phrases) >= {"trading edge", "statistical edge", "predictive edge", "positive edge", "an edge", "has edge", "have edge"}
    assert "stop loss" in phrases and "take profit" in phrases


def test_standalone_edge_is_allowed_but_the_performance_phrases_are_rejected():
    from src.setups import prompts
    assert prompts.lint_output({"s": "price stalls at the right edge of the chart"}) == []
    for phrase in ("trading edge", "statistical edge", "predictive edge", "positive edge", "an edge", "has edge", "have edge"):
        assert prompts.lint_output({"s": f"this gives {phrase} here"}) == [phrase], phrase
