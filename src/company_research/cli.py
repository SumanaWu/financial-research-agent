"""Run inside the research sandbox: python -m company_research.cli ..."""

import argparse
import html
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from .core import (
    ResearchRequest,
    calculate,
    cutoff,
    digest,
    select_facts,
    validate_analysis,
    validate_bundle,
)


def get_json(url, identity):
    if "@" not in identity or "example.com" in identity:
        raise ValueError("Provide a real SEC identity: name and contact email")
    for attempt in range(3):
        try:
            with urlopen(
                Request(url, headers={"User-Agent": identity}), timeout=25
            ) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2**attempt)


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(spec, root, identity):
    root.mkdir(parents=True, exist_ok=True)
    if (root / "scope.json").is_file():
        spec = ResearchRequest(**json.loads((root / "scope.json").read_text()))
    request = spec.model_dump(mode="json")
    if (root / "request.json").exists():
        stored = json.loads((root / "request.json").read_text())
        if spec.cutoff_at is None:
            request["cutoff_at"] = stored.get("cutoff_at")
        if stored != request:
            raise ValueError(
                "Existing snapshot has another request; use a new directory"
            )
        required = (
            "sources.json",
            "observations.json",
            "snapshot.json",
            "raw/companyfacts.json",
            "raw/submissions.json",
        )
        if not all((root / name).is_file() for name in required):
            raise ValueError(
                "Cached snapshot is incomplete; use a new research directory"
            )
        return
    spec.cutoff_at = cutoff(spec)
    request = spec.model_dump(mode="json")
    raw = root / "raw"
    raw.mkdir(exist_ok=True)
    submissions = get_json(
        f"https://data.sec.gov/submissions/CIK{spec.cik}.json", identity
    )
    write(raw / "submissions.json", submissions)
    recent = submissions["filings"]["recent"]
    tables = [recent]
    for item in submissions["filings"].get("files", []):
        if item.get("filingFrom", "") <= spec.as_of.isoformat():
            time.sleep(0.25)
            table = get_json(
                "https://data.sec.gov/submissions/" + item["name"], identity
            )
            write(raw / item["name"], table)
            tables.append(table)
    filings = [
        dict(zip(table, values)) for table in tables for values in zip(*table.values())
    ]
    facts = get_json(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{spec.cik}.json", identity
    )
    write(raw / "companyfacts.json", facts)
    observations = select_facts(facts, filings, cutoff(spec))
    periods = sorted({o["end"] for o in observations})[-4:]
    observations = [o for o in observations if o["end"] in periods]
    quarterly = select_facts(facts, filings, cutoff(spec), annual=False)
    latest_quarter = max((o["end"] for o in quarterly), default=None)
    quarterly = [o for o in quarterly if o["end"] == latest_quarter]
    write(root / "quarterly.json", quarterly)
    sources = []
    for accession in sorted({o["accession"] for o in observations + quarterly}):
        filing = next(f for f in filings if f["accessionNumber"] == accession)
        base = f"https://www.sec.gov/Archives/edgar/data/{int(spec.cik)}/{accession.replace('-', '')}/"
        sources.append(
            {"id": accession, "url": base + filing.get("primaryDocument", ""), **filing}
        )
    for source in sources:
        time.sleep(0.25)
        with urlopen(
            Request(source["url"], headers={"User-Agent": identity}), timeout=25
        ) as response:
            content = response.read(20_000_001)
        if len(content) > 20_000_000:
            raise ValueError("Filing exceeds 20 MB limit")
        (raw / (source["id"] + ".html")).write_bytes(content)
        source["sha256"] = __import__("hashlib").sha256(content).hexdigest()
    write(root / "sources.json", sources)
    write(root / "observations.json", observations)
    write(
        root / "snapshot.json",
        {
            "fetched_at": datetime.now(UTC).isoformat(),
            "company": submissions.get("name"),
            "facts_sha256": digest(facts),
        },
    )
    write(root / "request.json", request)  # commit marker after all snapshot files


def build(root, *, preserve_workbook=False):
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    spec = ResearchRequest(**json.loads((root / "request.json").read_text()))
    observations = json.loads((root / "observations.json").read_text())
    rows = calculate(observations)
    checks = validate_bundle(spec, observations, rows)
    write(root / "metrics.json", rows)
    write(root / "validation.json", checks)
    sources = json.loads((root / "sources.json").read_text())
    snapshot_path = root / "snapshot.json"
    company = (
        json.loads(snapshot_path.read_text()).get("company")
        if snapshot_path.exists()
        else None
    ) or f"CIK {spec.cik}"
    if not (root / "analysis.json").exists():
        checks["gaps"].append("Narrative analysis not supplied")
    write(root / "validation.json", checks)
    fields = [
        "revenue",
        "net_income",
        "assets",
        "liabilities",
        "equity",
        "operating_cashflow",
        "capex",
        "free_cashflow",
        "net_margin",
        "revenue_growth",
        "debt_ratio",
        "cash_conversion",
    ]
    analysis = (
        json.loads((root / "analysis.json").read_text())
        if (root / "analysis.json").exists()
        else {}
    )
    if validate_analysis(analysis, observations, sources):
        raise ValueError(
            "Analysis claim references missing evidence or invalid content"
        )
    if not preserve_workbook:
        wb = Workbook()
        overview = wb.active
        overview.title = "Overview"
        overview.append(["Company", company])
        overview.append(["CIK", spec.cik])
        overview.append(["As of", str(spec.as_of)])
        overview.append(["Delivery", checks["state"]])
        financials = wb.create_sheet("Financials")
        financials.append(["Period", *fields[:7]])
        metrics = wb.create_sheet("Metrics")
        metrics.append(
            [
                "Period",
                "Free cashflow",
                "Net margin",
                "Revenue growth",
                "Debt ratio",
                "Cash conversion",
            ]
        )
        all_rows = calculate(observations)
        periods = sorted({o["end"] for o in observations})[-4:]
        if len(periods) == 4:
            base = {
                o["metric"]: o["value"] for o in observations if o["end"] == periods[0]
            }
            all_rows = [{"period": periods[0], **base}, *rows]
        if all_rows:
            latest = len(all_rows) + 1
            overview.append(["Latest fiscal period", f"=Financials!A{latest}"])
            overview.append(["Revenue (USD)", f"=Financials!B{latest}"])
            overview.append(["Net income (USD)", f"=Financials!C{latest}"])
            overview.append(["Free cashflow (USD)", f"=Metrics!B{latest}"])
            overview.append(["Net margin", f"=Metrics!C{latest}"])
            overview.cell(overview.max_row, 2).number_format = "0.00%"
        for gap in checks["gaps"]:
            overview.append(["Data gap", gap])
        for i, row in enumerate(all_rows, 2):
            financials.append([row["period"], *(row.get(k) for k in fields[:7])])
            metrics.append(
                [
                    row["period"],
                    f'=IF(OR(Financials!G{i}="",Financials!H{i}="",Financials!H{i}<0),"",Financials!G{i}-Financials!H{i})',
                    f'=IF(OR(Financials!B{i}="",Financials!B{i}=0,Financials!C{i}=""),"",Financials!C{i}/Financials!B{i})',
                    ""
                    if i == 2
                    else f'=IF(OR(Financials!B{i}="",Financials!B{i - 1}="",Financials!B{i - 1}<=0),"",Financials!B{i}/Financials!B{i - 1}-1)',
                ]
            )
            metrics.cell(
                i,
                5,
                f'=IF(OR(Financials!E{i}="",Financials!D{i}="",Financials!D{i}=0),"",Financials!E{i}/Financials!D{i})',
            )
            metrics.cell(
                i,
                6,
                f'=IF(OR(Financials!G{i}="",Financials!C{i}="",Financials!C{i}=0),"",Financials!G{i}/Financials!C{i})',
            )
            for j, key in enumerate(fields[:7], 2):
                refs = [
                    o["source_id"]
                    for o in observations
                    if o["end"] == row["period"] and o["metric"] == key
                ]
                financials.cell(i, j).comment = Comment(
                    "\n".join(refs) or "Missing", "Source"
                )
        ws = wb.create_sheet("Sources")
        ws.append(["Accession", "URL", "Published"])
        for s in sources:
            ws.append([s["id"], s["url"], s["acceptanceDateTime"]])
        quarter_sheet = wb.create_sheet("Quarterly")
        quarter_sheet.append(["Period", "Metric", "Value", "Source"])
        quarter_path = root / "quarterly.json"
        for item in (
            json.loads(quarter_path.read_text()) if quarter_path.exists() else []
        ):
            quarter_sheet.append(
                [item["end"], item["metric"], item["value"], item["source_id"]]
            )
        ws = wb.create_sheet("Checks")
        ws.append(["State", checks["state"]])
        for gap in checks["gaps"]:
            ws.append(["Gap", gap])
        ws.append([])
        ws.append(["Hard check", "Difference", "Verdict"])
        first_check = ws.max_row + 1
        for i, row in enumerate(all_rows, 2):
            check_row = ws.max_row + 1
            ws.append(
                [
                    "Balance sheet " + row["period"],
                    f'=IF(COUNT(Financials!D{i}:F{i})=3,Financials!D{i}-Financials!E{i}-Financials!F{i},"" )',
                    f'=IF(B{check_row}="","MISSING",IF(ABS(B{check_row})<=MAX(1,ABS(Financials!D{i})*0.000001),"OK","FAIL"))',
                ]
            )
            check_row = ws.max_row + 1
            ws.append(
                [
                    "Free cashflow " + row["period"],
                    f'=IF(COUNT(Financials!G{i}:H{i})=2,Metrics!B{i}-(Financials!G{i}-Financials!H{i}),"" )',
                    f'=IF(B{check_row}="","MISSING",IF(ABS(B{check_row})<=1,"OK","FAIL"))',
                ]
            )
        last_check = ws.max_row
        verdicts = f"C{first_check}:C{last_check}"
        ws.append(
            [
                "Overall",
                f'=COUNTIF({verdicts},"FAIL")' if all_rows else None,
                f'=IF(COUNTIF({verdicts},"FAIL")>0,"FAIL",IF(COUNTIF({verdicts},"MISSING")>0,"MISSING","OK"))'
                if all_rows
                else "MISSING",
            ]
        )
        for sheet in wb:
            sheet.sheet_view.showGridLines = False
            sheet.sheet_properties.pageSetUpPr.fitToPage = True
            sheet.page_setup.orientation = "landscape"
            sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
            sheet.page_setup.fitToWidth = 1
            sheet.page_setup.fitToHeight = 0
            sheet.print_title_rows = "1:1"
            sheet.print_options.horizontalCentered = True
            sheet.freeze_panes = "B2"
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = 24
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="243746")
            for row in sheet:
                for cell in row:
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    cell.border = Border(bottom=Side(style="hair", color="D9D9D9"))
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "#,##0.00"
                    elif cell.data_type == "f":
                        cell.font = Font(
                            color="008000" if "!" in cell.value else "000000"
                        )
                        if cell.number_format == "General":
                            cell.number_format = '#,##0;(#,##0);"-"'
            if sheet.title in ("Metrics", "Checks"):
                for row in sheet.iter_rows(min_row=2, min_col=2, max_col=2):
                    row[0].number_format = '#,##0;(#,##0);"-"'
            if sheet.title == "Metrics":
                for row in sheet.iter_rows(min_row=2, min_col=3):
                    for cell in row:
                        cell.number_format = "0.00%"
            if sheet.title == "Financials":
                for row in sheet.iter_rows(min_row=2, min_col=2):
                    for cell in row:
                        cell.font = Font(color="0000FF")
        overview.column_dimensions["A"].width = 30
        overview.column_dimensions["B"].width = 75
        for row in overview:
            overview.row_dimensions[row[0].row].height = 32
        for row in wb["Sources"].iter_rows(min_row=2):
            wb["Sources"].row_dimensions[row[0].row].height = 65
        wb["Sources"].column_dimensions["B"].width = 70
        for row in wb["Quarterly"].iter_rows(min_row=2):
            wb["Quarterly"].row_dimensions[row[0].row].height = 60
            row[2].font = Font(color="0000FF")
            row[2].comment = Comment(str(row[3].value), "Source")
        wb["Quarterly"].column_dimensions["D"].width = 70
        wb.save(root / "research.xlsx")
    esc = html.escape
    body = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>公司研究</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;padding:16px}table{border-collapse:collapse;width:100%}p{overflow-wrap:anywhere}td,th{border:1px solid #ccc;padding:8px}a{overflow-wrap:anywhere}</style>'
    body += f"<h1>{esc(company)} · 公司财务研究</h1><p>CIK {spec.cik}；截止日：{spec.as_of}；币种 USD；交付状态：{checks['state']}</p>"
    labels = {
        "revenue": "营业收入",
        "net_income": "净利润",
        "assets": "总资产",
        "liabilities": "总负债",
        "equity": "股东权益",
        "operating_cashflow": "经营现金流",
        "capex": "资本开支",
        "free_cashflow": "自由现金流",
        "net_margin": "净利率",
        "revenue_growth": "收入增长率",
        "debt_ratio": "资产负债率",
        "cash_conversion": "现金流转化率",
    }
    ratios = {"net_margin", "revenue_growth", "debt_ratio", "cash_conversion"}
    body += (
        "<h2>已公开财务数据</h2><p>金额单位：百万 USD；比率以百分比展示。点击原始指标数字可查看来源。</p><table><tr><th>指标</th>"
        + "".join("<th>" + row["period"] + "</th>" for row in rows)
        + "</tr>"
    )
    source_urls = {source["id"]: source["url"] for source in sources}
    for key in fields:
        body += "<tr><th>" + labels[key] + "</th>"
        for row in rows:
            value = row.get(key)
            text = (
                "缺失"
                if value is None
                else (f"{value:.2%}" if key in ratios else f"{value / 1e6:,.2f}")
            )
            refs = [
                o
                for o in observations
                if o["end"] == row["period"] and o["metric"] == key
            ]
            if refs:
                text = (
                    '<a href="'
                    + esc(source_urls[refs[0]["accession"]], quote=True)
                    + '" title="'
                    + esc(refs[0]["source_id"], quote=True)
                    + '">'
                    + text
                    + "</a>"
                )
            body += "<td>" + text + "</td>"
        body += "</tr>"
    body += "</table>"
    quarter_file = root / "quarterly.json"
    quarterly = json.loads(quarter_file.read_text()) if quarter_file.exists() else []
    citation_urls = dict(source_urls)
    for item in [*observations, *quarterly]:
        citation_urls[item["source_id"]] = source_urls[item["accession"]]
    body += "<h2>最近 10-Q 的独立季度字段</h2>"
    if not quarterly:
        body += "<p>缺少可核实的独立季度数据，累计期间未当作单季使用。</p>"
    for item in quarterly:
        body += (
            "<p>"
            + esc(
                item["end"]
                + " "
                + item["metric"]
                + ": "
                + str(item["value"])
                + " USD ["
                + item["source_id"]
                + "]"
            )
            + "</p>"
        )
    for section, label in [
        ("business", "业务分析"),
        ("trends", "财务趋势"),
        ("risks", "风险"),
    ]:
        body += "<h2>" + label + "</h2>"
        for claim in analysis.get(section, []):
            body += (
                "<p>"
                + esc(claim["text"])
                + " ["
                + ", ".join(
                    f'<a href="{esc(citation_urls[ref], quote=True)}">{esc(ref)}</a>'
                    for ref in claim["sources"]
                )
                + "]</p>"
            )
        if not analysis.get(section):
            body += "<p>缺少已验证的分析材料。</p>"
    body += (
        "<h2>资料缺口</h2><ul>"
        + "".join("<li>" + esc(g) + "</li>" for g in checks["gaps"])
        + "</ul><h2>来源</h2><ul>"
    )
    body += (
        "".join(
            f'<li><a href="{esc(s["url"], quote=True)}">{esc(s["id"])}</a> {esc(s["acceptanceDateTime"])}</li>'
            for s in sources
        )
        + "</ul>"
    )
    (root / "report.html").write_text(body, encoding="utf-8")
    (root / "calculate.py").write_text(
        'import json\nfrom pathlib import Path\nfrom research_core import calculate\np=Path(__file__).parent\nprint(json.dumps(calculate(json.loads((p/"observations.json").read_text())), indent=2))\n'
    )
    (root / "requirements.txt").write_text("pydantic>=2,<3\n")
    (root / "research_core.py").write_text(
        Path(__file__).with_name("core.py").read_text()
    )
    seal(root)
    return checks


def seal(root):
    write(
        root / "manifest.json",
        {
            p.name: __import__("hashlib").sha256(p.read_bytes()).hexdigest()
            for p in root.iterdir()
            if p.is_file() and p.name not in ("manifest.json", "scope.json")
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "build", "render", "seal"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--request-json")
    parser.add_argument("--cik")
    parser.add_argument("--as-of")
    parser.add_argument("--identity")
    args = parser.parse_args()
    root = Path(args.root)
    if args.action == "collect":
        collect(
            ResearchRequest(**json.loads(args.request_json))
            if args.request_json
            else ResearchRequest(cik=args.cik, as_of=args.as_of),
            root,
            args.identity or "",
        )
    elif args.action == "render":
        print(json.dumps(build(root, preserve_workbook=True), ensure_ascii=False))
    elif args.action == "build":
        print(json.dumps(build(root), ensure_ascii=False))
    else:
        seal(root)


if __name__ == "__main__":
    main()
