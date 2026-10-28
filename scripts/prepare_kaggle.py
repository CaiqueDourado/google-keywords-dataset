"""Get the Kaggle folder ready to upload: flat file names (Kaggle keeps no subfolders), stats.json and
dataset-metadata.json with the description and every file's columns.

    python scripts/prepare_kaggle.py --kaggle D:\\buscas_out\\kaggle
    kaggle datasets create -p D:\\buscas_out\\kaggle          # first time
    kaggle datasets version -p D:\\buscas_out\\kaggle -m "…"   # later versions

Moves palavras_chave/part-0000.parquet to palavras_chave-0000.parquet (older build output); nothing is copied.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S, I, F, B = "string", "integer", "number", "boolean"
COLS = {
    "palavras_chave": ("One search per row: market, source, volume, CPC and competition.", [
        ("id", I, "Row id in the source table"), ("palavra", S, "The search, as typed"),
        ("mercado", S, "Market of the keyword tool: BR, US, ES (Spain), AR (Argentina)"),
        ("fonte", S, "ubersuggest_2018 (Keyword Planner metrics via Ubersuggest) or dataforseo"),
        ("volume", I, "Monthly searches; empty when the tool had no number"),
        ("concorrencia", F, "Advertiser competition, 0 to 1"),
        ("cpc", F, "Cost per click as recorded (DataForSEO ~US$; Ubersuggest 2018 unit unknown)"),
        ("id_padrao", I, "Prefix pattern in padroes.parquet"), ("num_palavras", I, "Words in the search"),
        ("adulto", B, "Search with explicit adult terms")]),
    "padroes": ("Prefix patterns of 2-5 stemmed words, as in SuperNichos.com.", [
        ("id", I, "Pattern id (palavras_chave.id_padrao)"), ("padrao", S, "Pattern, stemmed words"),
        ("mercado", S, "BR, US, ES, AR"), ("fonte", S, "ubersuggest_2018 or dataforseo"),
        ("num_buscas", I, "Searches in the pattern"), ("volume_total", I, "Sum of monthly volume"),
        ("concorrencia_media", F, "Mean competition, 0 to 1"), ("cpc_medio", F, "Mean CPC"),
        ("busca_lider", S, "Search with the most volume"), ("exemplo1", S, "Example search"),
        ("exemplo2", S, "Example search"), ("num_palavras", I, "Words in the pattern"),
        ("faixa_volume", I, "Volume band 1-20 (NTILE)"), ("faixa_concorrencia", I, "Competition band 1-20"),
        ("faixa_cpc", I, "CPC band 1-20"), ("faixa_num_buscas", I, "Number-of-searches band 1-20"),
        ("adulto", B, "Pattern or examples with explicit adult terms")]),
    "padroes_algoritmos": ("Patterns of five algorithms, with entities and the author's curation labels.", [
        ("id", I, "Pattern id"), ("padrao", S, "Pattern; [type] = an entity replaced by its type"),
        ("algoritmo", S, "viana, vilela, barbosa, figueredo or rosa"),
        ("num_buscas", I, "Searches in the pattern"), ("volume_total", I, "Sum of monthly volume"),
        ("concorrencia_media", F, "Mean competition, 0 to 1"), ("cpc_medio", F, "Mean CPC"),
        ("busca_lider", S, "Search with the most volume"), ("num_palavras", I, "Words in the pattern"),
        ("faixa_volume", I, "Volume band 1-20"), ("faixa_concorrencia", I, "Competition band 1-20"),
        ("faixa_cpc", I, "CPC band 1-20"), ("faixa_num_buscas", I, "Number-of-searches band 1-20"),
        ("rotulos_uso", S, "Curation labels, comma separated (AdSense, Afiliados, Produtos…)"),
        ("obs_uso", S, "Curation note"), ("visto", S, "Marked as seen during curation"),
        ("padrao_pai", S, "More general parent pattern"), ("padrao_pai_nivel", S, "Level of the parent pattern"),
        ("tem_entidade", B, "Pattern has at least one [entity]"), ("adulto", B, "Explicit adult terms")]),
    "padroes_buscas": ("Which searches each pattern groups, per algorithm.", [
        ("padrao", S, "Pattern (padroes_algoritmos.padrao)"), ("algoritmo", S, "Algorithm"),
        ("palavra", S, "Search (palavras_chave.palavra)")]),
    "perguntas": ("Brazilian searches phrased as questions, without adult terms.", [
        ("id", I, "Row id (palavras_chave.id)"), ("palavra", S, "The question"), ("volume", I, "Monthly searches"),
        ("concorrencia", F, "Competition, 0 to 1"), ("cpc", F, "CPC"), ("fonte", S, "Source"),
        ("id_padrao", I, "Prefix pattern")]),
}


def flatten(k: Path) -> None:
    for prefix in ("palavras_chave", "padroes_buscas"):
        sub = k / prefix
        if sub.is_dir():
            for f in sorted(sub.glob("part-*.parquet")):
                f.replace(k / f"{prefix}-{f.stem.split('-')[1]}.parquet")
            if not any(sub.iterdir()):
                sub.rmdir()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, required=True)
    a = ap.parse_args()
    k = a.kaggle
    flatten(k)
    stats = k.parent / "stats.json"
    if stats.exists():
        shutil.copy(stats, k / "stats.json")
    resources = []
    for f in sorted(k.glob("*.parquet")):
        key = f.stem.split("-")[0]
        desc, fields = COLS[key]
        part = f" Part {int(f.stem.split('-')[1]) + 1}." if "-" in f.stem else ""
        resources.append({"path": f.name, "description": desc + part,
                          "schema": {"fields": [{"name": n, "type": t, "description": d} for n, t, d in fields]}})
    resources.append({"path": "stats.json", "description": "Totals used in the README."})
    meta = {
        "title": "Google Keywords: 38M searches with volume & CPC",
        "subtitle": "Search volume, CPC and search patterns for Brazil, US, Spain and Argentina",
        "id": "caiquedourado/google-keywords-dataset",
        "licenses": [{"name": "Attribution 4.0 International (CC BY 4.0)"}],
        "keywords": ["internet", "marketing", "nlp", "text"],
        "description": (ROOT / "docs" / "kaggle-description.md").read_text(encoding="utf-8"),
        "isPrivate": False,
        "resources": resources,
    }
    (k / "dataset-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    copy = ROOT / "kaggle" / "dataset-metadata.json"
    copy.parent.mkdir(exist_ok=True)
    copy.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")  # the repo keeps a copy
    print(f"{len(resources)} files described -> {k / 'dataset-metadata.json'}")
    print(f"title {len(meta['title'])} chars · subtitle {len(meta['subtitle'])} chars")


if __name__ == "__main__":
    main()
