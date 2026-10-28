"""One pattern as nested JSON: the pattern, its totals and curation labels, and the searches it groups with their
volume, CPC and competition. Reads the Kaggle files.

    python scripts/make_json.py --data D:\\buscas_out\\kaggle --padrao "previsa temp [local]" --algoritmo barbosa
    python scripts/make_json.py --data D:\\buscas_out\\kaggle --list            # labelled patterns with entities to choose from

Writes docs/example-pattern.json (or --out). Needs duckdb.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SEARCHES = 15  # searches listed, highest volume first


def clean(v):
    if isinstance(v, float):
        return None if v != v else (int(v) if v.is_integer() else round(v, 4))
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--padrao")
    ap.add_argument("--algoritmo", default="barbosa")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "example-pattern.json")
    a = ap.parse_args()
    d = a.data.as_posix()
    con = duckdb.connect()
    con.execute(f"CREATE VIEW pa AS SELECT * FROM read_parquet('{d}/padroes_algoritmos.parquet')")
    if a.list:
        print(con.execute("""SELECT algoritmo, padrao, busca_lider, num_buscas, volume_total, rotulos_uso FROM pa
                             WHERE tem_entidade AND rotulos_uso IS NOT NULL AND NOT adulto AND num_buscas BETWEEN 15 AND 400
                             ORDER BY volume_total DESC LIMIT 40""").df().to_string(index=False, max_colwidth=50))
        return
    p = con.execute("SELECT * FROM pa WHERE padrao = ? AND algoritmo = ?", [a.padrao, a.algoritmo]).fetchdf()
    if p.empty:
        raise SystemExit(f"pattern {a.padrao!r} ({a.algoritmo}) not found; try --list")
    rec = {k: clean(v) for k, v in p.iloc[0].to_dict().items()}
    rows = con.execute(f"""
        SELECT k.palavra, k.mercado, k.fonte, k.volume, k.concorrencia, k.cpc
        FROM read_parquet('{d}/padroes_buscas-*.parquet') b
        JOIN read_parquet('{d}/palavras_chave-*.parquet') k ON lower(k.palavra) = lower(b.palavra) AND k.mercado = 'BR'
        WHERE b.padrao = ? AND b.algoritmo = ? AND NOT k.adulto
        ORDER BY k.volume DESC NULLS LAST LIMIT {SEARCHES}""", [a.padrao, a.algoritmo]).fetchall()
    out = {
        "padrao": rec["padrao"], "algoritmo": rec["algoritmo"], "padrao_pai": rec.get("padrao_pai"),
        "busca_lider": rec["busca_lider"],
        "totais": {k: rec[k] for k in ("num_buscas", "volume_total", "concorrencia_media", "cpc_medio")},
        "faixas_1_a_20": {k.replace("faixa_", ""): rec[k] for k in ("faixa_volume", "faixa_concorrencia", "faixa_cpc", "faixa_num_buscas")},
        "rotulos_uso": [x.strip() for x in (rec.get("rotulos_uso") or "").split(",") if x.strip()],
        "buscas": [{"palavra": w, "mercado": m, "fonte": f, "volume": clean(v), "concorrencia": clean(c), "cpc": clean(cp)}
                   for w, m, f, v, c, cp in rows],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} searches -> {a.out}")


if __name__ == "__main__":
    main()
