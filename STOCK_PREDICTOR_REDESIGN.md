# Stock Predictor Platform Redesign

Research date: 2026-05-07

This document supersedes the older aspirational plan in `PROJECT_PLAN.md` for the next build pass. The current app is a useful FastAPI demo shell, but the predictor itself is still mostly mock data plus rule-based technical scoring. The redesigned product should become a source-aware research platform: collect durable market, fundamental, macro, and event data; build features only from information available at the time; backtest honestly; and explain every signal with the facts and news that support it.

Important framing: this should be built as decision support and research tooling, not guaranteed investment advice.

Implementation status: the first speckit-driven increment is tracked in `/Users/sandgupt/Wf-Adobe/spec-driven-development/projects/stock-predictor-research-platform`. The codebase now includes an additive research prediction endpoint and AI infrastructure theme endpoint as an MVP foundation for the broader roadmap.

## Core Product Thesis

Predict stocks by estimating future risk-adjusted return probabilities, not by pretending to know an exact future price.

Recommended prediction targets:

- 5 trading days, 21 trading days, and 63 trading days forward.
- Excess return versus `SPY`, sector ETF, and industry peer basket.
- Probability of outperforming by 2 percent, 5 percent, and 10 percent.
- Downside risk: probability of max drawdown greater than 5 percent or 10 percent.
- Confidence interval and explanation quality score.

The platform should answer:

- What changed recently?
- Which companies are exposed to that change?
- Did similar events historically help or hurt similar stocks?
- Is the market already pricing the story?
- What evidence supports the recommendation?

## Free And Low-Cost Data Sources

Use "free" carefully. Some sources are free for personal/internal research but not for redistribution, commercial display, or automated scraping. The ingestion layer should store source, license notes, retrieval time, and raw payload hash for every record.

### Market Prices, Fundamentals, And Reference Data

| Source | Best use | Free usefulness | Caveats |
| --- | --- | --- | --- |
| Yahoo Finance via `yfinance` | Broad daily price history, dividends/splits, quotes, some metadata, search/news | Excellent for personal research and quick bootstrapping | Unofficial. `yfinance` says Yahoo Finance data is for personal use and the package is not affiliated with Yahoo. Do not depend on it as the only production source. |
| Stooq | No-key historical OHLCV CSV, especially daily data | Very useful backup for prices and indices | Not a formal API. Ticker naming differs, for example `AAPL.US`. Verify corporate-action adjustments. |
| SEC EDGAR APIs | Company filings, submissions, XBRL company facts, 10-K/10-Q/8-K history | Essential and official. No API key required. Great for fundamentals and event detection | US public companies only. XBRL facts need normalization and point-in-time handling. |
| FRED/ALFRED | Macro series, rates, inflation, employment, yield curve, industrial production, vintages | Essential macro layer | FRED needs an API key. Use ALFRED vintages when avoiding look-ahead bias from revised economic data. |
| Alpha Vantage | Daily/weekly/monthly series, technical indicators, macro, news sentiment, earnings transcripts | Useful with a free key for narrow tests | Free service is currently up to 25 requests/day. Many full-history or adjusted endpoints may require premium. |
| Financial Modeling Prep | EOD prices, company profiles, financial statements, ratios, news on paid tiers | Strong free starter for 250 calls/day and 5 years of some data | Free tier is constrained; more history, transcripts, and richer datasets move to paid plans. Licensing required for redistribution. |
| Twelve Data | Time series, quotes, technical indicators, reference data, forex/crypto | Useful free tier: 8 API credits/minute, 800/day | Free plan is personal/non-commercial and has market/symbol limits. |
| Tiingo | EOD price history and current daily updates | Good source for cleaner EOD pipelines with account token | Internal-use terms matter; redistribution requires permission. |
| Finnhub | Quotes, candles, fundamentals, company news, alternative data | Useful retail free API for prototyping | Confirm endpoint entitlements and rate limits before relying on it. |
| Marketstack | EOD prices, tickers, exchanges, splits/dividends | Only useful for small demos | Free plan is very small: 100 requests/month and 12 months of history. Not enough for full backtesting. |

### News, Events, Filings, And World Context

| Source | Best use | Free usefulness | Caveats |
| --- | --- | --- | --- |
| GDELT | Global news/event monitoring, themes, locations, organizations, geopolitical events | Best free global news/event backbone | Entity extraction is noisy. Must de-duplicate and score source quality. |
| SEC EDGAR | Earnings, risk factors, 8-K events, guidance changes, capex, backlog, customer concentration | Best official company-event source | Filing timestamps matter. Normalize CIK to ticker over time. |
| The Guardian Open Platform | Long archive of general world news dating back to 1999 | Useful for macro/geopolitical narratives | Free non-profit/developer access, commercial packages separate. Not finance-specific. |
| Alpha Vantage News Sentiment | Ticker/topic-scoped news and sentiment | Convenient if request volume is tiny | 25 requests/day free limit makes broad crawling impractical. |
| Company IR sites and RSS feeds | Press releases, earnings dates, investor presentations | High-signal primary source | Each company differs. Build source adapters incrementally. |
| Federal agency APIs and calendars | CPI, payrolls, GDP, rates, energy, trade, manufacturing | High-signal macro and sector inputs | Need release timestamps and vintage data to prevent look-ahead. |
| Wikipedia/Wikimedia pageviews | Attention proxy for products, companies, technologies | Free useful alternative feature | Attention does not equal demand; use as weak feature only. |
| GitHub Archive, OpenAlex, arXiv, Hugging Face | AI developer/research adoption, model releases, agent framework activity | Useful AI adoption proxies | Needs careful topic taxonomy and lag tests. |

Avoid depending on paywalled news scraping or unlicensed redistribution. Also avoid treating generic NewsAPI as a historical backbone unless a paid historical plan is selected; its free tier is usually for development and recent articles, not multi-year backtests.

## Event Graph Design

The main redesign is an event graph that connects companies, sectors, macro series, technologies, and world events.

Core entities:

- `security`: ticker, exchange, CIK, company name, sector, industry, active dates.
- `company`: canonical company entity with aliases, subsidiaries, suppliers, customers.
- `event`: timestamped item such as earnings beat, export control, product launch, strike, rate decision, war escalation, AI model release, cloud capex increase, power shortage, or regulatory action.
- `article_or_filing`: raw evidence with source, URL, publication time, retrieval time, title, body/summary, and license.
- `event_entity_link`: event to company, sector, country, commodity, or macro series.
- `supply_chain_edge`: supplier, customer, competitor, dependent technology, geography.
- `feature_snapshot`: point-in-time feature values used by a model run.
- `prediction`: target horizon, probability, expected return, risk, explanation, model version.

Event fields:

- `event_type`: earnings, guidance, capex, regulation, geopolitics, macro, supply_chain, technology_release, product_demand, commodity, labor, cyber, legal.
- `direction`: demand_up, demand_down, supply_up, supply_down, margin_up, margin_down, valuation_multiple_up, valuation_multiple_down, risk_up, risk_down.
- `magnitude`: low, medium, high, or numeric score.
- `surprise`: expected versus unexpected compared to consensus, prior trend, or market-implied behavior.
- `relevance`: score per entity and per sector.
- `as_of_time`: the timestamp at which the system could have known this.

This is the bridge between news and prediction. A headline is not a feature by itself. A parsed, timestamped, entity-linked event is.

## Semiconductor And AI Market Map

The AI boom example should become a reusable "theme model". A theme model maps a narrative to the public companies and measurable drivers it may affect.

AI infrastructure theme layers:

- Model training demand: frontier model labs and hyperscaler capex drive GPUs, AI accelerators, HBM memory, networking, servers, datacenter power, cooling, and construction.
- Inference demand: once models are deployed, value shifts toward efficient accelerators, networking, model-serving software, cloud consumption, observability, security, data platforms, and agentic application vendors.
- Physical bottlenecks: advanced packaging, HBM supply, foundry capacity, EUV tools, networking switches, power transformers, cooling systems, land, fiber, grid interconnects, and datacenter permits.
- Geopolitical constraints: Taiwan risk, export controls, tariffs, chip subsidies, China restrictions, and supply concentration.
- Financial constraints: interest rates, capex cycles, hyperscaler free cash flow, inventory digestion, gross margin changes, and customer concentration.

Example company baskets to model:

- GPU/accelerator: `NVDA`, `AMD`, `AVGO`, `MRVL`.
- Foundry and manufacturing: `TSM`, `INTC`, `GFS`.
- Equipment and process control: `ASML`, `AMAT`, `LRCX`, `KLAC`.
- EDA/IP: `SNPS`, `CDNS`, `ARM`.
- Memory/storage: `MU`, `WDC`, `STX`.
- Networking: `ANET`, `AVGO`, `MRVL`, `CSCO`.
- Servers and integration: `SMCI`, `DELL`, `HPE`.
- Datacenter power/cooling: `VRT`, `ETN`, `PWR`, `GNRC`.
- Datacenter REIT/infrastructure: `EQIX`, `DLR`.
- Cloud and AI platforms: `MSFT`, `AMZN`, `GOOGL`, `ORCL`, `META`.
- Agentic/inference software and data layer: `NOW`, `CRM`, `PLTR`, `SNOW`, `DDOG`, `NET`, `MDB`, with care because valuation and actual AI revenue need evidence.

AI-specific features:

- Hyperscaler capex growth and capex guidance from filings/earnings.
- Mentions of "AI infrastructure", "GPU", "accelerator", "inference", "agent", "datacenter", "HBM", "advanced packaging", "liquid cooling", and "power constraint" in filings/news.
- Backlog, inventory, gross margin, customer concentration, and revenue segment changes.
- Electricity demand and energy price series.
- Semiconductor industrial production, trade/import series, and export-control events.
- AI research/model release cadence from arXiv/OpenAlex/Hugging Face/GitHub.
- Product adoption proxies: cloud AI service releases, developer activity, enterprise software AI attach-rate commentary.

Do not only model `NVDA`. The platform should detect second-order beneficiaries and bottlenecks.

## Feature Families

Start with interpretable features before deep learning:

- Price and volume: momentum, reversal, realized volatility, ATR, drawdown, abnormal volume, beta, sector-relative strength.
- Fundamentals: revenue growth, gross margin, operating margin, FCF margin, ROIC, debt, dilution, capex intensity, inventory days, backlog, valuation multiples.
- Filings and text: filing sentiment, risk-factor deltas, new material contracts, guidance changes, capex language, product/customer/geography exposure.
- News/events: event counts by type, event novelty, sentiment, topic velocity, entity relevance, source credibility, event co-occurrence.
- Macro: Fed funds, 2Y/10Y rates, CPI, payrolls, unemployment, ISM, GDP, credit spreads, dollar index, oil/gas/electricity, yield curve, liquidity.
- Sector/theme: supply-chain exposure, theme momentum, peer dispersion, commodity dependency, regulatory exposure.
- Market microstructure/risk: liquidity, gap risk, earnings date proximity, options implied volatility if a reliable source is added later.

## Modeling Approach

Begin with baselines and honest validation:

- Baseline 1: market/sector momentum and volatility model.
- Baseline 2: fundamental quality/value/momentum factor model.
- Baseline 3: event-augmented model with news/filing/macroeconomic features.
- Model candidates: logistic regression, ridge/elastic net, random forest, gradient boosting/XGBoost/LightGBM, calibrated probability models.
- Deep learning comes later, only after the dataset is large and clean enough.

Validation rules:

- Use walk-forward validation.
- Use point-in-time features only.
- Respect publication lags and macro data revisions.
- Include delisted companies where possible to avoid survivorship bias.
- Evaluate by hit rate, calibration, excess return, Sharpe/Sortino, max drawdown, turnover, transaction costs, and sector neutrality.
- Track model drift and regime performance, for example 2020 liquidity shock, 2022 rate shock, 2023-2025 AI infrastructure regime.

## Proposed Architecture

### Storage

Use a raw data lake plus relational serving tables:

- Raw files: Parquet or JSONL partitioned by source/date/entity.
- Postgres or SQLite/DuckDB for normalized metadata, features, and API serving.
- Redis only for cache, not as durable source of truth.

Tables to add:

- `data_sources`
- `securities`
- `security_identifiers`
- `daily_bars`
- `corporate_actions`
- `fundamental_facts`
- `filings`
- `articles`
- `events`
- `event_entity_links`
- `theme_exposures`
- `feature_snapshots`
- `model_runs`
- `predictions`
- `backtest_results`
- `prediction_outcomes`

### Services

- `SourceRegistry`: source metadata, limits, license notes, priority, health.
- `MarketDataIngestionService`: Yahoo/Stooq/Twelve/FMP/Alpha/Tiingo adapters.
- `FundamentalIngestionService`: SEC first, FMP optional.
- `NewsIngestionService`: GDELT, Guardian, Alpha News, company RSS.
- `EventExtractionService`: extract, classify, dedupe, entity-link events.
- `FeatureStoreService`: compute as-of feature snapshots.
- `BacktestService`: walk-forward evaluation and leakage checks.
- `PredictionService`: calibrated model inference.
- `ExplanationService`: evidence cards and factor contribution summaries.

## Implementation Roadmap

### Phase 0: Reset The Current App

- Stop treating mock data as a normal production fallback.
- Mark existing rule-based recommendations as demo-only.
- Add source provenance to every quote, bar, article, and recommendation.
- Correct outdated API key docs, especially Alpha Vantage and Marketstack limits.

### Phase 1: Free Historical Market Data MVP

- Add `yfinance` and Stooq adapters for daily bars.
- Store adjusted and raw OHLCV where available.
- Add SEC ticker/CIK mapping and company submissions ingestion.
- Build daily feature snapshots for 50 to 200 symbols.
- Add a basic benchmark-aware backtest.

### Phase 2: News And Event Backbone

- Add GDELT ingestion for company/theme queries.
- Add Guardian API ingestion for global macro/geopolitical archive.
- Add SEC 8-K, 10-Q, 10-K event extraction.
- Build event taxonomy and entity-linking.
- Add evidence cards to API responses.

### Phase 3: Theme Models

- Build first theme model: AI infrastructure and inference.
- Build second theme model: rates-sensitive growth stocks.
- Build third theme model: energy/commodity shock exposure.
- Add theme exposure scores and baskets.

### Phase 4: Predictive Models

- Train baseline factor models.
- Train event-augmented gradient boosting model.
- Add calibration curves and model cards.
- Compare predictions with and without event features.

### Phase 5: Product Experience

- Stock page: price/fundamentals/events/prediction/evidence timeline.
- Theme page: AI infrastructure map, beneficiaries, bottlenecks, recent events.
- Backtest page: model version, date range, performance, failures.
- Watchlist page: "what changed today" with source-backed explanations.

## What The Current Project Is Missing

- Point-in-time data discipline.
- Real historical ingestion beyond mock/demo data.
- Data source health, provenance, and license controls.
- Event extraction and company/theme linking.
- Backtesting that includes transaction costs and drawdowns.
- Survivorship-bias handling.
- Macro and cross-asset context.
- Sector and supply-chain models.
- Explanation output with linked evidence.
- Model monitoring against realized outcomes.

## Source Notes

- `yfinance`: https://pypi.org/project/yfinance/
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Alpha Vantage docs and support: https://www.alphavantage.co/documentation/ and https://www.alphavantage.co/support/
- Financial Modeling Prep pricing/FAQ: https://site.financialmodelingprep.com/pricing-plans and https://site.financialmodelingprep.com/faqs
- Twelve Data pricing/history docs: https://twelvedata.com/pricing and https://support.twelvedata.com/en/articles/5214728-getting-historical-data
- Tiingo EOD workflow and terms: https://www.tiingo.com/kb/article/the-fastest-method-to-ingest-tiingo-end-of-day-stock-api-data/ and https://api.tiingo.com/tos/
- Marketstack pricing/docs: https://marketstack.com/pricing/ and https://marketstack.com/documentation
- Finnhub overview/docs: https://finnhubio.github.io/ and https://finnhub.io/docs/api
- Stooq via pandas-datareader: https://pydata.github.io/pandas-datareader/devel/readers/stooq.html
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- The Guardian Open Platform: https://open-platform.theguardian.com/
- GDELT: https://www.gdeltproject.org/
