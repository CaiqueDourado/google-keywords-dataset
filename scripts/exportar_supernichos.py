"""Export the Buscas tables from SQL Server to Parquet, ONE sequential read per table (no LIKE, no GROUP BY on
the server). Every check and the cleaning run afterwards on the Parquet files, with DuckDB, on your machine.

    python exportar_supernichos.py --server localhost --out D:\\buscas_raw

Writes, in --out:
  keywords/part-0000.parquet …   supernichos.dbo.keywords (54.9 M rows, ~2 M per part)
  padroes.parquet                supernichos.dbo.padroes (2.0 M)
  entidades_normalizado.parquet  nlp.dbo.palavras_replace_normalizado (412 k)
  entidades.parquet              nlp.dbo.palavras_replace (2.3 M; phonetic keys included)
  padroes_algoritmos.parquet     nlp_padroes.dbo.padroes_agrupado (1.7 M): patterns of every algorithm, with entities,
                                 the curation labels (uso, visto) and the generalized parent (padrao_pai)
  padroes_buscas/part-*.parquet  nlp_padroes.dbo.padroes (141 M pattern → search pairs), only with --with-mapping

Raw copy: nothing is cleaned or removed here, so this folder stays on your machine (never on GitHub).
Needs pyodbc and pyarrow. Re-running skips the files that already exist.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

TABLES = {
    "keywords": ("SELECT id, idPadrao, Keyword, CAST(Volume AS bigint) Volume, CAST(Competition AS float) Competition, "
                 "CAST(CPC AS float) CPC, tipo, idioma FROM supernichos.dbo.keywords WITH (NOLOCK)"),
    "padroes": ("SELECT id, padrao, quantidade, CAST(volume AS bigint) volume, CAST(competition AS float) competition, "
                "CAST(cpc AS float) cpc, filho, NumPalavras, exemplo1, exemplo2, QuartilCompetition, QuartilCPC, "
                "QuartilVolume, QuartilNumTermos, tipo, idioma FROM supernichos.dbo.padroes WITH (NOLOCK)"),
    "padroes_algoritmos": ("SELECT id, padrao, quantidade, CAST(volume AS bigint) volume, CAST(competition AS float) competition, "
                           "CAST(cpc AS float) cpc, filho, NumPalavras, QuartilCompetition, QuartilCPC, QuartilVolume, "
                           "QuartilNumTermos, uso, CAST(uso_obs AS nvarchar(max)) uso_obs, visto, padrao_pai, tipo, padrao_pai_nivel "
                           "FROM nlp_padroes.dbo.padroes_agrupado WITH (NOLOCK)"),
    "padroes_buscas": ("SELECT padrao, tipo, Keyword, NumPalavras FROM nlp_padroes.dbo.padroes WITH (NOLOCK)"),
    "entidades_normalizado": "SELECT id, palavra, tipos, tipos_normalizado FROM nlp.dbo.palavras_replace_normalizado WITH (NOLOCK)",
    "entidades": ("SELECT id, palavra, tipo, possuiAmbiguacao, fingerprint, ngram, metaphone, tokenizada, idioma, "
                  "idiomaDefinitivo, foiNormalizadaManualmente, tipo_normalizado, tipos, tipos2, palavra_sem_acento "
                  "FROM nlp.dbo.palavras_replace WITH (NOLOCK)"),
}
PART_ROWS = {"keywords": 2_000_000, "padroes_buscas": 5_000_000}
BATCH = 200_000


def connect(server: str):
    import pyodbc
    return pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};Trusted_Connection=yes",
                          autocommit=True)


def export(cur, name: str, sql: str, out: Path) -> None:
    parted = name in PART_ROWS
    target = out / name if parted else out / f"{name}.parquet"
    if (parted and target.exists() and any(target.glob("*.parquet"))) or (not parted and target.exists()):
        print(f"{name}: already there, skipped")
        return
    if parted:
        target.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    types = {int: pa.int64(), float: pa.float64(), str: pa.string(), bool: pa.bool_()}
    schema = pa.schema([(d[0], types.get(d[1], pa.string())) for d in cur.description])
    writer, part, in_part, total = None, 0, 0, 0
    tmp = target.with_suffix(".tmp") if not parted else None
    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        table = pa.Table.from_pydict({c: [r[i] for r in rows] for i, c in enumerate(cols)}, schema=schema)
        if writer is None:
            path = target / f"part-{part:04d}.parquet" if parted else tmp
            writer = pq.ParquetWriter(path, schema, compression="zstd")
        writer.write_table(table)
        in_part += len(rows)
        total += len(rows)
        if parted and in_part >= PART_ROWS[name]:
            writer.close()
            writer, part, in_part = None, part + 1, 0
        print(f"\r{name}: {total:,} rows  {time.time() - t0:.0f}s", end="", flush=True)
    if writer:
        writer.close()
    if tmp:
        tmp.replace(target)
    print(f"\r{name}: {total:,} rows  {time.time() - t0:.0f}s  -> {target}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="localhost")
    ap.add_argument("--out", type=Path, default=Path("buscas_raw"))
    ap.add_argument("--only", help="comma-separated subset of: " + ", ".join(TABLES))
    ap.add_argument("--with-mapping", action="store_true", help="also export padroes_buscas (141 M rows, slow)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cur = connect(a.server).cursor()
    for name, sql in TABLES.items():
        if a.only and name not in a.only.split(","):
            continue
        if name == "padroes_buscas" and not (a.with_mapping or (a.only and name in a.only.split(","))):
            continue
        export(cur, name, sql, a.out)


if __name__ == "__main__":
    main()
