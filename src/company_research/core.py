"""Pure research contracts, SEC fact selection and report validation."""

import hashlib
import json
import math
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    cik: str
    as_of: date
    cutoff_at: datetime | None = None
    focus: str = Field(default="", max_length=2000)

    @field_validator("focus", mode="before")
    @classmethod
    def normalize_focus(cls, value):
        return "" if value is None else value

    @field_validator("cik")
    @classmethod
    def validate_cik(cls, value):
        if not value.isascii() or not value.isdigit() or not 1 <= len(value) <= 10:
            raise ValueError("CIK must contain 1–10 ASCII digits")
        return value.zfill(10)

    @field_validator("cutoff_at")
    @classmethod
    def validate_cutoff(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("cutoff_at requires a timezone")
        return value

    @field_validator("as_of")
    @classmethod
    def validate_date(cls, value):
        if value > datetime.now(ZoneInfo("America/New_York")).date():
            raise ValueError("Future research dates are not supported")
        return value


def cutoff(spec):
    end = datetime.combine(spec.as_of, time.max, ZoneInfo("America/New_York"))
    captured = spec.cutoff_at or datetime.now(UTC)
    if captured.tzinfo is None:
        raise ValueError("cutoff_at requires a timezone")
    return min(end, captured)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


TAGS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net_income": ["NetIncomeLoss"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity"],
    "operating_cashflow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
}


def select_facts(companyfacts, filings, end, *, annual=True):
    """Select only facts tied to eligible accessions, never latest frame values."""
    eligible = {}
    for filing in filings:
        accepted = filing.get("acceptanceDateTime")
        if not accepted:
            continue
        stamp = datetime.fromisoformat(accepted)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=ZoneInfo("America/New_York"))
        if stamp <= end and filing.get("form") in ("10-K", "10-K/A", "10-Q", "10-Q/A"):
            eligible[filing["accessionNumber"]] = filing
    result = []
    for metric, tags in TAGS.items():
        candidates = {}
        for rank, tag in enumerate(tags):
            records = (
                companyfacts.get("facts", {})
                .get("us-gaap", {})
                .get(tag, {})
                .get("units", {})
                .get("USD", [])
            )
            for fact in records:
                filing = eligible.get(fact.get("accn"))
                if not filing or fact.get("end", "") > end.date().isoformat():
                    continue
                value = fact.get("val")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    continue
                # Duration facts must be annual; instant facts must come from an annual filing.
                if filing["form"] not in (
                    ("10-K", "10-K/A") if annual else ("10-Q", "10-Q/A")
                ):
                    continue
                if metric in ("assets", "liabilities", "equity"):
                    if fact.get("start"):
                        continue
                    # Do not mix quarterly instants into annual comparison columns.
                    if fact["end"] != filing.get("reportDate"):
                        continue
                else:
                    if not fact.get("start"):
                        continue
                    days = (
                        date.fromisoformat(fact["end"])
                        - date.fromisoformat(fact["start"])
                    ).days
                    if not ((330 <= days <= 380) if annual else (60 <= days <= 120)):
                        continue
                key = (fact.get("start"), fact["end"])
                order = (filing["acceptanceDateTime"], -rank)
                if key not in candidates or order > candidates[key][0]:
                    candidates[key] = (
                        order,
                        {
                            "metric": metric,
                            "value": value,
                            "unit": "USD",
                            "start": fact.get("start"),
                            "end": fact["end"],
                            "tag": tag,
                            "accession": fact["accn"],
                            "published_at": filing["acceptanceDateTime"],
                            "source_id": fact["accn"] + ":" + tag + ":" + fact["end"],
                        },
                    )
        result.extend(item[1] for item in candidates.values())
    return sorted(result, key=lambda r: (r["end"], r["metric"]))


def calculate(observations):
    periods = sorted({r["end"] for r in observations})[-4:]
    rows = []
    previous = None
    for period in periods:
        values = {r["metric"]: r["value"] for r in observations if r["end"] == period}
        row = {"period": period, **values}
        revenue = values.get("revenue")
        income = values.get("net_income")
        assets, liabilities = values.get("assets"), values.get("liabilities")
        row["debt_ratio"] = (
            liabilities / assets if assets and liabilities is not None else None
        )
        row["cash_conversion"] = (
            values["operating_cashflow"] / income
            if income and "operating_cashflow" in values
            else None
        )
        row["net_margin"] = income / revenue if revenue and income is not None else None
        row["revenue_growth"] = (
            revenue / previous - 1
            if revenue is not None and previous and previous > 0
            else None
        )
        cfo, capex = values.get("operating_cashflow"), values.get("capex")
        row["free_cashflow"] = (
            cfo - capex
            if cfo is not None and capex is not None and capex >= 0
            else None
        )
        previous = revenue
        rows.append(row)
    return rows[-3:]


def validate_bundle(spec, observations, rows):
    errors = []
    end = cutoff(spec)
    for item in observations:
        published = datetime.fromisoformat(item["published_at"])
        if published.tzinfo is None:
            published = published.replace(tzinfo=ZoneInfo("America/New_York"))
        if item.get("unit") != "USD" or not math.isfinite(item["value"]):
            errors.append("invalid_value:" + item["source_id"])
        if published > end:
            errors.append("future_source:" + item["source_id"])
    if rows != calculate(observations):
        errors.append("calculation_mismatch")
    for row in rows:
        if all(k in row for k in ("assets", "liabilities", "equity")):
            delta = abs(row["assets"] - row["liabilities"] - row["equity"])
            if delta > max(1, abs(row["assets"]) * 1e-6):
                errors.append("balance_sheet_mismatch:" + row["period"])
    gaps = [
        f"{row.get('period', 'unknown')}:{key}"
        for row in rows
        for key in TAGS
        if key not in row
    ]
    for row in rows:
        if row.get("capex", 0) < 0:
            gaps.append("Unsupported capital expenditure sign:" + row["period"])
    if len(rows) < 3:
        gaps.append("Fewer than three fiscal years available")
    gaps.append("Historical market data and valuation vintage not verified; omitted")
    return {
        "state": "invalid" if errors else "partial" if rows else "blocked",
        "errors": errors,
        "gaps": gaps,
    }


def validate_analysis(analysis, observations, sources):
    """Check reference integrity; textual support still needs a research review."""
    allowed = {o["source_id"] for o in observations} | {s["id"] for s in sources}
    errors = []
    if not isinstance(analysis, dict):
        return ["invalid_analysis_shape"]
    for section in ("business", "trends", "risks"):
        claims = analysis.get(section, [])
        if not isinstance(claims, list) or len(claims) > 100:
            errors.append("invalid_analysis_section:" + section)
            continue
        for claim in claims:
            if (
                not isinstance(claim, dict)
                or not isinstance(claim.get("text"), str)
                or not claim["text"].strip()
            ):
                errors.append("invalid_analysis_claim:" + section)
                continue
            refs = claim.get("sources")
            if (
                not isinstance(refs, list)
                or not refs
                or not all(isinstance(ref, str) and ref in allowed for ref in refs)
            ):
                errors.append("missing_evidence:" + section)
    return errors
