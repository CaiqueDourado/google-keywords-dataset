"""Checks run in CI on sample/ and data/stats.json. Run: python scripts/validate.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "sample"
ADULT = r"\b(porn\w*|xvideos?|xxx+|sexo|puta\w*|nudes?|nuas?|pelad[ao]s?|safad[ao]s?|sex|desnud\w*)\b"
BRANDS = r"\b(getech|sunglider|herval|incoterm|bel fix|umbro|pro-bass|r3p|thunderx3|aerocool|fortrek|highmed|[eé]dez|mundial records)\b"
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        errors.append(msg)


def one(sql: str):
    return duckdb.sql(sql).fetchall()[0][0]


kw, pd, pa = (S / "palavras_chave_sample.csv").as_posix(), (S / "padroes_sample.csv").as_posix(), (S / "padroes_algoritmos_sample.csv").as_posix()
st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))

check(set(r[0] for r in duckdb.sql(f"SELECT DISTINCT mercado FROM '{kw}'").fetchall()) == {"BR", "US", "ES", "AR"}, "searches: four markets")
check(set(r[0] for r in duckdb.sql(f"SELECT DISTINCT fonte FROM '{kw}'").fetchall()) <= {"ubersuggest_2018", "dataforseo"}, "searches: known sources")
check(one(f"SELECT count(*) FROM '{kw}' WHERE volume <= 0") == 0, "searches: no zero volume (zero = empty)")
check(one(f"SELECT count(*) FROM '{kw}' WHERE concorrencia < 0 OR concorrencia > 1") == 0, "searches: competition within 0-1")
check(one(f"SELECT count(*) FROM '{kw}' WHERE palavra LIKE '%??%' OR palavra LIKE '%''''%'") == 0, 'searches: no "??" and no doubled apostrophes')
check(one(f"SELECT count(*) - count(DISTINCT (mercado, lower(palavra))) FROM '{kw}'") == 0, "searches: no duplicates")
for name, f, col in (("searches", kw, "palavra"), ("prefix patterns", pd, "concat_ws(' ', padrao, busca_lider)"),
                     ("algorithm patterns", pa, "concat_ws(' ', padrao, busca_lider)")):
    check(one(f"SELECT count(*) FROM '{f}' WHERE regexp_matches(lower({col}), '{ADULT}')") == 0, f"{name} sample: no adult terms")
    check(one(f"SELECT count(*) FROM '{f}' WHERE regexp_matches(lower({col}), '{BRANDS}')") == 0, f"{name} sample: no brands that asked removal")
check(one(f"SELECT count(*) FROM '{kw}' WHERE regexp_matches(palavra, '[\\w.+-]+@[\\w-]+\\.[a-z]{{2,}}')") == 0, "searches sample: no e-mails")
check(set(r[0] for r in duckdb.sql(f"SELECT DISTINCT algoritmo FROM '{pa}'").fetchall())
      == {"viana", "vilela", "barbosa", "figueredo", "rosa"}, "algorithm patterns: five algorithms")
check(one(f"SELECT count(*) FROM '{pa}' WHERE tem_entidade <> contains(padrao, '[')") == 0, "algorithm patterns: tem_entidade matches '['")
check(one(f"SELECT count(*) FROM '{pa}' WHERE rotulos_uso LIKE '%Concuros%'") == 0, "algorithm patterns: label typo fixed")
check(sum(st["por_mercado"].values()) == st["palavras_chave"], "stats: markets add up to the searches")
check(sum(st["por_fonte"].values()) == st["palavras_chave"], "stats: sources add up to the searches")
check(st["padroes_com_entidade"] <= sum(st["padroes_algoritmos"].values()), "stats: entity patterns within all patterns")

print(f"\n{len(errors)} failure(s)")
sys.exit(1 if errors else 0)
