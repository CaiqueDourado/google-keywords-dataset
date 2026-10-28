"""Figures for the README and Kaggle, EN and PT, from data/stats.json. Run: python scripts/make_figures.py"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
INK, MUTED, GRID, BG = "#111111", "#5c5c5c", "#e6e8eb", "#fdfdfc"
BLUE, ORANGE = "#2a78d6", "#eb6834"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

# one real pattern per algorithm, from sample/padroes_algoritmos_sample.csv
EXAMPLES = {
    "viana": ("previsa temp", "previsão do tempo"),
    "barbosa": ("receit [comida]", "receita de bolo"),
    "rosa": ("[imovel] par [local]", "apartamentos para alugar em curitiba"),
    "vilela": ("nacional ensin medi", "exame nacional do ensino médio"),
    "figueredo": ("[-bebes] [marca]", "fraldas huggies"),
}
T = {
    "": dict(
        alg_t="Patterns found by each algorithm", alg_s="1.73 million patterns; the example is a real pattern and its leading search",
        alg_how={"viana": "prefixes of 2–5 words", "barbosa": "entities, then prefixes", "rosa": "entities, then skipped words",
                 "vilela": "runs of words", "figueredo": "entities, then runs of words"},
        lab_t="What each pattern was good for", lab_s="Labels given by hand while choosing niches: patterns per label (154,654 labelled)",
        cpc_t="CPC is on two different scales", cpc_s="Cost per click by source and market: dot = median, line = up to the 90th percentile, tick = 99th; log scale",
        cpc_x="CPC as recorded by the tool (DataForSEO in US$; Ubersuggest 2018 unit unknown)",
        src="Source: google-keywords-dataset (SuperNichos)"),
    ".pt-BR": dict(
        alg_t="Padrões encontrados por algoritmo", alg_s="1,73 milhão de padrões; o exemplo é um padrão real e a busca que o lidera",
        alg_how={"viana": "prefixos de 2–5 palavras", "barbosa": "entidades, depois prefixos", "rosa": "entidades, depois palavras saltadas",
                 "vilela": "sequências de palavras", "figueredo": "entidades, depois sequências"},
        lab_t="Para que servia cada padrão", lab_s="Rótulos dados à mão na escolha de nichos: padrões por rótulo (154.654 rotulados)",
        cpc_t="O CPC está em duas escalas", cpc_s="Custo por clique por fonte e mercado: ponto = mediana, linha = até o percentil 90, traço = 99; escala log",
        cpc_x="CPC como gravado pela ferramenta (DataForSEO em US$; unidade do Ubersuggest 2018 desconhecida)",
        src="Fonte: google-keywords-dataset (SuperNichos)"),
}


def style(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def head(fig, t, s, src):
    fig.text(0.02, 0.965, t, fontsize=16, weight="bold", color=INK, va="top")
    fig.text(0.02, 0.905, s, fontsize=10, color=MUTED, va="top")
    fig.text(0.02, 0.015, src, fontsize=8, color=MUTED)


def num(n, pt):
    s = f"{n:,}"
    return s.replace(",", ".") if pt else s


def algorithms(st, t, suf):
    pt = bool(suf)
    d = sorted(st["padroes_algoritmos"].items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=110)
    fig.patch.set_facecolor(BG)
    fig.subplots_adjust(left=0.31, right=0.97, top=0.8, bottom=0.08)
    mx = max(v for _, v in d)
    for i, (k, v) in enumerate(d):
        ax.barh(i, v, color=BLUE, height=0.62)
        ax.text(v + mx * 0.01, i + 0.13, num(v, pt), va="center", fontsize=9.5, color=INK, weight="bold")
        pat, lead = EXAMPLES[k]
        ax.text(v + mx * 0.01, i - 0.2, f"{pat}  ←  {lead}", va="center", fontsize=8.5, color=MUTED, family="DejaVu Sans Mono")
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([f"{k.capitalize()}\n{t['alg_how'][k]}" for k, _ in d], fontsize=9.5, color=INK)
    ax.set_xlim(0, mx * 1.75)
    ax.set_xticks([])
    style(ax)
    ax.spines["bottom"].set_visible(False)
    head(fig, t["alg_t"], t["alg_s"], t["src"])
    fig.savefig(OUT / f"algorithms{suf}.png", facecolor=BG)
    plt.close(fig)


def labels(st, t, suf):
    pt = bool(suf)
    d = list(st["rotulos_uso_top"].items())[:20][::-1]
    fig, ax = plt.subplots(figsize=(9, 7.2), dpi=110)
    fig.patch.set_facecolor(BG)
    fig.subplots_adjust(left=0.24, right=0.93, top=0.86, bottom=0.07)
    mx = max(v for _, v in d)
    ax.barh(range(len(d)), [v for _, v in d], color=BLUE, height=0.68)
    for i, (_, v) in enumerate(d):
        ax.text(v + mx * 0.01, i, num(v, pt), va="center", fontsize=8.5, color=MUTED)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([k for k, _ in d], fontsize=9.5, color=INK)
    ax.set_xlim(0, mx * 1.12)
    ax.set_xticks([])
    style(ax)
    ax.spines["bottom"].set_visible(False)
    head(fig, t["lab_t"], t["lab_s"], t["src"])
    fig.savefig(OUT / f"labels{suf}.png", facecolor=BG)
    plt.close(fig)


def cpc(st, t, suf):
    d = st["cpc_percentis_por_fonte_mercado"]
    order = ["dataforseo/AR", "dataforseo/BR", "dataforseo/ES", "dataforseo/US", "ubersuggest_2018/BR"][::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=110)
    fig.patch.set_facecolor(BG)
    fig.subplots_adjust(left=0.26, right=0.95, top=0.78, bottom=0.2)
    for i, k in enumerate(order):
        p50, p90, p99 = d[k]
        c = ORANGE if k.startswith("uber") else BLUE
        ax.plot([p50, p90], [i, i], color=c, linewidth=2.5, solid_capstyle="round")
        ax.plot([p99], [i], marker="|", markersize=12, color=c, markeredgewidth=2)
        ax.plot([p50], [i], marker="o", markersize=8, color=c, markeredgecolor=BG, markeredgewidth=1.5)
        lab = f"{p50:g} · {p90:g} · {p99:g}"
        ax.text(p99 * 1.12, i, lab.replace(".", ",") if suf else lab, va="center", fontsize=8.5, color=MUTED)
    names = {"dataforseo/AR": "DataForSEO · Argentina", "dataforseo/BR": "DataForSEO · Brasil",
             "dataforseo/ES": "DataForSEO · España", "dataforseo/US": "DataForSEO · US",
             "ubersuggest_2018/BR": "Ubersuggest 2018 · Brasil"}
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([names[k] for k in order], fontsize=9.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(0.03, 600)
    ax.set_xticks([0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500])
    ax.set_xticklabels([("{:g}".format(v)).replace(".", "," if suf else ".") for v in [0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500]])
    ax.minorticks_off()
    ax.set_xlabel(t["cpc_x"], fontsize=8.5, color=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    style(ax)
    head(fig, t["cpc_t"], t["cpc_s"], t["src"])
    fig.savefig(OUT / f"cpc{suf}.png", facecolor=BG)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    for suf, t in T.items():
        algorithms(st, t, suf)
        labels(st, t, suf)
        cpc(st, t, suf)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
