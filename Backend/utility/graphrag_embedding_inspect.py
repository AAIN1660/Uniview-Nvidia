"""
Inspect GraphRAG stored entity embeddings (blob parquets + optional LanceDB).

Used by ``graphrag_verify_embeddings.py`` and callable from other tooling.
"""

from __future__ import annotations

import io
import os
from collections import Counter
from typing import Any

import pandas as pd

from utility.graphrag_artifacts import (
    expected_graph_embedding_dim,
    graph_lancedb_uri,
    graphrag_embeddings_use_nim,
    resolve_graph_artifacts_folder,
    validate_entity_embedding_dims,
)
from utility.graphrag_text_embedder import graphrag_nim_embedding_model_id

ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
ARTIFACT_PARQUETS = (
    "create_final_entities",
    "create_final_nodes",
    "create_final_relationships",
    "create_final_community_reports",
    "create_final_text_units",
)


def _embedding_length(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return len(value)
    return None


def inspect_entities_parquet(df: pd.DataFrame, *, expected_dim: int) -> dict[str, Any]:
    """Summarize ``description_embedding`` vectors in ``create_final_entities``."""
    col = "description_embedding"
    if col not in df.columns:
        return {
            "ok": False,
            "error": f"column '{col}' missing (columns: {list(df.columns)})",
        }

    lengths: list[int] = []
    missing = 0
    for val in df[col]:
        n = _embedding_length(val)
        if n is None:
            missing += 1
        else:
            lengths.append(n)

    if not lengths:
        return {
            "ok": False,
            "error": "no non-empty description_embedding vectors in parquet",
            "entity_rows": len(df),
            "missing_embeddings": missing,
        }

    counts = Counter(lengths)
    unique_dims = sorted(counts.keys())
    primary_dim = counts.most_common(1)[0][0]
    ok = primary_dim == expected_dim and len(unique_dims) == 1

    return {
        "ok": ok,
        "entity_rows": len(df),
        "with_embedding": len(lengths),
        "missing_embeddings": missing,
        "unique_dims": unique_dims,
        "dim_counts": dict(counts),
        "primary_dim": primary_dim,
        "expected_dim": expected_dim,
        "matches_expected": ok,
    }


def load_entities_df_from_bytes(data: bytes) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(data))


def verify_graphrag_artifacts(
    *,
    folder_path: str,
    container_name: str | None = None,
    blob_service_client: Any = None,
    local_artifacts_dir: str | None = None,
    probe_query_embed: bool = True,
) -> dict[str, Any]:
    """
    Verify GraphRAG artifact embeddings for a category folder.

    Reads ``create_final_entities.parquet`` from blob or ``local_artifacts_dir``.
    """
    expected_dim = expected_graph_embedding_dim()
    use_nim = graphrag_embeddings_use_nim()
    report: dict[str, Any] = {
        "folder_path": folder_path,
        "expected_dim": expected_dim,
        "embed_backend": "nvidia" if use_nim else "azure",
        "nim_model": graphrag_nim_embedding_model_id() if use_nim else None,
        "lancedb_path": graph_lancedb_uri(folder_path),
    }

    # Parquet source
    df: pd.DataFrame | None = None
    parquet_source = ""

    if local_artifacts_dir:
        path = os.path.join(local_artifacts_dir, f"{ENTITY_EMBEDDING_TABLE}.parquet")
        if not os.path.isfile(path):
            report["ok"] = False
            report["error"] = f"local parquet not found: {path}"
            return report
        df = pd.read_parquet(path)
        parquet_source = path
    else:
        if not container_name or blob_service_client is None:
            report["ok"] = False
            report["error"] = "blob client/container required unless --local-dir is set"
            return report
        missing = []
        for name in ARTIFACT_PARQUETS:
            blob = f"{folder_path.rstrip('/')}/{name}.parquet"
            if not blob_service_client.get_blob_client(
                container=container_name, blob=blob
            ).exists():
                missing.append(blob)
        report["missing_parquets"] = missing
        blob_path = f"{folder_path.rstrip('/')}/{ENTITY_EMBEDDING_TABLE}.parquet"
        data = blob_service_client.get_blob_client(
            container=container_name, blob=blob_path
        ).download_blob().readall()
        df = load_entities_df_from_bytes(data)
        parquet_source = f"blob:{container_name}/{blob_path}"

    report["parquet_source"] = parquet_source
    summary = inspect_entities_parquet(df, expected_dim=expected_dim)
    report.update(summary)

    # Same check inference uses at runtime (GraphRAG entity objects)
    if summary.get("with_embedding", 0) > 0:
        try:
            from graphrag.query.indexer_adapters import read_indexer_entities

            entity_df = df  # entities table only; nodes join not required for dim probe
            entities = read_indexer_entities(
                pd.DataFrame(),
                entity_df,
                community_level=3,
                description_embedding_col="description_embedding",
            )
            validate_entity_embedding_dims(entities, expected_dim, folder_path)
            report["runtime_validator"] = "passed"
        except Exception as exc:
            report["runtime_validator"] = f"failed: {exc}"
            report["ok"] = False
            report["error"] = str(exc)

    # Optional: confirm query-side NIM embedder returns same width
    if probe_query_embed and use_nim and summary.get("matches_expected"):
        try:
            from utility.embedding_config import create_embedding_vector, get_embedding_client

            client = get_embedding_client()
            qvec = create_embedding_vector(client, "graphrag embedding probe", input_type="query")
            report["query_probe_dim"] = len(qvec)
            report["query_probe_ok"] = len(qvec) == expected_dim
            if not report["query_probe_ok"]:
                report["ok"] = False
                report["error"] = (
                    f"query embedding dim {len(qvec)} != expected {expected_dim}"
                )
        except Exception as exc:
            report["query_probe_ok"] = False
            report["query_probe_error"] = str(exc)

    # LanceDB on disk (built on first query, may not exist yet)
    lance_path = report["lancedb_path"]
    if os.path.isdir(lance_path):
        report["lancedb_exists"] = True
        try:
            import lancedb

            db = lancedb.connect(lance_path)
            tables = db.table_names()
            report["lancedb_tables"] = tables
            if "entity_description_embeddings" in tables:
                tbl = db.open_table("entity_description_embeddings")
                report["lancedb_row_count"] = tbl.count_rows()
        except Exception as exc:
            report["lancedb_note"] = f"could not open LanceDB: {exc}"
    else:
        report["lancedb_exists"] = False
        report["lancedb_note"] = "not built yet (normal until first graph/hybrid query)"

    return report


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "",
        "=== GraphRAG embedding verification ===",
        f"  folder:          {report.get('folder_path')}",
        f"  parquet:         {report.get('parquet_source')}",
        f"  backend:         {report.get('embed_backend')}",
        f"  expected dim:    {report.get('expected_dim')}",
    ]
    if report.get("nim_model"):
        lines.append(f"  NIM model:         {report.get('nim_model')}")
    if report.get("entity_rows") is not None:
        lines.append(f"  entity rows:       {report.get('entity_rows')}")
        lines.append(f"  with embedding:    {report.get('with_embedding')}")
        lines.append(f"  missing embedding: {report.get('missing_embeddings')}")
        lines.append(f"  stored dims:       {report.get('unique_dims')}")
        lines.append(f"  dim histogram:     {report.get('dim_counts')}")
    if report.get("runtime_validator"):
        lines.append(f"  runtime check:     {report.get('runtime_validator')}")
    if "query_probe_dim" in report:
        lines.append(
            f"  query probe dim:   {report.get('query_probe_dim')} "
            f"(ok={report.get('query_probe_ok')})"
        )
    if report.get("missing_parquets"):
        lines.append(f"  missing parquets:  {report.get('missing_parquets')}")
    lines.append(f"  LanceDB path:      {report.get('lancedb_path')}")
    lines.append(f"  LanceDB exists:    {report.get('lancedb_exists')}")
    if report.get("lancedb_row_count") is not None:
        lines.append(f"  LanceDB rows:      {report.get('lancedb_row_count')}")
    if report.get("lancedb_note"):
        lines.append(f"  LanceDB note:      {report.get('lancedb_note')}")
    status = "PASS" if report.get("ok") else "FAIL"
    lines.append(f"  result:            {status}")
    if report.get("error"):
        lines.append(f"  error:             {report.get('error')}")
    lines.append("")
    return "\n".join(lines)
