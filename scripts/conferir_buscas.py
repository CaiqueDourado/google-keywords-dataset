"""Checks on the exported Parquet (exportar_supernichos.py), with DuckDB, without touching SQL Server: what 'ar'
and tipo 'N1' are, the competition scale, what a zero volume means, duplicates, personal data, brands that
asked removal and adult terms.

    python conferir_buscas.py --data D:\\buscas_raw --out D:\\buscas_conferencia.txt

Personal data is only COUNTED; examples are printed masked. Needs duckdb.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import duckdb

REMOVED_BRANDS = ["getech", "sunglider", "herval", "incoterm", "bel fix", "umbro", "aurora", "pro-bass", "r3p",
                  "thunderx3", "aerocool", "fortrek", "highmed", "édez", "edez", "mundial records"]
ADULT = ["porn", "xvideos", "xxx", "sexo", "puta", "nude", "nua"]
PII = {
    "email": r"[\w.+-]+@[\w-]+\.[a-z]{2,}",
    "11+ digits (CPF/phone)": r"\d{11,}",
    "CPF 000.000.000-00": r"\d{3}\.\d{3}\.\d{3}-\d{2}",
    "phone (00) 0000-0000": r"\(\d{2}\)\s?\d{4,5}-?\d{4}",
}


def mask(text: str) -> str:
    return re.sub(r"\d[\d.\- ()]{5,}\d", lambda m: re.sub(r"\d", "#", m.group()), re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("buscas_conferencia.txt"))
    a = ap.parse_args()
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"CREATE VIEW k AS SELECT * FROM read_parquet('{(a.data / 'keywords' / '*.parquet').as_posix()}')")
    con.execute(f"CREATE VIEW p AS SELECT * FROM read_parquet('{(a.data / 'padroes.parquet').as_posix()}')")
    q = lambda sql, *args: con.execute(sql, list(args)).fetchall()  # noqa: E731

    with open(a.out, "w", encoding="utf-8") as out:
        def section(t):
            print(f"\n## {t}", file=out)
            print(t, flush=True)

        section("idioma: rows, volume>0, and 8 random searches with volume")
        for lang, n, nv in q("SELECT idioma, count(*), count(*) FILTER (Volume > 0) FROM k GROUP BY 1 ORDER BY 2 DESC"):
            ex = q("SELECT Keyword, Volume FROM k WHERE idioma IS NOT DISTINCT FROM ? AND Volume > 0 ORDER BY random() LIMIT 8", lang)
            print(f"{lang}: {n:,} rows, {nv:,} with volume · " + " · ".join(f"{mask(w)} ({v})" for w, v in ex), file=out)

        section("tipo (N1 vs empty): id range, idioma, volume, examples")
        for t, n, lo, hi, avg, z in q("SELECT tipo, count(*), min(id), max(id), avg(Volume), count(*) FILTER (Volume = 0) "
                                      "FROM k GROUP BY 1"):
            langs = q("SELECT idioma, count(*) FROM k WHERE tipo IS NOT DISTINCT FROM ? GROUP BY 1 ORDER BY 2 DESC", t)
            ex = q("SELECT Keyword, Volume, Competition, CPC FROM k WHERE tipo IS NOT DISTINCT FROM ? ORDER BY random() LIMIT 6", t)
            print(f"{t}: {n:,} rows, ids {lo:,}–{hi:,}, avg volume {avg:.0f}, zero volume {z:,}; "
                  + ", ".join(f"{l}={c:,}" for l, c in langs), file=out)
            print("  " + " · ".join(f"{mask(w)} ({v}, {c}, {p_})" for w, v, c, p_ in ex), file=out)

        section("competition scale (by tipo)")
        for b, t, n in q("""SELECT CASE WHEN Competition = 0 THEN '0' WHEN Competition < 1 THEN '0–1 fraction'
                                       WHEN Competition = floor(Competition) THEN '1–99 integer' ELSE '1–99 decimals' END b,
                                  tipo, count(*) FROM k GROUP BY ALL ORDER BY 1, 2"""):
            print(f"{b:<15} tipo={t}: {n:,}", file=out)

        section("zero volume: with competition or CPC? (yes = 0 means unknown)")
        r = q("SELECT count(*) FILTER (Competition > 0 OR CPC > 0), count(*) FROM k WHERE Volume = 0")[0]
        print(f"volume 0 with competition or CPC > 0: {r[0]:,} of {r[1]:,}", file=out)
        print("most common volumes: " + ", ".join(f"{v}={n:,}" for v, n in
              q("SELECT Volume, count(*) n FROM k WHERE Volume > 0 GROUP BY 1 ORDER BY n DESC LIMIT 12")), file=out)

        section("CPC: highest values (currency unknown)")
        print(" · ".join(f"{mask(w)} ({c}, {i})" for w, c, i in q("SELECT Keyword, CPC, idioma FROM k ORDER BY CPC DESC LIMIT 10")),
              file=out)
        print("CPC percentiles 50/90/99/99.9: " + str(q("SELECT quantile_cont(CPC, [0.5, 0.9, 0.99, 0.999]) FROM k WHERE CPC > 0")[0][0]),
              file=out)

        section("duplicates")
        r = q("SELECT count(*), count(DISTINCT (idioma, lower(trim(Keyword)))) FROM k")[0]
        print(f"rows {r[0]:,} · distinct (idioma, lower keyword) {r[1]:,}", file=out)
        damaged = q("SELECT count(*) FROM k WHERE Keyword LIKE '%??%'")[0][0]
        apos = q("SELECT count(*) FROM k WHERE Keyword LIKE '%''''%'")[0][0]
        print(f"'?' damaged: {damaged:,} · quadrupled apostrophes: {apos:,}", file=out)

        section("personal data (counts; examples masked)")
        for name, rx in PII.items():
            n = q("SELECT count(*) FROM k WHERE regexp_matches(Keyword, ?)", rx)[0][0]
            ex = q("SELECT Keyword FROM k WHERE regexp_matches(Keyword, ?) LIMIT 3", rx)
            print(f"{name}: {n:,}  e.g. " + " · ".join(mask(w) for (w,) in ex), file=out)

        section("brands that asked removal (keywords / padroes)")
        for b in REMOVED_BRANDS:
            rx = rf"\b{re.escape(b)}\b"
            n = q("SELECT count(*) FROM k WHERE regexp_matches(lower(Keyword), ?)", rx)[0][0]
            m = q("SELECT count(*) FROM p WHERE regexp_matches(lower(padrao), ?)", rx)[0][0]
            print(f"{b}: {n:,} / {m:,}", file=out)

        section("adult terms (counts only)")
        for w in ADULT:
            n = q("SELECT count(*) FROM k WHERE regexp_matches(lower(Keyword), ?)", r"\b" + w)[0][0]
            print(f"{w}: {n:,}", file=out)

        section("padroes: tipo, and keywords without a pattern")
        print(" · ".join(f"{t}: {n:,} (ids {lo:,}–{hi:,})" for t, n, lo, hi in
                         q("SELECT tipo, count(*), min(id), max(id) FROM p GROUP BY 1")), file=out)
        print(f"keywords whose idPadrao is not in padroes: "
              f"{q('SELECT count(*) FROM k ANTI JOIN p ON p.id = k.idPadrao')[0][0]:,}", file=out)
    print(f"{time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
