---
name: company-research
description: Standardized US company research at a historical cutoff, with SEC evidence, deterministic financial calculations, HTML and Excel. Use for a company-research form request or explicit company-research-v1 workflow.
---

For a new report or an explicit rebuild, run `company-research-v1` through RunWorkflow. For a follow-up question, read the existing snapshot and answer with sources without relaunching the workflow. A request solely to check the local execution environment needs no research run. Pass the supplied cik, as_of, output root and SEC identity as params. Scope is immutable throughout this thread. Do not use current financials, current business summaries, web searches or prices to fill historical gaps. Never trade or send notifications.

The collector is `python -m company_research.cli collect --request-json 'FULL_CANONICAL_SCOPE_JSON' --root ROOT --identity 'Name contact@domain'`. Use the full server scope including cutoff_at and focus, not a shortened copy from the opening message. Quote every argument as shell data. Then `python -m company_research.cli build --root ROOT` produces the report, workbook and validation. Reuse an existing complete snapshot; changing scope needs a new thread and root. Never overwrite raw evidence.

Read sources and observations before analysis. Describe business, financial trends and risks only when the selected filings support them; cite accession and source IDs. Mark inference and missing inputs. Do not invent missing figures or historical valuation. Final delivery must link report.html, research.xlsx, observations.json, sources.json, validation.json and calculate.py. State partial/blocked/invalid honestly. A finished chat is not proof of a valid report. Use existing xlsx recalc/audit/render scripts to check the workbook and inspect HTML before delivery. Research output may be partial because market data vintage cannot be verified.

After workbook recalculation and all checks, run `python -m company_research.cli seal --root ROOT` to refresh the file hashes. Do not rebuild the workbook after recalculation.

For a narrative-only correction, edit analysis.json and use `python -m company_research.cli render --root ROOT`; this preserves the already reviewed workbook. Do not derive causal explanations or rule out working-capital effects from aggregate cash flow and net income alone. Missing tax, one-off, financing or working-capital detail must remain a named uncertainty.

The server writes scope.json in the research root. It is authoritative and the collector reads it directly; never rewrite it or convert cutoff_at yourself. Preserve the timezone and precision.

An omitted or null focus means no extra research focus; the CLI normalizes it to an empty string. Empty strings are supported by RunWorkflow. Do not replace the server cutoff with a UTC midnight or infer it from the date yourself.
