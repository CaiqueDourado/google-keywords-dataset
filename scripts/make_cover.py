"""Cover image (EN and PT): the searches, the patterns and the curation labels, with real values.
Run: python scripts/make_cover.py"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, LINE, BG, CARD = "#111111", "#5c5c5c", "#d9dde3", "#fdfdfc", "#ffffff"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MONO = "DejaVu Sans Mono"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

FLOWS = [("previsão do tempo sp", "previsa temp [local]", "barbosa"),
         ("apartamentos para alugar em curitiba", "[imovel] par [local]", "rosa"),
         ("receita de bolo", "receit [comida]", "barbosa")]
T = {
    "": dict(title="Google Keywords",
             sub="{kw} searches · {pd} patterns · {pairs} pattern → search pairs · volume, CPC and competition",
             p1="Searches by market", p1s="{vol} searches a month in total", p2="Search → pattern", p2s="entities become [types]",
             p3="Curation labels", p3s="{lab} patterns labelled by hand",
             markets={"BR": "Brazil", "US": "United States", "ES": "Spain", "AR": "Argentina"}, mi="M",
             foot="google-keywords-dataset · the data behind SuperNichos.com"),
    ".pt-BR": dict(title="Palavras-chave do Google",
                   sub="{kw} buscas · {pd} padrões · {pairs} pares padrão → busca · volume, CPC e concorrência",
                   p1="Buscas por mercado", p1s="{vol} buscas por mês no total", p2="Busca → padrão", p2s="entidades viram [tipos]",
                   p3="Rótulos da curadoria", p3s="{lab} padrões rotulados à mão",
                   markets={"BR": "Brasil", "US": "Estados Unidos", "ES": "Espanha", "AR": "Argentina"}, mi="mi",
                   foot="google-keywords-dataset · os dados por trás do SuperNichos.com"),
}


def mil(n, pt, unit):
    s = f"{n / 1e6:.1f}"
    return (s.replace(".", ",") if pt else s) + f" {unit}"


def num(n, pt):
    s = f"{n:,}"
    return s.replace(",", ".") if pt else s


def panel(ax, x, w, color, title, sub):
    ax.add_patch(FancyBboxPatch((x, 6), w, 52, boxstyle="round,pad=0,rounding_size=1.4", fc=CARD, ec=LINE, lw=1.1))
    ax.add_patch(FancyBboxPatch((x, 57.2), w, 0.8, boxstyle="square,pad=0", fc=color, ec="none"))
    ax.text(x + 2, 53, title, fontsize=13, weight="bold", color=INK, va="center")
    ax.text(x + 2, 49.2, sub, fontsize=8.6, color=MUTED, va="center")


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    for suf, t in T.items():
        pt = bool(suf)
        fig = plt.figure(figsize=(12, 6.2), dpi=100)
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 74)
        ax.axis("off")
        ax.text(3, 69, t["title"], fontsize=21, weight="bold", color=INK, va="center")
        ax.text(3, 63.6, t["sub"].format(kw=mil(st["palavras_chave"], pt, t["mi"]), pd=mil(sum(st["padroes_algoritmos"].values()), pt, t["mi"]),
                                         pairs=mil(st["pares_padrao_busca"], pt, t["mi"])), fontsize=10.5, color=MUTED, va="center")

        x1, w = 3, 33
        bi = f"{st['volume_total'] / 1e9:.0f}" + (" bi" if pt else " B")
        panel(ax, x1, w, BLUE, t["p1"], t["p1s"].format(vol=bi))
        mk = st["por_mercado"]
        mx = max(mk.values())
        for i, (k, v) in enumerate(mk.items()):
            y = 41 - i * 8
            ax.text(x1 + 2, y + 2.2, t["markets"][k], fontsize=9, color=INK, va="center")
            bw = max(0.6, 20 * v / mx)
            ax.add_patch(FancyBboxPatch((x1 + 2, y - 2.2), bw, 2.6, boxstyle="square,pad=0", fc=BLUE, ec="none"))
            ax.text(x1 + 2.8 + bw, y - 0.9, mil(v, pt, t["mi"]), fontsize=8.6, color=MUTED, va="center")

        x2 = x1 + w + 2.5
        w2 = 42
        panel(ax, x2, w2, AQUA, t["p2"], t["p2s"])
        for i, (search, pattern, alg) in enumerate(FLOWS):
            y = 40 - i * 11.5
            ax.text(x2 + 2, y + 1.6, search, fontsize=9.2, color=INK, va="center", family=MONO)
            ax.text(x2 + 2, y - 2.6, "→ " + pattern, fontsize=9.6, color=AQUA, va="center", family=MONO, weight="bold")
            ax.text(x2 + w2 - 2, y - 2.6, alg, fontsize=8, color=MUTED, va="center", ha="right")

        x3 = x2 + w2 + 2.5
        w3 = 117 - x3
        panel(ax, x3, w3, ORANGE, t["p3"], t["p3s"].format(lab=num(st["padroes_rotulados"], pt)))
        labs = list(st["rotulos_uso_top"].items())[:6]
        lm = labs[0][1]
        for i, (k, v) in enumerate(labs):
            y = 42 - i * 6.2
            ax.text(x3 + 2, y + 1.4, k, fontsize=8.8, color=INK, va="center")
            bw = max(0.6, 16 * v / lm)
            ax.add_patch(FancyBboxPatch((x3 + 2, y - 2.1), bw, 1.9, boxstyle="square,pad=0", fc=ORANGE, ec="none"))
            ax.text(x3 + 2.8 + bw, y - 1.15, num(v, pt), fontsize=8, color=MUTED, va="center")

        ax.text(3, 2.6, t["foot"], fontsize=8.4, color=MUTED)
        ax.text(117, 2.6, "github.com/CaiqueDourado", fontsize=8.4, color=MUTED, ha="right")
        fig.savefig(out / f"cover{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
