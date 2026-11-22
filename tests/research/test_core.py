import json
from datetime import UTC, datetime

import pytest

from src.company_research.core import (
    ResearchRequest,
    calculate,
    select_facts,
    validate_bundle,
)


def filing(accn, accepted, end="2023-12-31"):
    return {
        "accessionNumber": accn,
        "acceptanceDateTime": accepted,
        "form": "10-K",
        "reportDate": end,
    }


def test_future_restatement_is_not_visible():
    filings = [
        filing("old", "2024-02-01T12:00:00Z"),
        filing("new", "2025-02-01T12:00:00Z"),
    ]
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 100,
                                "accn": "old",
                            },
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 999,
                                "accn": "new",
                            },
                        ]
                    }
                }
            }
        }
    }
    found = select_facts(facts, filings, datetime(2024, 12, 31, tzinfo=UTC))
    assert [r["value"] for r in found] == [100]


def test_annual_instant_rejects_quarterly_period():
    facts = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {"USD": [{"end": "2023-09-30", "val": 100, "accn": "old"}]}
                }
            }
        }
    }
    assert not select_facts(
        facts,
        [filing("old", "2024-02-01T12:00:00Z")],
        datetime(2024, 12, 31, tzinfo=UTC),
    )


def test_math_and_missing():
    obs = [
        {"metric": m, "value": v, "end": p}
        for p, vals in [
            ("2022-12-31", {"revenue": 100}),
            (
                "2023-12-31",
                {
                    "revenue": 120,
                    "net_income": -12,
                    "operating_cashflow": 30,
                    "capex": 10,
                },
            ),
        ]
        for m, v in vals.items()
    ]
    rows = calculate(obs)
    assert rows[-1]["net_margin"] == -0.1
    assert rows[-1]["free_cashflow"] == 20
    assert rows[-1]["revenue_growth"] == pytest.approx(0.2)
    assert rows[0]["net_margin"] is None


def test_scope_and_corrupt_calculation():
    with pytest.raises(ValueError):
        ResearchRequest(cik="../1", as_of="2024-12-31")
    with pytest.raises(ValueError):
        ResearchRequest(cik="1", as_of="2099-01-01")
    result = validate_bundle(
        ResearchRequest(cik="1", as_of="2024-12-31"), [], [{"bad": 1}]
    )
    assert result["state"] == "invalid"


def test_report_bundle(tmp_path):
    from src.company_research.cli import build, write

    write(
        tmp_path / "request.json",
        {"cik": "0000320193", "as_of": "2024-12-31", "focus": ""},
    )
    write(tmp_path / "sources.json", [])
    write(tmp_path / "observations.json", [])
    result = build(tmp_path)
    assert result["state"] == "blocked"
    assert (tmp_path / "research.xlsx").is_file()
    assert "资料缺口" in (tmp_path / "report.html").read_text()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "calculate.py" in manifest


def test_optional_focus_normalizes_null():
    assert ResearchRequest(cik="320193", as_of="2024-12-31", focus=None).focus == ""


def test_workbook_summary_and_company_title(tmp_path):
    from openpyxl import load_workbook

    from src.company_research.cli import build, write

    write(tmp_path / "request.json", {"cik": "320193", "as_of": "2024-12-31"})
    write(tmp_path / "snapshot.json", {"company": "Apple Inc."})
    write(tmp_path / "sources.json", [{"id": "s", "url": "https://www.sec.gov/", "acceptanceDateTime": "2024-11-01T12:00:00Z"}])
    write(
        tmp_path / "observations.json",
        [
            {
                "metric": m,
                "value": v,
                "end": "2024-09-28",
                "source_id": "s",
                "accession": "s",
                "unit": "USD",
                "published_at": "2024-11-01T12:00:00Z",
            }
            for m, v in {
                "revenue": 100,
                "net_income": 20,
                "assets": 90,
                "liabilities": 60,
                "equity": 30,
                "operating_cashflow": 25,
                "capex": 5,
            }.items()
        ],
    )
    build(tmp_path)
    wb = load_workbook(tmp_path / "research.xlsx")
    overview = {r[0].value: r[1].value for r in wb["Overview"]}
    assert overview["Revenue (USD)"] == "=Financials!B2"
    assert overview["Net margin"] == "=Metrics!C2"
    checks = wb["Checks"]
    assert checks.cell(checks.max_row, 1).value == "Overall"
    assert "COUNTIF(" in checks.cell(checks.max_row, 3).value
    assert '"MISSING"' in checks.cell(checks.max_row, 3).value
    assert "Apple Inc." in (tmp_path / "report.html").read_text()
    assert all(s.page_setup.fitToWidth == 1 for s in wb)


def test_quarter_does_not_accept_cumulative_cashflows():
    filings = [
        {
            "accessionNumber": "q",
            "acceptanceDateTime": "2024-08-01T12:00:00Z",
            "form": "10-Q",
            "reportDate": "2024-06-30",
        }
    ]
    facts = {
        "facts": {
            "us-gaap": {
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-06-30",
                                "val": 200,
                                "accn": "q",
                            }
                        ]
                    }
                }
            }
        }
    }
    assert (
        select_facts(facts, filings, datetime(2024, 12, 31, tzinfo=UTC), annual=False)
        == []
    )


def test_cutoff_uses_acceptance_not_report_period():
    filings = [filing("a", "2024-02-01T12:00:00Z")]
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 100,
                                "accn": "a",
                            }
                        ]
                    }
                }
            }
        }
    }
    assert not select_facts(facts, filings, datetime(2024, 1, 31, tzinfo=UTC))


def test_conflict_prefers_latest_eligible_accession():
    filings = [filing("a", "2024-02-01T12:00:00Z"), filing("b", "2024-03-01T12:00:00Z")]
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 100,
                                "accn": "a",
                            },
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 110,
                                "accn": "b",
                            },
                        ]
                    }
                }
            }
        }
    }
    result = select_facts(facts, filings, datetime(2024, 12, 31, tzinfo=UTC))
    assert result[0]["value"] == 110
    assert result[0]["accession"] == "b"


def test_nonfinite_values_are_not_observations():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": float("nan"),
                                "accn": "a",
                            }
                        ]
                    }
                }
            }
        }
    }
    assert not select_facts(
        facts,
        [filing("a", "2024-02-01T12:00:00Z")],
        datetime(2024, 12, 31, tzinfo=UTC),
    )


def test_negative_capex_is_not_silently_reversed():
    obs = [
        {"metric": m, "value": v, "end": "2023-12-31"}
        for m, v in [("operating_cashflow", 100), ("capex", -20)]
    ]
    assert calculate(obs)[0]["free_cashflow"] is None


def test_source_after_frozen_cutoff_is_invalid():
    spec = ResearchRequest(
        cik="1", as_of="2024-12-31", cutoff_at="2024-10-01T00:00:00Z"
    )
    obs = [
        {
            "metric": "revenue",
            "value": 100,
            "end": "2023-12-31",
            "unit": "USD",
            "published_at": "2024-10-02T00:00:00Z",
            "source_id": "late",
        }
    ]
    assert "future_source:late" in validate_bundle(spec, obs, calculate(obs))["errors"]


def test_balance_sheet_mismatch_is_reported():
    obs = [
        {
            "metric": m,
            "value": v,
            "end": "2023-12-31",
            "unit": "USD",
            "published_at": "2024-01-01T00:00:00Z",
            "source_id": m,
        }
        for m, v in [("assets", 100), ("liabilities", 80), ("equity", 40)]
    ]
    assert (
        validate_bundle(
            ResearchRequest(cik="1", as_of="2024-12-31"), obs, calculate(obs)
        )["state"]
        == "invalid"
    )


def test_analysis_cannot_reference_unknown_source(tmp_path):
    from src.company_research.cli import build, write

    write(tmp_path / "request.json", {"cik": "0000320193", "as_of": "2024-12-31"})
    write(tmp_path / "sources.json", [])
    write(tmp_path / "observations.json", [])
    write(
        tmp_path / "analysis.json",
        {"business": [{"text": "Unsupported", "sources": ["missing"]}]},
    )
    with pytest.raises(ValueError, match="missing evidence"):
        build(tmp_path)


def test_naive_cutoff_is_rejected():
    with pytest.raises(ValueError, match="timezone"):
        ResearchRequest(cik="1", as_of="2024-12-31", cutoff_at="2024-01-01T12:00:00")


def test_cached_snapshot_keeps_its_original_cutoff(tmp_path):
    from src.company_research.cli import collect, write

    spec = ResearchRequest(
        cik="1", as_of="2024-12-31", cutoff_at="2024-12-01T00:00:00Z"
    )
    write(tmp_path / "request.json", spec.model_dump(mode="json"))
    (tmp_path / "raw").mkdir()
    for name in (
        "sources.json",
        "observations.json",
        "snapshot.json",
        "raw/companyfacts.json",
        "raw/submissions.json",
    ):
        write(tmp_path / name, {})
    collect(ResearchRequest(cik="1", as_of="2024-12-31"), tmp_path, "")
    assert (
        json.loads((tmp_path / "request.json").read_text())["cutoff_at"]
        == "2024-12-01T00:00:00Z"
    )
    with pytest.raises(ValueError, match="another request"):
        collect(ResearchRequest(cik="2", as_of="2024-12-31"), tmp_path, "")


def test_narrative_render_preserves_reviewed_workbook(tmp_path):
    from src.company_research.cli import build, write

    write(tmp_path / "request.json", {"cik": "0000320193", "as_of": "2024-12-31"})
    write(tmp_path / "sources.json", [])
    write(tmp_path / "observations.json", [])
    build(tmp_path)
    reviewed = (tmp_path / "research.xlsx").read_bytes()
    build(tmp_path, preserve_workbook=True)
    assert (tmp_path / "research.xlsx").read_bytes() == reviewed


def test_scope_timezones_compare_by_instant():
    a = ResearchRequest(
        cik="320193", as_of="2024-12-31", cutoff_at="2024-12-31T23:59:59.999999-05:00"
    )
    b = ResearchRequest(
        cik="320193", as_of="2024-12-31", cutoff_at="2025-01-01T04:59:59.999999Z"
    )
    wrong = ResearchRequest(
        cik="320193", as_of="2024-12-31", cutoff_at="2024-12-31T23:59:59Z"
    )
    assert a == b
    assert a != wrong


def test_server_scope_file_overrides_model_timezone(tmp_path):
    from src.company_research.cli import collect, write

    canonical = ResearchRequest(
        cik="320193", as_of="2024-12-31", cutoff_at="2024-12-31T23:59:59.999999-05:00"
    )
    write(tmp_path / "scope.json", canonical.model_dump(mode="json"))
    write(tmp_path / "request.json", canonical.model_dump(mode="json"))
    (tmp_path / "raw").mkdir()
    for name in (
        "sources.json",
        "observations.json",
        "snapshot.json",
        "raw/companyfacts.json",
        "raw/submissions.json",
    ):
        write(tmp_path / name, {})
    collect(
        ResearchRequest(
            cik="320193", as_of="2024-12-31", cutoff_at="2024-12-31T23:59:59Z"
        ),
        tmp_path,
        "",
    )
    assert (
        ResearchRequest(**json.loads((tmp_path / "request.json").read_text()))
        == canonical
    )
