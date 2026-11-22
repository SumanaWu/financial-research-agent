import asyncio
import hashlib
import json

from fastapi import HTTPException

from src.company_research.cli import get_json
from src.company_research.core import (
    ResearchRequest,
    validate_analysis,
    validate_bundle,
)
from src.server.utils.api import require_workspace_owner


async def resolve_company(request):
    try:
        data = await asyncio.to_thread(
            get_json, "https://www.sec.gov/files/company_tickers.json", request.identity
        )
    except (OSError, ValueError):
        raise HTTPException(503, "SEC unavailable or access identity invalid")
    symbol = request.symbol.upper()
    matches = [
        {"cik": str(r["cik_str"]).zfill(10), "name": r["title"], "ticker": r["ticker"]}
        for r in data.values()
        if r["ticker"].upper() == symbol
        or str(r["cik_str"]).zfill(10) == symbol.zfill(10)
    ]
    return {
        "candidates": matches,
        "note": "Ticker mapping is current; use CIK to identify a historical issuer.",
    }


async def research_result(thread_id, user_id, *, acquire=False):
    from src.server.database.conversation.threads_read import (
        get_thread_auth_meta,
        get_thread_by_id,
    )
    from src.server.database.workspace import get_workspace
    from src.server.services.artifacts.reader import ReadMode, snapshot_reader

    owner = await get_thread_auth_meta(str(thread_id))
    if not owner or owner["user_id"] != user_id:
        raise HTTPException(404, "Thread not found")
    thread = await get_thread_by_id(str(thread_id))
    spec = ((thread or {}).get("metadata") or {}).get("company_research")
    if not spec:
        raise HTTPException(404, "Not a company research thread")
    workspace = await get_workspace(str(owner["workspace_id"]))
    require_workspace_owner(workspace, user_id=user_id)
    root = f"research/{thread_id}"
    async with snapshot_reader(
        workspace, user_id, ReadMode.OWNER if acquire else ReadMode.WARM_OR_STORED
    ) as reader:

        async def read(name):
            data = await reader.files.read(root + "/" + name)
            if data is None:
                return None
            if len(data) > 2_000_000:
                raise HTTPException(422, "Research metadata too large")
            return data

        observations, metrics, manifest = (
            await read("observations.json"),
            await read("metrics.json"),
            await read("manifest.json"),
        )
        if not observations or not metrics or not manifest:
            return {"spec": spec, "state": "pending", "root": root}
        try:
            checks = validate_bundle(
                ResearchRequest(**spec), json.loads(observations), json.loads(metrics)
            )
            entries = json.loads(manifest)
            if not isinstance(entries, dict):
                raise TypeError("Invalid manifest")
            required = {
                "request.json",
                "sources.json",
                "observations.json",
                "metrics.json",
                "validation.json",
                "report.html",
                "research.xlsx",
                "calculate.py",
                "research_core.py",
                "snapshot.json",
            }
            if not required <= entries.keys():
                raise ValueError("Incomplete manifest")
            stored_request = await read("request.json")
            if ResearchRequest(**json.loads(stored_request)) != ResearchRequest(**spec):
                checks["errors"].append(
                    "scope_mismatch: 研究文件中的截止时间与提交的范围不一致，请重新创建研究。"
                )
            if not isinstance(entries, dict) or len(entries) > 30:
                raise TypeError("Invalid manifest")
            for name, sha in entries.items():
                if "/" in name or "\\" in name or name in (".", ".."):
                    raise ValueError("Invalid path")
                body = await read(name)
                if body is None or hashlib.sha256(body).hexdigest() != sha:
                    checks["errors"].append("file_changed:" + name)
            analysis_data = await read("analysis.json")
            if analysis_data:
                checks["errors"].extend(
                    validate_analysis(
                        json.loads(analysis_data),
                        json.loads(observations),
                        json.loads(await read("sources.json")),
                    )
                )
            else:
                checks["gaps"].append("Narrative analysis not supplied")
            if checks["errors"]:
                checks["state"] = "invalid"
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "Research files are invalid")
    return {"spec": spec, **checks, "root": root, "files": list(entries)}
