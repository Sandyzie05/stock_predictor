const API_BASE = '';

let currentList = 'all-time-high';
const appState = {
    market: null,
    report: null,
    currentPage: 'recommendations',
};

document.addEventListener('DOMContentLoaded', () => {
    initializePageTabs();
    initializeListTabs();
    refreshWorkspace();
});

function initializePageTabs() {
    const tabs = document.querySelectorAll('.page-tab');
    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const page = tab.getAttribute('data-page');
            switchPage(page);
        });
    });
}

function switchPage(page) {
    appState.currentPage = page;
    document.querySelectorAll('.page-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.getAttribute('data-page') === page);
    });
    document.querySelectorAll('.page').forEach((section) => {
        section.classList.toggle('active', section.id === `page-${page}`);
    });
}

function initializeListTabs() {
    document.querySelectorAll('#listTabs .tab').forEach((tab) => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('#listTabs .tab').forEach((item) => item.classList.remove('active'));
            tab.classList.add('active');
            currentList = tab.getAttribute('data-list');
            loadStockList(currentList);
        });
    });
}

async function refreshWorkspace() {
    setRefreshState(true);
    await Promise.allSettled([
        loadMarketIntelligence(),
        loadDailyReport(),
        loadStockList(currentList),
        checkSystemHealth(),
    ]);
    syncHeaderFromState();
    setRefreshState(false);
}

function setRefreshState(isLoading) {
    const button = document.getElementById('refreshWorkspaceButton');
    button.disabled = isLoading;
    button.innerHTML = isLoading
        ? '<i class="fa-solid fa-arrows-rotate fa-spin"></i> Refreshing'
        : '<i class="fa-solid fa-rotate-right"></i> Refresh';
}

function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        searchStock();
    }
}

function handleNewsSearchKeypress(event) {
    if (event.key === 'Enter') {
        searchMarketNews();
    }
}

async function loadMarketIntelligence() {
    try {
        const response = await fetch(`${API_BASE}/api/v1/market/intelligence/today?limit=5`);
        if (!response.ok) {
            throw new Error('Failed to load market intelligence.');
        }
        const data = await response.json();
        appState.market = data;
        renderMarketIntelligence(data);
    } catch (error) {
        renderRecommendationTable([]);
        renderIdeaMiniList('topBullishIdeas', [], 'No bullish ideas are available right now.');
        renderIdeaMiniList('topBearishIdeas', [], 'No bearish ideas are available right now.');
        renderStoryList('majorStories', [], 'Market stories are temporarily unavailable.');
        renderDecisionMethod(null, null);
        setElementText('marketIntelTimestamp', 'Market data unavailable');
        setElementText('tableSummaryPill', 'Market report unavailable');
        setElementText('topBuyPill', 'Top buy: --');
        setElementText('decisionModePill', '--');
        setElementText('dataFreshnessPolicy', error.message);
    }
}

async function loadDailyReport() {
    try {
        const response = await fetch(`${API_BASE}/api/v1/market/predictions/daily-report?days=30`);
        if (!response.ok) {
            throw new Error('Failed to load daily report.');
        }
        const data = await response.json();
        appState.report = data;
        renderDailyReport(data);
    } catch (error) {
        renderNarrative([]);
        renderRecentEvaluations([]);
        renderDailyBreakdown([]);
        document.getElementById('predictionScoreboard').innerHTML = '<div class="empty-state">Daily report unavailable right now.</div>';
        setElementText('predictionAccuracyBadge', 'Pending');
    }
}

function renderMarketIntelligence(data) {
    const ideas = [...(data.topBullish || []), ...(data.topBearish || [])];
    renderRecommendationTable(ideas);
    renderIdeaMiniList('topBullishIdeas', data.topBullish || [], 'No bullish ideas ranked yet.');
    renderIdeaMiniList('topBearishIdeas', data.topBearish || [], 'No bearish ideas ranked yet.');
    renderStoryList('majorStories', data.majorStories || [], 'No linked stories available.');
    renderDecisionMethod(data.decisionMethod, data.dataFreshness);
    renderPredictionScoreboard(data.scoreboard || {});

    setElementText('marketIntelTimestamp', `Updated ${formatDateTime(data.asOf)}`);
    setElementText('reportDateBadge', `Report date: ${data.reportDate || '--'}`);
    setElementText('reportDatePill', data.reportDate || '--');
    setElementText('resetAtBadge', `Reset: ${formatShortDateTime(data.resetAt)}`);
    setElementText('topBuyPill', `Top buy: ${data.summary?.topBuySymbol || 'None today'}`);
    setElementText('decisionModePill', prettifyMode(data.decisionMethod?.mode || '--'));
    setElementText('tableSummaryPill', `${ideas.length} names | ${data.summary?.buyCount ?? 0} buys`);

    setElementText('statBuyCount', String(data.summary?.buyCount ?? 0));
    setElementText('statWatchCount', String(data.summary?.watchCount ?? 0));
    setElementText('statAvoidCount', String(data.summary?.avoidCount ?? 0));
    setElementText('statBuyDetail', data.summary?.topBuySymbol ? `Best current long idea: ${data.summary.topBuySymbol}` : 'No buy met threshold yet.');
    setElementText('statWatchDetail', `${data.summary?.watchCount ?? 0} names still need another look.`);
    setElementText('statAvoidDetail', `${data.summary?.avoidCount ?? 0} names failed the current threshold.`);
    setElementText('dataFreshnessPolicy', data.dataFreshness?.datasetPolicy || 'Dataset freshness policy unavailable.');
}

function renderDailyReport(data) {
    const overall = data.overall || {};
    const trend = data.trend || {};

    renderNarrative(data.narrative || []);
    renderRecentEvaluations(data.recentEvaluations || []);
    renderDailyBreakdown(data.dailyBreakdown || []);

    setElementText('systemRatingBadge', `System rating: ${overall.systemRating || 'PENDING'}`);
    setElementText(
        'predictionAccuracyBadge',
        overall.accuracyPct != null ? `${formatPct(overall.accuracyPct, 2, false)} accuracy` : 'Awaiting evaluations'
    );

    setElementText('statAccuracy', overall.accuracyPct != null ? formatPct(overall.accuracyPct, 2, false) : '--');
    setElementText(
        'statAccuracyDetail',
        overall.evaluatedPredictions ? `${overall.correctPredictions ?? 0} correct of ${overall.evaluatedPredictions}.` : 'Waiting for next-day validation.'
    );
    setElementText(
        'statExcessReturn',
        overall.averageExcessReturnPct != null ? formatPct(overall.averageExcessReturnPct, 4, true) : '--'
    );
    setElementText(
        'statExcessDetail',
        overall.averageBenchmarkReturnPct != null
            ? `Benchmark average ${formatPct(overall.averageBenchmarkReturnPct, 4, true)}`
            : 'Benchmark comparison appears after evaluations settle.'
    );

    const narrative = data.narrative || [];
    if (narrative.length) {
        setElementText('tableSummaryPill', narrative[0]);
    }

    const exportDays = data.windowDays || 30;
    document.getElementById('dailyExportLink').href = `/api/v1/market/predictions/daily-report.csv?days=${exportDays}`;

    // expose trend in the validation page header chip if needed later
    document.getElementById('predictionAccuracyBadge').className = `mini-chip ${
        overall.accuracyPct == null ? '' : overall.accuracyPct >= 55 ? 'success' : 'warning'
    }`;
}

function syncHeaderFromState() {
    const resetAt = appState.market?.resetAt || appState.report?.resetAt;
    if (resetAt) {
        setElementText('resetAtBadge', `Reset: ${formatShortDateTime(resetAt)}`);
    }
}

function renderRecommendationTable(ideas) {
    const tbody = document.getElementById('recommendationRows');
    if (!ideas.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="subtle">No ranked recommendations are available right now.</td></tr>';
        return;
    }

    const rankedIdeas = [...ideas].sort((left, right) => {
        const actionPriority = { buy: 0, watch: 1, avoid: 2 };
        const leftAction = actionPriority[left.action] ?? 3;
        const rightAction = actionPriority[right.action] ?? 3;
        if (leftAction !== rightAction) {
            return leftAction - rightAction;
        }
        return Number(right.buyScore || 0) - Number(left.buyScore || 0);
    });

    tbody.innerHTML = rankedIdeas.map((idea) => {
        const localModel = idea.localModelAnalysis || {};
        const scenario = idea.scenarioSwarm || {};
        const evidenceCount = idea.nonDemoEvidenceCount ?? idea.metrics?.nonDemoEvidenceCount ?? 0;
        const confidenceText = idea.confidence != null ? `${Math.round(Number(idea.confidence) * 100)}%` : '--';
        const price = idea.currentPrice != null ? `$${Number(idea.currentPrice).toFixed(2)}` : '--';
        const change = idea.changePercent != null ? formatPct(Number(idea.changePercent), 2, true) : '--';
        const score = idea.buyScore != null ? Number(idea.buyScore).toFixed(2) : '--';
        const evidenceSummary = (idea.supportingEvidence || []).slice(0, 1).map((item) => item.summary || item.title || '').join('');

        return `
            <tr onclick="searchStockFromList('${escapeHtml(idea.symbol)}')">
                <td class="symbol-cell">
                    <strong>${escapeHtml(idea.symbol)}</strong>
                    <span>${escapeHtml(idea.companyName || 'Company')}</span><br>
                    <span>${escapeHtml(idea.topic || 'Market')}</span>
                </td>
                <td><span class="badge ${badgeTone(idea.action)}">${escapeHtml((idea.action || 'watch').toUpperCase())}</span></td>
                <td><span class="badge ${badgeTone(idea.dailyRating)}">${escapeHtml(idea.dailyRating || '--')}</span></td>
                <td class="mono">${score}</td>
                <td><span class="badge ${badgeTone(idea.direction)}">${escapeHtml((idea.direction || '--').toUpperCase())}</span></td>
                <td class="mono">${confidenceText}</td>
                <td>
                    <div class="mono">${price}</div>
                    <div class="${Number(idea.changePercent || 0) >= 0 ? 'positive' : 'negative'} mono">${change}</div>
                </td>
                <td>
                    <div class="subtle">${evidenceCount} live links</div>
                    <div class="subtle">${escapeHtml(evidenceSummary || 'No stored evidence summary.')}</div>
                </td>
                <td>
                    ${localModel.verdict ? `<span class="badge ${badgeTone(localModel.verdict)}">${escapeHtml(localModel.verdict.toUpperCase())}</span>` : '<span class="subtle">Not reviewed</span>'}
                    <div class="subtle">${escapeHtml(localModel.thesisSummary || idea.reasoning?.[0] || 'Awaiting structured local-model review.')}</div>
                    ${scenario.scenarioVerdict ? `<div class="subtle">Scenario ${escapeHtml(String(scenario.scenarioVerdict).toUpperCase())} | support ${Number(scenario.supportScore || 0).toFixed(2)}</div>` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function renderIdeaMiniList(containerId, ideas, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!ideas.length) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
        return;
    }

    container.innerHTML = ideas.map((idea, index) => `
        <div class="idea-card" onclick="searchStockFromList('${escapeHtml(idea.symbol)}')">
            <div class="idea-card-head">
                <div>
                    <strong>${index + 1}. ${escapeHtml(idea.symbol)}</strong><br>
                    <span class="subtle">${escapeHtml(idea.companyName || 'Company')}</span>
                </div>
                <span class="badge ${badgeTone(idea.action)}">${escapeHtml((idea.action || 'watch').toUpperCase())}</span>
            </div>
            <div class="microcopy">${escapeHtml(idea.reasoning?.[0] || 'No reasoning stored.')}</div>
            <div class="microcopy">${idea.buyScore != null ? `Buy score ${Number(idea.buyScore).toFixed(2)}` : 'Buy score unavailable'} | ${idea.confidence != null ? `${Math.round(Number(idea.confidence) * 100)}% confidence` : 'Confidence unavailable'}</div>
            <div class="microcopy">${idea.scenarioSwarm?.scenarioVerdict ? `Scenario ${String(idea.scenarioSwarm.scenarioVerdict).toUpperCase()} | Fragility ${Number(idea.scenarioSwarm.fragilityScore || 0).toFixed(2)}` : 'Scenario review pending.'}</div>
        </div>
    `).join('');
}

function renderNarrative(lines) {
    const container = document.getElementById('dailyNarrative');
    if (!lines.length) {
        container.innerHTML = '<li>No report notes are available yet.</li>';
        return;
    }
    container.innerHTML = lines.map((line) => `<li>${escapeHtml(line)}</li>`).join('');
}

function renderRecentEvaluations(rows) {
    const container = document.getElementById('recentEvaluations');
    if (!rows.length) {
        container.innerHTML = '<div class="empty-state">No evaluated daily predictions yet.</div>';
        return;
    }
    container.innerHTML = rows.map((row) => `
        <div class="evaluation-item">
            <div class="status-row">
                <div>
                    <strong>${escapeHtml(row.symbol)} ${escapeHtml((row.action || row.direction || '').toUpperCase())}</strong>
                    <div class="microcopy">${escapeHtml(row.topic || 'Market')} | ${escapeHtml(row.catalyst || 'Catalyst')}</div>
                </div>
                <span class="badge ${badgeTone(row.status)}">${escapeHtml((row.status || 'pending').toUpperCase())}</span>
            </div>
            <div class="microcopy">Return ${row.realizedReturnPct != null ? formatPct(row.realizedReturnPct, 2, true) : '--'} | Excess ${row.excessReturnPct != null ? formatPct(row.excessReturnPct, 2, true) : '--'} | Rating ${escapeHtml(row.dailyRating || '--')}</div>
            <div class="microcopy">${escapeHtml(row.evaluationNotes || 'Waiting for evaluation notes.')}</div>
        </div>
    `).join('');
}

function renderDailyBreakdown(rows) {
    const container = document.getElementById('dailyBreakdown');
    if (!rows.length) {
        container.innerHTML = '<div class="empty-state">Daily breakdown rows will appear once reports are stored.</div>';
        return;
    }
    container.innerHTML = rows.map((row) => `
        <div class="breakdown-row">
            <strong>${escapeHtml(row.reportDate)}</strong>
            <div>${row.totalPredictions} calls</div>
            <div>${row.evaluatedPredictions} evaluated</div>
            <div>${row.accuracyPct != null ? formatPct(row.accuracyPct, 2, false) : '--'} accuracy</div>
            <div>${row.averageExcessReturnPct != null ? formatPct(row.averageExcessReturnPct, 2, true) : '--'} excess</div>
            <div><span class="badge ${badgeTone(row.rating)}">${escapeHtml(row.rating || 'PENDING')}</span></div>
        </div>
    `).join('');
}

function renderPredictionScoreboard(scoreboard) {
    const container = document.getElementById('predictionScoreboard');
    const accuracy = scoreboard.accuracyPct != null ? formatPct(scoreboard.accuracyPct, 2, false) : 'Pending';
    const recentIdeas = (scoreboard.recentIdeas || []).slice(0, 5);

    container.innerHTML = `
        <div class="status-row">
            <div>
                <strong>${scoreboard.totalIdeas || 0} total ideas</strong>
                <div class="microcopy">${scoreboard.evaluatedIdeas || 0} evaluated | ${scoreboard.pendingIdeas || 0} pending</div>
            </div>
            <span class="badge ${scoreboard.accuracyPct == null ? 'neutral' : scoreboard.accuracyPct >= 55 ? 'buy' : 'watch'}">${accuracy}</span>
        </div>
        ${recentIdeas.length ? recentIdeas.map((idea) => `
            <div class="evaluation-item">
                <div class="status-row">
                    <div>
                        <strong>${escapeHtml(idea.symbol)} ${escapeHtml((idea.direction || '').toUpperCase())}</strong>
                        <div class="microcopy">${escapeHtml(idea.topic || 'Market')} | ${escapeHtml(idea.catalyst || 'Catalyst')}</div>
                    </div>
                    <span class="badge ${badgeTone(idea.status)}">${escapeHtml((idea.status || 'pending').toUpperCase())}</span>
                </div>
                <div class="microcopy">${escapeHtml(idea.evaluationNotes || 'Waiting for the holding window to complete.')}</div>
            </div>
        `).join('') : '<div class="empty-state">No tracked ideas yet. The next refresh will add them.</div>'}
    `;
}

function renderStoryList(containerId, stories, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!stories.length) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
        return;
    }
    container.innerHTML = stories.map((story) => {
        const linkedStocks = (story.linkedStocks || []).slice(0, 4);
        return `
            <div class="story-item">
                <div class="story-head">
                    <div>
                        <strong>${escapeHtml(story.title || 'Untitled story')}</strong><br>
                        <span class="subtle">${escapeHtml(story.source || 'Source')} | ${escapeHtml(story.topic || 'Market')} | ${formatDateTime(story.publishedAt)}</span>
                    </div>
                    <span class="badge ${badgeTone(story.directionalBias || 'neutral')}">${escapeHtml((story.directionalBias || 'mixed').toUpperCase())}</span>
                </div>
                ${linkedStocks.length ? `<div class="microcopy">${linkedStocks.map((item) => `${escapeHtml(item.symbol)}: ${escapeHtml(item.reason || 'linked')}`).join(' | ')}</div>` : ''}
                ${story.url ? `<div class="microcopy"><a href="${escapeHtml(story.url)}" target="_blank" rel="noopener noreferrer">Open story</a></div>` : ''}
            </div>
        `;
    }).join('');
}

function renderDecisionMethod(method, freshness) {
    document.getElementById('decisionMethodDescription').textContent = method?.description || 'Decision logic unavailable.';
    const steps = [
        'Collect current stories and structured evidence from open sources.',
        'Score stocks with deterministic weights before adding model opinion.',
        'Use Ollama only to review the prepared dataset, not to invent facts.',
        'Run a small role-based scenario swarm, then aggregate those opinions deterministically.',
        freshness?.datasetPolicy || 'Refresh data continuously and reset to a new report date at midnight.',
    ];
    document.getElementById('decisionWorkflowList').innerHTML = steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('');
}

async function searchMarketNews() {
    const query = document.getElementById('newsSearchQuery').value.trim();
    if (!query) {
        renderStoryList('newsSearchResults', [], 'Enter a topic to search current event coverage.');
        return;
    }
    document.getElementById('newsSearchResults').innerHTML = '<div class="loading-state">Searching live coverage...</div>';
    try {
        const response = await fetch(`${API_BASE}/api/v1/market/news/search?query=${encodeURIComponent(query)}&limit=8`);
        if (!response.ok) {
            throw new Error('Live news search is unavailable.');
        }
        const data = await response.json();
        renderStoryList('newsSearchResults', data.results || [], 'No current stories matched that search.');
    } catch (error) {
        renderStoryList('newsSearchResults', [], error.message);
    }
}

async function searchStock() {
    const input = document.getElementById('stockSearch');
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) {
        setAnalysisMessage('Enter a stock symbol to inspect drilldown details.', true);
        return;
    }

    switchPage('drilldown');
    document.getElementById('stockAnalysis').style.display = 'block';
    document.getElementById('analysisSymbol').textContent = symbol;
    setAnalysisPlaceholders();
    setAnalysisMessage('Loading quote, recommendation, company, research, analysis, and news...', true);

    const endpoints = {
        quote: `${API_BASE}/api/v1/stocks/${symbol}/quote`,
        recommendation: `${API_BASE}/api/v1/stocks/${symbol}/recommendation`,
        company: `${API_BASE}/api/v1/stocks/${symbol}/company`,
        analysis: `${API_BASE}/api/v1/stocks/${symbol}/analysis`,
        research: `${API_BASE}/api/v1/stocks/${symbol}/research-prediction`,
        news: `${API_BASE}/api/v1/stocks/${symbol}/news?limit=5`,
    };

    const entries = await Promise.all(
        Object.entries(endpoints).map(async ([key, url]) => {
            try {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`${key} unavailable`);
                }
                return [key, await response.json()];
            } catch (error) {
                return [key, null];
            }
        })
    );

    const payload = Object.fromEntries(entries);

    if (!payload.quote && !payload.recommendation && !payload.company) {
        setAnalysisMessage(`Unable to load drilldown for ${symbol}.`, false);
        return;
    }

    renderStockDrilldown(symbol, payload);
}

function setAnalysisPlaceholders() {
    const ids = [
        'currentPrice', 'recommendation', 'confidence', 'targetPrice',
        'analysisMarketCap', 'analysisSector', 'analysisRisk', 'analysisPotentialReturn',
        'analysisOverallScore', 'analysisResearch21d', 'analysisScenarioVerdict',
        'analysisScenarioFragility',
    ];
    ids.forEach((id) => setElementText(id, '--'));
    setElementText('analysisCompanyLine', 'Waiting for drilldown data.');
    setElementText('analysisUpdatedAt', '--');
    document.getElementById('analysisCompanyDescription').textContent = 'Waiting for company info.';
    document.getElementById('analysisCompanyWebsite').innerHTML = '';
    document.getElementById('analysisTechnical').textContent = 'Waiting for technical analysis.';
    document.getElementById('analysisResearchSignals').innerHTML = '<div class="empty-state">Waiting for research prediction.</div>';
    document.getElementById('analysisNews').innerHTML = '<div class="empty-state">Waiting for stock news.</div>';
    document.getElementById('analysisScenarioAgents').innerHTML = '<div class="empty-state">No scenario review loaded yet.</div>';
    document.getElementById('analysisScenarioSummary').textContent = 'Search a symbol to view scenario review.';
    document.getElementById('analysisScenarioWatch').textContent = 'Waiting for scenario watch points.';
}

function renderStockDrilldown(symbol, payload) {
    const quote = payload.quote || {};
    const recommendation = payload.recommendation || {};
    const company = payload.company || {};
    const analysis = payload.analysis || {};
    const research = payload.research || {};
    const news = payload.news || [];
    const currentIdea = findCurrentIdea(symbol);
    const scenario = currentIdea?.scenarioSwarm || null;

    setElementText('analysisCompanyLine', `${company.name || recommendation.company_name || symbol}${company.sector ? ` | ${company.sector}` : ''}`);
    setElementText('analysisUpdatedAt', quote.timestamp ? formatShortDateTime(quote.timestamp) : '--');

    setElementText('currentPrice', quote.price != null ? `$${Number(quote.price).toFixed(2)}` : '--');
    setElementText('recommendation', recommendation.recommendation ? String(recommendation.recommendation).toUpperCase() : '--');
    setElementText('confidence', recommendation.confidence != null ? `${Math.round(Number(recommendation.confidence) * 100)}%` : '--');
    setElementText('targetPrice', recommendation.target_price != null ? `$${Number(recommendation.target_price).toFixed(2)}` : '--');
    setElementText('analysisMarketCap', company.market_cap != null ? formatMarketCap(company.market_cap) : '--');
    setElementText('analysisSector', company.sector || '--');
    setElementText('analysisRisk', recommendation.risk_level ? String(recommendation.risk_level).toUpperCase() : '--');
    setElementText('analysisPotentialReturn', recommendation.potential_return != null ? formatPct(Number(recommendation.potential_return), 2, true) : '--');
    setElementText('analysisOverallScore', recommendation.overall_score != null ? Number(recommendation.overall_score).toFixed(1) : '--');

    const research21d = findResearchHorizon(research, '21d');
    setElementText(
        'analysisResearch21d',
        research21d ? `${String(research21d.recommendation || '--').replace(/_/g, ' ')} | ${Math.round(Number(research21d.confidence || 0) * 100)}% conf` : '--'
    );
    setElementText('analysisScenarioVerdict', scenario?.scenarioVerdict ? String(scenario.scenarioVerdict).toUpperCase() : '--');
    setElementText(
        'analysisScenarioFragility',
        scenario?.fragilityScore != null ? Number(scenario.fragilityScore).toFixed(2) : '--'
    );

    const reasoning = Array.isArray(recommendation.reasoning) ? recommendation.reasoning.join(' ') : recommendation.reasoning;
    setAnalysisMessage(reasoning || company.description || 'Drilldown loaded.', true);

    document.getElementById('analysisCompanyDescription').textContent = company.description || 'No company description available.';
    document.getElementById('analysisCompanyWebsite').innerHTML = company.website
        ? `<a href="${escapeHtml(company.website)}" target="_blank" rel="noopener noreferrer">${escapeHtml(company.website)}</a>`
        : '';

    document.getElementById('analysisTechnical').textContent = buildTechnicalSummary(analysis);
    renderResearchSignals(research);
    renderStockNews(news);
    renderScenarioReview(currentIdea);
}

function renderResearchSignals(research) {
    const container = document.getElementById('analysisResearchSignals');
    const horizons = research.horizons || [];
    if (!horizons.length) {
        container.innerHTML = '<div class="empty-state">No research prediction available.</div>';
        return;
    }

    container.innerHTML = horizons.slice(0, 3).map((horizon) => `
        <div class="metric-tile">
            <div class="label">${escapeHtml(horizon.horizon || 'horizon')}</div>
            <div class="value">${escapeHtml(String(horizon.recommendation || '--').replace(/_/g, ' ').toUpperCase())}</div>
            <div class="microcopy">
                ${horizon.probability_outperform != null ? `${Math.round(Number(horizon.probability_outperform) * 100)}% outperform` : '--'} |
                ${horizon.confidence != null ? `${Math.round(Number(horizon.confidence) * 100)}% confidence` : '--'}
            </div>
        </div>
    `).join('');
}

function renderStockNews(news) {
    const container = document.getElementById('analysisNews');
    if (!news.length) {
        container.innerHTML = '<div class="empty-state">No recent stock news available.</div>';
        return;
    }
    container.innerHTML = news.map((item) => `
        <div class="story-item">
            <div class="story-head">
                <div>
                    <strong>${escapeHtml(item.title || 'Untitled story')}</strong><br>
                    <span class="subtle">${escapeHtml(item.source || 'Source')} | ${formatDateTime(item.published_at)}</span>
                </div>
                <span class="badge ${badgeTone(item.sentiment || 'neutral')}">${escapeHtml(String(item.sentiment || 'neutral').toUpperCase())}</span>
            </div>
            <div class="microcopy">${escapeHtml(item.description || 'No description available.')}</div>
            ${item.url ? `<div class="microcopy"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Open story</a></div>` : ''}
        </div>
    `).join('');
}

function renderScenarioReview(idea) {
    const scenario = idea?.scenarioSwarm || null;
    const agentsContainer = document.getElementById('analysisScenarioAgents');
    if (!scenario) {
        document.getElementById('analysisScenarioSummary').textContent = 'No stored scenario review for this symbol in the current report.';
        document.getElementById('analysisScenarioWatch').textContent = 'No scenario watch points stored yet.';
        agentsContainer.innerHTML = '<div class="empty-state">No scenario review loaded yet.</div>';
        return;
    }

    document.getElementById('analysisScenarioSummary').textContent = scenario.summary || 'Scenario review loaded.';
    document.getElementById('analysisScenarioWatch').textContent = (scenario.watchNextSession || []).length
        ? `Watch next: ${(scenario.watchNextSession || []).join(' | ')}`
        : 'No special next-session watch points were stored.';

    const agents = scenario.agents || [];
    if (!agents.length) {
        agentsContainer.innerHTML = '<div class="empty-state">No agent opinions were stored.</div>';
        return;
    }

    agentsContainer.innerHTML = agents.map((agent) => `
        <div class="story-item">
            <div class="story-head">
                <div>
                    <strong>${escapeHtml(agent.agentName || 'agent')}</strong><br>
                    <span class="subtle">${escapeHtml(agent.keyReason || 'No reason stored.')}</span>
                </div>
                <span class="badge ${badgeTone(agent.stance)}">${escapeHtml(String(agent.stance || 'mixed').toUpperCase())}</span>
            </div>
            <div class="microcopy">Confidence ${agent.confidence != null ? `${Math.round(Number(agent.confidence) * 100)}%` : '--'} | Invalidate: ${escapeHtml(agent.whatChangesMyView || '--')}</div>
            <div class="microcopy">${escapeHtml(agent.nextSessionRisk || 'No next-session risk stored.')}</div>
        </div>
    `).join('');
}

function buildTechnicalSummary(analysis) {
    if (!analysis || Object.keys(analysis).length === 0) {
        return 'No technical snapshot available.';
    }

    const bits = [];
    if (analysis.trend) {
        bits.push(`Trend: ${analysis.trend}`);
    }
    const technicals = analysis.technical_indicators || {};
    if (technicals.rsi != null) {
        bits.push(`RSI ${Number(technicals.rsi).toFixed(1)}`);
    }
    if (technicals.macd != null && technicals.macd_signal != null) {
        bits.push(`MACD ${Number(technicals.macd).toFixed(2)} vs signal ${Number(technicals.macd_signal).toFixed(2)}`);
    }
    if (technicals.sma_20 != null && technicals.sma_50 != null) {
        bits.push(`SMA20 ${Number(technicals.sma_20).toFixed(2)} / SMA50 ${Number(technicals.sma_50).toFixed(2)}`);
    }
    return bits.length ? bits.join('. ') : 'Technical snapshot returned limited data.';
}

function findResearchHorizon(research, wanted) {
    return (research.horizons || []).find((item) => item.horizon === wanted) || null;
}

function findCurrentIdea(symbol) {
    const ideas = [
        ...(appState.market?.topBullish || []),
        ...(appState.market?.topBearish || []),
    ];
    return ideas.find((idea) => String(idea.symbol || '').toUpperCase() === String(symbol || '').toUpperCase()) || null;
}

function setAnalysisMessage(message, neutral = true) {
    const summary = document.getElementById('analysisSummary');
    summary.textContent = message;
    summary.style.borderColor = neutral ? 'rgba(148, 163, 184, 0.18)' : 'rgba(248, 113, 113, 0.22)';
    summary.style.color = neutral ? 'var(--text-soft)' : '#fecaca';
}

async function loadStockList(listType) {
    const container = document.getElementById('stockLists');
    container.innerHTML = '<div class="loading-state">Loading stock screen...</div>';
    try {
        const response = await fetch(`${API_BASE}/api/v1/lists/${listType}?max_items=10`);
        if (!response.ok) {
            throw new Error('Stock screen unavailable.');
        }
        const data = await response.json();
        renderStockList(data);
    } catch (error) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(error.message)} You can still search an individual symbol above.</div>`;
    }
}

function renderStockList(data) {
    const container = document.getElementById('stockLists');
    const items = data.items || [];
    if (!items.length) {
        container.innerHTML = '<div class="empty-state">That screen has no current data right now.</div>';
        return;
    }

    container.innerHTML = `
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Stock</th>
                        <th>Price</th>
                        <th>Move</th>
                        <th>Score</th>
                        <th>Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map((stock, index) => `
                        <tr onclick="searchStockFromList('${escapeHtml(stock.symbol)}')">
                            <td class="symbol-cell">
                                <strong>${index + 1}. ${escapeHtml(stock.symbol)}</strong>
                                <span>${escapeHtml(stock.company_name || 'Company')}</span>
                            </td>
                            <td class="mono">${stock.current_price != null ? `$${Number(stock.current_price).toFixed(2)}` : '--'}</td>
                            <td class="${Number(stock.change_percent || 0) >= 0 ? 'positive' : 'negative'} mono">${stock.change_percent != null ? formatPct(Number(stock.change_percent), 2, true) : '--'}</td>
                            <td class="mono">${stock.score != null ? Number(stock.score).toFixed(0) : '--'}</td>
                            <td><span class="badge ${badgeTone(stock.recommendation || 'watch')}">${escapeHtml((stock.recommendation || 'hold').toUpperCase())}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function searchStockFromList(symbol) {
    document.getElementById('stockSearch').value = symbol;
    switchPage('drilldown');
    searchStock();
}

async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/v1/monitoring/health`);
        if (!response.ok) {
            throw new Error('Health endpoint unavailable.');
        }
        const health = await response.json();
        updateSystemStatus(health);
    } catch (error) {
        updateSystemStatus(null);
    }
}

function updateSystemStatus(health) {
    const subsystems = health?.subsystems || {};
    applyStatusBadge('apiStatus', subsystems.api?.status, { healthy: 'Online', degraded: 'Degraded', unhealthy: 'Offline', idle: 'Idle', unknown: 'Unknown' });
    applyStatusBadge('dataStatus', subsystems.data?.status, { healthy: 'Active', degraded: 'Limited', unhealthy: 'Inactive', idle: 'Idle', unknown: 'Unknown' });
    applyStatusBadge('mlStatus', subsystems.ml?.status, { healthy: 'Running', degraded: 'Partial', unhealthy: 'Stopped', idle: 'Idle', unknown: 'Unknown' });
    applyStatusBadge('telemetryStatus', subsystems.observability?.status, { healthy: 'Tracking', degraded: 'Partial', unhealthy: 'Down', idle: 'Idle', unknown: 'Unknown' });
}

function applyStatusBadge(elementId, status, labels) {
    const element = document.getElementById(elementId);
    const normalized = status || 'unknown';
    element.textContent = labels[normalized] || labels.unknown || 'Unknown';
    element.className = `badge ${statusTone(normalized)}`;
}

function badgeTone(value) {
    const normalized = String(value || '').toLowerCase();
    if (['buy', 'a', 'b', 'up', 'correct', 'supports', 'positive'].includes(normalized)) {
        return normalized === 'supports' ? 'supports' : 'buy';
    }
    if (['watch', 'c', 'mixed', 'pending', 'neutral'].includes(normalized)) {
        return 'watch';
    }
    if (['avoid', 'd', 'f', 'down', 'incorrect', 'contradicts', 'sell', 'strong_sell', 'negative'].includes(normalized)) {
        return normalized === 'contradicts' ? 'contradicts' : 'avoid';
    }
    return 'neutral';
}

function statusTone(status) {
    if (status === 'healthy') return 'buy';
    if (status === 'degraded') return 'watch';
    if (status === 'unhealthy') return 'avoid';
    return 'neutral';
}

function prettifyMode(value) {
    return String(value || '--').replace(/-/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatPct(value, digits = 2, signed = true) {
    if (value == null || Number.isNaN(Number(value))) {
        return '--';
    }
    const amount = Number(value);
    const prefix = signed && amount > 0 ? '+' : '';
    return `${prefix}${amount.toFixed(digits)}%`;
}

function formatDateTime(value) {
    if (!value) return '--';
    return new Date(value).toLocaleString();
}

function formatShortDateTime(value) {
    if (!value) return '--';
    return new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function formatMarketCap(value) {
    const amount = Number(value);
    if (Number.isNaN(amount)) return '--';
    if (amount >= 1_000_000_000_000) return `$${(amount / 1_000_000_000_000).toFixed(2)}T`;
    if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(2)}B`;
    if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(2)}M`;
    return `$${amount.toFixed(0)}`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setElementText(id, text) {
    const element = document.getElementById(id);
    if (element) element.textContent = text;
}

setInterval(() => {
    checkSystemHealth();
}, 30000);

setInterval(() => {
    refreshWorkspace();
}, 300000);
