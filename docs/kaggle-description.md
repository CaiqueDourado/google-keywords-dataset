**Google Keywords**: a free keyword research dataset, Brazilian Portuguese first, plus the US, Spain and Argentina. **37,961,526 search queries** with **monthly search volume, CPC and competition**, grouped into **1.73 million search patterns** by five pattern-mining algorithms, with **137,974,529 pattern → search pairs** and **154,654 patterns labelled by hand** with what they were good for (AdSense, affiliates, products, apps…).

It is the data behind [SuperNichos.com](https://supernichos.com), a niche-discovery tool, and behind the choice of the ~80 programmatic SEO sites the author built from 2017 on.

| Market | Searches | Share | Source | Patterns and labels |
|---|---:|---:|---|---|
| Brazil (BR) | 33,289,393 | 88% | Ubersuggest 2018 + DataForSEO | yes |
| United States (US) | 2,005,560 | 5% | DataForSEO | prefix patterns only |
| Spain (ES) | 1,434,325 | 4% | DataForSEO | prefix patterns only |
| Argentina (AR) | 1,232,248 | 3% | DataForSEO | prefix patterns only |

## How a pattern is structured

![One pattern in JSON](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/pattern-json.png)

`com faz [comida]` is *como fazer + a food*: 98,097 searches, 12.1 million searches a month, labelled for AdSense, affiliates, how-to and recipes.

## Files

- `palavras_chave-*.parquet`: one search per row: `palavra`, `mercado` (BR, US, ES, AR), `fonte` (ubersuggest_2018, dataforseo), `volume`, `concorrencia` (0–1), `cpc`, `id_padrao`, `num_palavras`, `adulto`.
- `padroes.parquet`: 2,040,760 prefix patterns used by SuperNichos (`previsa temp` → *previsão do tempo*), with searches, total volume, leading search, examples and 1–20 bands.
- `padroes_algoritmos.parquet`: 1,731,236 patterns of the five algorithms, with entities (`[cidade]`, `[marca]`…), curation labels (`rotulos_uso`), the generalized parent pattern and 1–20 bands.
- `padroes_buscas-*.parquet`: which searches each pattern groups, per algorithm.
- `perguntas.parquet`: 4,053,470 Brazilian searches phrased as questions (como, qual, onde, quando, quanto, por que, melhor, vale a pena…).
- `stats.json`: totals.

## What the data shows

![Patterns found by each algorithm](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/algorithms.png)

![What each pattern was good for](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/labels.png)

![CPC by source and market](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/cpc.png)

The two sources did not record CPC on the same scale: DataForSEO looks like US dollars; the 2018 Ubersuggest unit is not known. Compare CPC only within one `fonte`.

## The site this comes from

![SuperNichos.com](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/supernichos.com_screenshot.png)

## How it was made

![Method](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/flow.png)

Batch 1 (Brazil only) came from Ubersuggest in 2018, which served Google Keyword Planner metrics; batch 2 (four markets) from DataForSEO. A zero volume became empty (in batch 1, 0 meant "no metric"); competition on a 0–100 scale was divided by 100; doubled apostrophes were fixed; searches damaged into `??` were removed; duplicates were collapsed from 54.95 million rows to 37.96 million. Adult searches (39,496) are kept and flagged in `adulto`. Metrics are a snapshot of when they were collected.

![Google Keywords](https://raw.githubusercontent.com/CaiqueDourado/google-keywords-dataset/main/docs/img/cover.png)

Scripts, method, limits and the study in Portuguese and English: **https://github.com/CaiqueDourado/google-keywords-dataset**

The seven pattern algorithms are available as a library, in Python and .NET, with a 2019 mode that reproduces these patterns: **https://github.com/CaiqueDourado/search-pattern-miner**

The entity dictionary behind the `[tipo]` patterns, cleaned (307 thousand entities with their types): **https://www.kaggle.com/datasets/caiquedourado/portuguese-entity-gazetteer**

## License

Compilation, patterns, labels and derived columns: CC BY 4.0. The search metrics were recorded from Ubersuggest (2018) and DataForSEO; check those providers' terms before commercial use of the metrics. Version 1.0.0. Author: Caique Dourado.
