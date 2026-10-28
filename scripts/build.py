"""Build the published dataset from the raw export (exportar_supernichos.py), with DuckDB.

    python scripts/build.py --raw D:\\buscas_raw --out D:\\buscas_out

Writes, in --out:
  kaggle/palavras_chave-NNNN.parquet     one row per search, cleaned and deduplicated (files under 45 MB)
  kaggle/padroes.parquet                 one row per pattern (template) with its totals
  kaggle/perguntas.parquet               Brazilian searches phrased as questions (como, qual, onde…)
  kaggle/padroes_algoritmos.parquet      patterns of every algorithm (viana … rosa), with entities and curation labels
  kaggle/padroes_buscas-NNNN.parquet     pattern -> search pairs per algorithm (138 M), when exported
  sample/*.csv                           small samples for GitHub
  stats.json                             counts used in the README

Cleaning (see README, "How it was made"):
  - idioma is the MARKET of the keyword tool: pt-br → BR, en → US, es → ES, ar → AR (Argentina, Spanish)
  - batch 1 (tipo empty) = Ubersuggest 2018 (Brazil only); batch 2 (tipo N1) = DataForSEO (4 markets)
  - volume 0 → null: in batch 1 a zero means "no metric" (only 5,330 of 18.3 M zeros have competition or CPC)
  - competition to 0–1: values above 1 were on a 0–100 scale and are divided by 100
  - apostrophes doubled on import ('' → '); searches damaged into "??" removed
  - duplicates (same market, same search ignoring case and spaces) collapsed, keeping the row with volume
  - adulto = true for searches with explicit adult terms (kept, so users can filter)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

MAX_BYTES = 45_000_000
ADULT = r"\b(porn\w*|xvideos?|xxx+|sexo|puta\w*|nudes?|nuas?|nu[ae]\b|transando|buceta|pornografia|hentai|xnxx|redtube|brazzers|pelad[ao]s?|putaria|safad[ao]s?|sex|desnud\w*)\b"
QUESTION = r"^(como|qual|quais|onde|quando|quanto|quantos|quantas|quem|por que|porque|pra que|para que|o que|que horas|melhor|melhores|vale a pena|[eé] bom)\b"
MARKET = "CASE idioma WHEN 'pt-br' THEN 'BR' WHEN 'en' THEN 'US' WHEN 'es' THEN 'ES' WHEN 'ar' THEN 'AR' ELSE idioma END"
SOURCE = "CASE WHEN tipo = 'N1' THEN 'dataforseo' ELSE 'ubersuggest_2018' END"


def write_parts(con, sql: str, folder: Path, prefix: str, row_group: int = 500_000) -> int:
    """Writes <folder>/<prefix>-0000.parquet, -0001… each under MAX_BYTES (flat names: Kaggle keeps no subfolders)."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{prefix}-*.parquet"):
        old.unlink()
    res = con.execute(sql)
    reader = res.to_arrow_reader(row_group) if hasattr(res, "to_arrow_reader") else res.fetch_record_batch(row_group)
    part, writer, path, total = 0, None, None, 0
    for batch in reader:
        if writer is None:
            path = folder / f"{prefix}-{part:04d}.parquet"
            writer = pq.ParquetWriter(path, batch.schema, compression="zstd")
        writer.write_batch(batch)
        total += batch.num_rows
        if os.path.getsize(path) >= MAX_BYTES * 0.85:
            writer.close()
            writer, part = None, part + 1
    if writer:
        writer.close()
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-pairs", action="store_true", help="keep kaggle/padroes_buscas from a previous run (slow step)")
    a = ap.parse_args()
    t0 = time.time()
    kag, smp = a.out / "kaggle", a.out / "sample"
    kag.mkdir(parents=True, exist_ok=True)
    smp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"SET temp_directory = '{(a.out / 'tmp').as_posix()}'")  # spills to disk instead of running out of memory
    raw = a.raw.as_posix()

    con.execute(f"""
        CREATE TEMP TABLE kw AS
        WITH src AS (
            SELECT id, idPadrao AS id_padrao,
                   trim(regexp_replace(Keyword, '''+', '''', 'g')) AS palavra,
                   {MARKET} AS mercado, {SOURCE} AS fonte,
                   NULLIF(Volume, 0) AS volume,
                   CASE WHEN Volume = 0 AND Competition = 0 AND CPC = 0 THEN NULL
                        WHEN Competition > 1 THEN Competition / 100 ELSE Competition END AS concorrencia,
                   CASE WHEN Volume = 0 AND Competition = 0 AND CPC = 0 THEN NULL ELSE CPC END AS cpc
            FROM read_parquet('{raw}/keywords/*.parquet')
            WHERE Keyword NOT LIKE '%??%'
        )
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, row_number() OVER (PARTITION BY mercado, lower(regexp_replace(palavra, '\\s+', ' ', 'g'))
                                         ORDER BY volume DESC NULLS LAST, id DESC) rn
            FROM src WHERE palavra <> ''
        ) WHERE rn = 1
    """)
    n_kw = write_parts(con, f"""
        SELECT id, palavra, mercado, fonte, volume, round(concorrencia, 4) AS concorrencia, cpc,
               id_padrao,
               len(string_split(palavra, ' ')) AS num_palavras,
               regexp_matches(lower(palavra), '{ADULT}') AS adulto
        FROM kw ORDER BY mercado, palavra""", kag, "palavras_chave")

    con.execute(f"""
        CREATE TEMP TABLE pd AS
        SELECT id, trim(regexp_replace(padrao, '''+', '''', 'g')) AS padrao,
               {MARKET} AS mercado, {SOURCE} AS fonte,
               quantidade AS num_buscas, volume AS volume_total,
               round(CASE WHEN competition > 1 THEN competition / 100 ELSE competition END, 4) AS concorrencia_media,
               cpc AS cpc_medio,
               trim(regexp_replace(trim(regexp_replace(filho, '''+', '''', 'g'), ''''), '\\s*\\([0-9.]+\\)\\s*$', ''), '''') AS busca_lider,
               trim(regexp_replace(exemplo1, '''+', '''', 'g'), '''') AS exemplo1,
               trim(regexp_replace(exemplo2, '''+', '''', 'g'), '''') AS exemplo2,
               NumPalavras AS num_palavras,
               QuartilVolume AS faixa_volume, QuartilCompetition AS faixa_concorrencia,
               QuartilCPC AS faixa_cpc, QuartilNumTermos AS faixa_num_buscas
        FROM read_parquet('{raw}/padroes.parquet')
        WHERE padrao NOT LIKE '%??%'
    """)
    con.execute(f"COPY (SELECT *, regexp_matches(lower(concat_ws(' ', padrao, busca_lider, exemplo1, exemplo2)), '{ADULT}') AS adulto FROM pd ORDER BY mercado, volume_total DESC) "
                f"TO '{(kag / 'padroes.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")

    con.execute(f"""COPY (SELECT id, palavra, volume, concorrencia, cpc, fonte, id_padrao FROM kw
                          WHERE mercado = 'BR' AND regexp_matches(lower(palavra), '{QUESTION}')
                            AND NOT regexp_matches(lower(palavra), '{ADULT}')
                          ORDER BY volume DESC NULLS LAST)
                    TO '{(kag / 'perguntas.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")

    # patterns of every algorithm (nlp_padroes.padroes_agrupado) and their pattern -> search pairs
    alg = a.raw / "padroes_algoritmos.parquet"
    if alg.exists():
        con.execute(f"""
            CREATE TEMP TABLE pa AS
            SELECT id, trim(regexp_replace(padrao, '''+', '''', 'g')) AS padrao, lower(tipo) AS algoritmo,
                   quantidade AS num_buscas, volume AS volume_total,
                   round(CASE WHEN competition > 1 THEN competition / 100 ELSE competition END, 4) AS concorrencia_media,
                   cpc AS cpc_medio,
                   trim(regexp_replace(trim(regexp_replace(filho, '''+', '''', 'g'), ''''), '\\s*\\([0-9.]+\\)\\s*$', ''), '''') AS busca_lider,
                   NumPalavras AS num_palavras,
                   QuartilVolume AS faixa_volume, QuartilCompetition AS faixa_concorrencia,
                   QuartilCPC AS faixa_cpc, QuartilNumTermos AS faixa_num_buscas,
                   NULLIF(array_to_string(list_sort(list_distinct(list_filter(list_transform(string_split(coalesce(uso, ''), ','), x -> CASE trim(x) WHEN 'Concuros' THEN 'Concurso Público' ELSE trim(x) END), x -> x <> ''))), ', '), '') AS rotulos_uso, NULLIF(trim(uso_obs), '') AS obs_uso,
                   NULLIF(trim(visto), '') AS visto,
                   NULLIF(trim(padrao_pai), '') AS padrao_pai, NULLIF(trim(padrao_pai_nivel), '') AS padrao_pai_nivel,
                   contains(padrao, '[') AS tem_entidade
            FROM read_parquet('{alg.as_posix()}')
            WHERE padrao NOT LIKE '%??%'
        """)
        con.execute(f"COPY (SELECT *, regexp_matches(lower(concat_ws(' ', padrao, busca_lider)), '{ADULT}') AS adulto FROM pa "
                    f"ORDER BY algoritmo, volume_total DESC) TO '{(kag / 'padroes_algoritmos.parquet').as_posix()}' "
                    "(FORMAT parquet, COMPRESSION zstd)")
    pairs = a.raw / "padroes_buscas"
    if pairs.exists() and any(pairs.glob("*.parquet")) and not a.skip_pairs:
        write_parts(con, f"""
            SELECT DISTINCT trim(regexp_replace(padrao, '''+', '''', 'g')) AS padrao, lower(tipo) AS algoritmo,
                   trim(regexp_replace(Keyword, '''+', '''', 'g')) AS palavra
            FROM read_parquet('{pairs.as_posix()}/*.parquet')
            WHERE padrao NOT LIKE '%??%' AND Keyword NOT LIKE '%??%'
            ORDER BY algoritmo, padrao""", kag, "padroes_buscas")

    # samples for GitHub: never adult, never the brands that asked removal (they stay in the full data)
    brands = r"\b(getech|sunglider|herval|incoterm|bel fix|umbro|pro-bass|r3p|thunderx3|aerocool|fortrek|highmed|[eé]dez|mundial records)\b"
    clean = f"NOT regexp_matches(lower(palavra), '{ADULT}') AND NOT regexp_matches(lower(palavra), '{brands}')"
    con.execute(f"""COPY (SELECT * EXCLUDE (r) FROM (SELECT id, palavra, mercado, fonte, volume, concorrencia, cpc, id_padrao,
                                 row_number() OVER (PARTITION BY mercado ORDER BY hash(id)) r FROM kw WHERE {clean})
                          WHERE r <= 2500 ORDER BY mercado, palavra)
                    TO '{(smp / 'palavras_chave_sample.csv').as_posix()}' (HEADER)""")
    con.execute(f"""COPY (SELECT * EXCLUDE (r) FROM (SELECT *, row_number() OVER (PARTITION BY mercado ORDER BY volume_total DESC) r
                                                   FROM pd WHERE NOT regexp_matches(lower(concat_ws(' ', padrao, busca_lider, exemplo1, exemplo2)), '{ADULT}')
                                                     AND NOT regexp_matches(lower(padrao), '{brands}'))
                          WHERE r <= 1000 ORDER BY mercado, volume_total DESC)
                    TO '{(smp / 'padroes_sample.csv').as_posix()}' (HEADER)""")

    if alg.exists():
        con.execute(f"""COPY (SELECT * EXCLUDE (r) FROM (
                              SELECT padrao, algoritmo, busca_lider, num_buscas, volume_total, concorrencia_media, cpc_medio,
                                     rotulos_uso, padrao_pai, tem_entidade,
                                     row_number() OVER (PARTITION BY algoritmo ORDER BY volume_total DESC) r
                              FROM pa WHERE NOT regexp_matches(lower(concat_ws(' ', padrao, busca_lider)), '{ADULT}')
                                AND NOT regexp_matches(lower(concat_ws(' ', padrao, busca_lider)), '{brands}'))
                          WHERE r <= 400 ORDER BY algoritmo, volume_total DESC)
                        TO '{(smp / 'padroes_algoritmos_sample.csv').as_posix()}' (HEADER)""")

    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
    stats = {
        "palavras_chave": n_kw,
        "linhas_brutas": q(f"SELECT count(*) FROM read_parquet('{raw}/keywords/*.parquet')")[0][0],
        "por_mercado": dict(q("SELECT mercado, count(*) FROM kw GROUP BY 1 ORDER BY 2 DESC")),
        "por_fonte": dict(q("SELECT fonte, count(*) FROM kw GROUP BY 1")),
        "com_volume": q("SELECT count(volume) FROM kw")[0][0],
        "volume_total": q("SELECT sum(volume) FROM kw")[0][0],
        "padroes": q("SELECT count(*) FROM pd")[0][0],
        "padroes_algoritmos": dict(q("SELECT algoritmo, count(*) FROM pa GROUP BY 1 ORDER BY 2 DESC")) if alg.exists() else None,
        "padroes_com_entidade": q("SELECT count(*) FROM pa WHERE tem_entidade")[0][0] if alg.exists() else None,
        "padroes_rotulados": q("SELECT count(*) FROM pa WHERE rotulos_uso IS NOT NULL")[0][0] if alg.exists() else None,
        "rotulos_uso_top": dict(q("SELECT trim(r), count(*) n FROM (SELECT unnest(string_split(rotulos_uso, ',')) r FROM pa) "
                                  "WHERE trim(r) <> '' GROUP BY 1 ORDER BY n DESC LIMIT 30")) if alg.exists() else None,
        "pares_padrao_busca": (q(f"SELECT count(*) FROM read_parquet('{kag.as_posix()}/padroes_buscas-*.parquet')")[0][0]
                               if any(kag.glob("padroes_buscas-*.parquet")) else None),
        "perguntas": q(f"SELECT count(*) FROM read_parquet('{(kag / 'perguntas.parquet').as_posix()}')")[0][0],
        "adulto": q(f"SELECT count(*) FROM kw WHERE regexp_matches(lower(palavra), '{ADULT}')")[0][0],
        "cpc_percentis_por_fonte_mercado": {f"{f}/{m}": [round(x, 2) for x in p] for f, m, p in q(
            "SELECT fonte, mercado, quantile_cont(cpc, [0.5, 0.9, 0.99]) FROM kw WHERE cpc > 0 GROUP BY ALL ORDER BY ALL")},
        "concorrencia_media_por_fonte": dict(q("SELECT fonte, round(avg(concorrencia), 4) FROM kw GROUP BY 1")),
    }
    (a.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
