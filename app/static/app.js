const API_BASE = '';

let currentList = 'all-time-high';
const appState = {
    market: null,
    report: null,
};

document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    refreshWorkspace();
});

function initializeTabs() {
    const tabs = document.querySelectorAll('#listTabs .tab');
    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            tabs.forEach((item) => item.classList.remove('active'));
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
    if (!button) {
        return;
    }

    button.disabled = isLoading;
    button.innerHTML = isLoading
        ? '<i class="fa-solid fa-arrows-rotate fa-spin"></i> Refreshing'
        : '<i class="fa-solid fa-rotate-right"></i> Refresh workspace';
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

async function searchStock() {
    const input = document.getElementById('stockSearch');
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) {
        setAnalysisMessage('Enter a stock symbol to inspect the latest quote and recommendation.', true);
        return;
    }

    document.getElementById('stockAnalysis').style.display = 'block';
    document.getElementById('analysisSymbol').textContent = symbol;
    document.getElementById('currentPrice').textContent = '--';
    document.getElementById('recommendation').textContent = '--';
    document.getElementById('confidence').textContent = '--';
    document.getElementById('targetPrice').textContent = '--';
    setAnalysisMessage('Loading live quote and recommendation...', true);

    try {
        const [quoteResponse, recommendationResponse] = await Promise.all([
            fetch(`${API_BASE}/api/v1/stocks/${symbol}/quote`),
            fetch(`${API_BASE}/api/v1/stocks/${symbol}/recommendation`),
        ]);

        if (!quoteResponse.ok || !recommendationResponse.ok) {
            throw new Error('Quote or recommendation endpoint is currently unavailable for that symbol.');
        }

        const quote = await quoteResponse.json();
        const recommendation = await recommendationResponse.json();
        updateStockAnalysis(quote, recommendation);
    } catch (error) {
        setAnalysisMessage(`Unable to load ${symbol}. ${error.message}`, false);
    }
}

function updateStockAnalysis(quote, recommendation) {
    const priceText = quote.price != null ? `$${Number(quote.price).toFixed(2)}` : 'N/A';
    const recommendationText = (recommendation.recommendation || 'hold').toUpperCase();
    const confidence = recommendation.confidence != null
        ? `${Math.round(Number(recommendation.confidence) * 100)}%`
        : 'N/A';
    const targetPrice = recommendation.target_price != null
        ? `$${Number(recommendation.target_price).toFixed(2)}`
        : 'N/A';
    const change = Number(quote.change || 0);

    document.getElementById('currentPrice').textContent = priceText;
    document.getElementById('currentPrice').className = change > 0 ? 'positive' : change < 0 ? 'negative' : '';
    document.getElementById('recommendation').textContent = recommendationText;
    document.getElementById('confidence').textContent = confidence;
    document.getElementById('targetPrice').textContent = targetPrice;

    const reasoning = Array.isArray(recommendation.reasoning)
        ? recommendation.reasoning.join(' ')
        : recommendation.reasoning || 'Recommendation ready.';
    setAnalysisMessage(reasoning, true);
}

function setAnalysisMessage(message, neutral = true) {
    const summary = document.getElementById('analysisSummary');
    summary.textContent = message;
    summary.style.borderColor = neutral ? 'rgba(148, 163, 184, 0.18)' : 'rgba(248, 113, 113, 0.22)';
    summary.style.color = neutral ? 'var(--text-soft)' : '#fecaca';
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
        setElementText('marketIntelTimestamp', 'Market data unavailable');
        setElementText('tableSummaryPill', 'Market report unavailable');
        document.getElementById('decisionMethodDescription').textContent = error.message;
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
        setElementText('predictionAccuracyBadge', 'Pending');
        document.getElementById('predictionScoreboard').innerHTML = '<div class="empty-state">Daily report unavailable right now.</div>';
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
    setElementText('reportDatePill', `Report date: ${data.reportDate || '--'}`);
    setElementText('resetAtBadge', `Reset: ${formatShortDateTime(data.resetAt)}`);
    setElementText('topBuyPill', `Top buy: ${data.summary?.topBuySymbol || 'None today'}`);
    setElementText(
        'decisionModePill',
        `Method: ${prettifyMode(data.decisionMethod?.mode || 'loading')}`
    );
    setElementText(
        'tableSummaryPill',
        `${ideas.length} ranked names | ${data.summary?.buyCount ?? 0} buys`
    );

    setElementText('statBuyCount', String(data.summary?.buyCount ?? 0));
    setElementText('statWatchCount', String(data.summary?.watchCount ?? 0));
    setElementText('statAvoidCount', String(data.summary?.avoidCount ?? 0));
    setElementText('statBuyDetail', data.summary?.topBuySymbol ? `Best current long idea: ${data.summary.topBuySymbol}` : 'No buy reached the threshold yet.');
    setElementText('statWatchDetail', `${data.summary?.watchCount ?? 0} names need another look before acting.`);
    setElementText('statAvoidDetail', `${data.summary?.avoidCount ?? 0} names failed the deterministic threshold today.`);
    setElementText('dataFreshnessPolicy', data.dataFreshness?.datasetPolicy || 'Dataset freshness policy unavailable.');
}

function renderDailyReport(data) {
    const overall = data.overall || {};
    const trend = data.trend || {};

    renderNarrative(data.narrative || []);
    renderRecentEvaluations(data.recentEvaluations || []);
    renderDailyBreakdown(data.dailyBreakdown || []);

    setElementText('heroSystemRating', overall.systemRating || 'PENDING');
    setElementText(
        'heroSystemDetail',
        overall.evaluatedPredictions
            ? `${overall.evaluatedPredictions} evaluated rows in the last ${data.windowDays} days.`
            : 'Predictions are still accumulating evaluated outcomes.'
    );
    setElementText('heroTrendStatus', prettifyMode(trend.status || 'stable'));
    setElementText(
        'heroTrendDetail',
        trend.recentAccuracyPct != null
            ? `Recent window ${formatPct(trend.recentAccuracyPct, 2, false)} vs prior ${formatPct(trend.priorAccuracyPct, 2, false)}`
            : trend.message || 'Trend signal is not available yet.'
    );

    setElementText(
        'systemRatingBadge',
        `System rating: ${overall.systemRating || 'PENDING'}`
    );
    setElementText(
        'predictionAccuracyBadge',
        overall.accuracyPct != null
            ? `${formatPct(overall.accuracyPct, 2, false)} accuracy`
            : 'Awaiting evaluations'
    );
    document.getElementById('predictionAccuracyBadge').className = `status-chip ${
        overall.accuracyPct == null ? '' : overall.accuracyPct >= 55 ? 'success' : 'warning'
    }`;

    setElementText('statAccuracy', overall.accuracyPct != null ? formatPct(overall.accuracyPct, 2, false) : '--');
    setElementText(
        'statAccuracyDetail',
        overall.evaluatedPredictions
            ? `${overall.correctPredictions ?? 0} correct of ${overall.evaluatedPredictions}.`
            : 'The next-day validation set has not settled yet.'
    );
    setElementText(
        'statExcessReturn',
        overall.averageExcessReturnPct != null ? formatPct(overall.averageExcessReturnPct, 4, true) : '--'
    );
    setElementText(
        'statExcessDetail',
        overall.averageBenchmarkReturnPct != null
            ? `Benchmark average ${formatPct(overall.averageBenchmarkReturnPct, 4, true)}`
            : 'Benchmark comparison will appear after evaluations settle.'
    );

    const exportDays = data.windowDays || 30;
    document.getElementById('dailyExportLink').href = `/api/v1/market/predictions/daily-report.csv?days=${exportDays}`;
}

function syncHeaderFromState() {
    const market = appState.market;
    const report = appState.report;
    const resetAt = market?.resetAt || report?.resetAt;

    if (resetAt) {
        setElementText('resetAtBadge', `Reset: ${formatShortDateTime(resetAt)}`);
    }

    if (report?.overall?.systemRating) {
        setElementText('systemRatingBadge', `System rating: ${report.overall.systemRating}`);
    }
}

function renderRecommendationTable(ideas) {
    const tbody = document.getElementById('recommendationRows');
    if (!ideas.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="muted">No ranked recommendations are available right now.</td></tr>';
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
        const evidenceCount = idea.nonDemoEvidenceCount ?? idea.metrics?.nonDemoEvidenceCount ?? 0;
        const confidenceText = idea.confidence != null ? `${Math.round(Number(idea.confidence) * 100)}%` : '--';
        const price = idea.currentPrice != null ? `$${Number(idea.currentPrice).toFixed(2)}` : '--';
        const change = idea.changePercent != null ? formatPct(Number(idea.changePercent), 2, true) : '--';
        const score = idea.buyScore != null ? Number(idea.buyScore).toFixed(2) : '--';
        const actionLabel = (idea.action || 'watch').toUpperCase();
        const evidenceLinks = (idea.supportingEvidence || [])
            .slice(0, 2)
            .map((item) => item.url
                ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source || 'Source')}</a>`
                : `<span>${escapeHtml(item.source || 'Source')}</span>`)
            .join('<br>');

        return `
            <tr onclick="searchStockFromList('${escapeHtml(idea.symbol)}')">
                <td class="symbol-cell">
                    <strong>${escapeHtml(idea.symbol)}</strong>
                    <span>${escapeHtml(idea.companyName || 'Company')}</span><br>
                    <span>${escapeHtml(idea.topic || 'market')}</span>
                </td>
                <td><span class="badge ${badgeTone(idea.action)}">${actionLabel}</span></td>
                <td><span class="badge ${badgeTone(idea.dailyRating)}">${escapeHtml(idea.dailyRating || '--')}</span></td>
                <td class="mono">${score}</td>
                <td><span class="badge ${badgeTone(idea.direction)}">${escapeHtml((idea.direction || '--').toUpperCase())}</span></td>
                <td class="mono">${confidenceText}</td>
                <td>
                    <div class="mono">${price}</div>
                    <div class="${Number(idea.changePercent || 0) >= 0 ? 'positive' : 'negative'} mono">${change}</div>
                </td>
                <td>
                    <div class="subtle">${evidenceCount} current evidence links</div>
                    <div class="subtle">${evidenceLinks || 'No live links stored.'}</div>
                </td>
                <td>
                    ${localModel.verdict ? `<span class="badge ${badgeTone(localModel.verdict)}">${escapeHtml(localModel.verdict.toUpperCase())}</span>` : '<span class="subtle">Not reviewed</span>'}
                    <div class="subtle">${escapeHtml(localModel.thesisSummary || idea.reasoning?.[0] || 'Awaiting structured local-model review.')}</div>
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

    container.innerHTML = ideas.map((idea, index) => {
        const localModel = idea.localModelAnalysis || {};
        const confidenceText = idea.confidence != null ? `${Math.round(Number(idea.confidence) * 100)}% confidence` : 'Confidence unavailable';
        const evidenceLinks = (idea.supportingEvidence || []).filter((item) => item.url).slice(0, 2);
        return `
            <div class="idea-card" onclick="searchStockFromList('${escapeHtml(idea.symbol)}')">
                <div class="idea-card-head">
                    <div>
                        <strong>${index + 1}. ${escapeHtml(idea.symbol)}</strong><br>
                        <small>${escapeHtml(idea.companyName || 'Company')} | ${escapeHtml(idea.topic || 'Market')}</small>
                    </div>
                    <span class="badge ${badgeTone(idea.action)}">${escapeHtml((idea.action || 'watch').toUpperCase())}</span>
                </div>
                <div class="microcopy" style="margin-top: 10px;">${escapeHtml(idea.reasoning?.slice(0, 2).join(' ') || 'No reasoning stored.')}</div>
                <div class="microcopy" style="margin-top: 8px;">${confidenceText} | buy score ${idea.buyScore != null ? Number(idea.buyScore).toFixed(2) : '--'}</div>
                ${localModel.verdict ? `<div class="microcopy" style="margin-top: 8px;"><span class="badge ${badgeTone(localModel.verdict)}">${escapeHtml(localModel.verdict.toUpperCase())}</span> ${escapeHtml(localModel.thesisSummary || '')}</div>` : ''}
                ${evidenceLinks.length ? `
                    <div class="evidence-list">
                        ${evidenceLinks.map((item) => `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source || 'Source')}: ${escapeHtml(item.title || 'Evidence')}</a>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderStoryList(containerId, stories, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!stories.length) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
        return;
    }

    container.innerHTML = stories.map((story) => {
        const linkedStocks = (story.linkedStocks || []).slice(0, 5);
        return `
            <div class="story-item">
                <div class="story-head">
                    <div>
                        <strong>${escapeHtml(story.title || 'Untitled story')}</strong><br>
                        <small>${escapeHtml(story.source || 'Source')} | ${escapeHtml(story.topic || 'Market')} | ${formatDateTime(story.publishedAt)}</small>
                    </div>
                    <span class="badge ${badgeTone(story.directionalBias || 'neutral')}">${escapeHtml((story.directionalBias || 'mixed').toUpperCase())}</span>
                </div>
                ${story.summary ? `<div class="microcopy" style="margin-top: 10px;">${escapeHtml(story.summary)}</div>` : ''}
                ${linkedStocks.length ? `<div class="microcopy" style="margin-top: 10px;">${linkedStocks.map((item) => `${escapeHtml(item.symbol)}: ${escapeHtml(item.reason || 'linked')}`).join(' | ')}</div>` : ''}
                ${story.url ? `<div class="evidence-list"><a href="${escapeHtml(story.url)}" target="_blank" rel="noopener noreferrer">Open source story</a></div>` : ''}
            </div>
        `;
    }).join('');
}

function renderDecisionMethod(method, freshness) {
    document.getElementById('decisionMethodDescription').textContent = method?.description || 'Deterministic scoring description unavailable.';
    const workflowList = document.getElementById('decisionWorkflowList');
    const steps = [
        'Current events and structured evidence are collected from open sources.',
        'Stocks are scored with deterministic weights before any model opinion is added.',
        'Ollama only evaluates the prepared dataset and can support, mix, or contradict the thesis.',
        freshness?.datasetPolicy || 'The dataset refreshes continually and resets to a new report date at midnight.',
    ];
    workflowList.innerHTML = steps.map((step) => `<li>${escapeHtml(step)}</li>`).join('');
}

function renderNarrative(lines) {
    const container = document.getElementById('dailyNarrative');
    if (!lines.length) {
        container.innerHTML = '<li>No report narrative is available yet.</li>';
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
                    <div class="microcopy">${escapeHtml(row.topic || 'Market')} | ${escapeHtml(row.catalyst || 'Daily catalyst')}</div>
                </div>
                <span class="badge ${badgeTone(row.status)}">${escapeHtml((row.status || 'pending').toUpperCase())}</span>
            </div>
            <div class="microcopy" style="margin-top: 10px;">
                Return ${row.realizedReturnPct != null ? formatPct(row.realizedReturnPct, 2, true) : '--'} |
                Excess ${row.excessReturnPct != null ? formatPct(row.excessReturnPct, 2, true) : '--'} |
                Rating ${escapeHtml(row.dailyRating || '--')}
            </div>
            <div class="microcopy" style="margin-top: 8px;">${escapeHtml(row.evaluationNotes || 'Waiting for evaluation notes.')}</div>
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
                <div class="microcopy" style="margin-top: 8px;">${escapeHtml(idea.evaluationNotes || 'Waiting for the holding window to complete.')}</div>
            </div>
        `).join('') : '<div class="empty-state">No tracked ideas yet. The next workspace refresh will add them.</div>'}
    `;
}

async function searchMarketNews() {
    const query = document.getElementById('newsSearchQuery').value.trim();
    if (!query) {
        renderStoryList('newsSearchResults', [], 'Enter a topic to search current event coverage.');
        return;
    }

    document.getElementById('newsSearchResults').innerHTML = '<div class="loading-state">Searching live market news...</div>';

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
        container.innerHTML = '<div class="empty-state">That screen has no current data. Free providers may be rate-limited or temporarily unavailable.</div>';
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
                            <td class="${Number(stock.change_percent || 0) >= 0 ? 'positive' : 'negative'} mono">
                                ${stock.change_percent != null ? formatPct(Number(stock.change_percent), 2, true) : '--'}
                            </td>
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
    searchStock();
    document.getElementById('stockAnalysis').scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    applyStatusBadge('apiStatus', subsystems.api?.status, {
        healthy: 'Online',
        degraded: 'Degraded',
        unhealthy: 'Offline',
        idle: 'Idle',
        unknown: 'Unknown',
    });
    applyStatusBadge('dataStatus', subsystems.data?.status, {
        healthy: 'Active',
        degraded: 'Limited',
        unhealthy: 'Inactive',
        idle: 'Idle',
        unknown: 'Unknown',
    });
    applyStatusBadge('mlStatus', subsystems.ml?.status, {
        healthy: 'Running',
        degraded: 'Partial',
        unhealthy: 'Stopped',
        idle: 'Idle',
        unknown: 'Unknown',
    });
    applyStatusBadge('telemetryStatus', subsystems.observability?.status, {
        healthy: 'Tracking',
        degraded: 'Partial',
        unhealthy: 'Down',
        idle: 'Idle',
        unknown: 'Unknown',
    });
}

function applyStatusBadge(elementId, status, labels) {
    const element = document.getElementById(elementId);
    const normalized = status || 'unknown';
    element.textContent = labels[normalized] || labels.unknown || 'Unknown';
    element.className = `badge ${statusTone(normalized)}`;
}

function badgeTone(value) {
    const normalized = String(value || '').toLowerCase();
    if (['buy', 'a', 'b', 'up', 'correct', 'supports'].includes(normalized)) {
        return normalized === 'supports' ? 'supports' : 'buy';
    }
    if (['watch', 'c', 'mixed', 'pending'].includes(normalized)) {
        return normalized === 'mixed' ? 'watch' : 'watch';
    }
    if (['avoid', 'd', 'f', 'down', 'incorrect', 'contradicts', 'sell', 'strong_sell'].includes(normalized)) {
        return normalized === 'contradicts' ? 'contradicts' : 'avoid';
    }
    return 'neutral';
}

function ratingTone(rating) {
    return badgeTone(rating);
}

function statusTone(status) {
    if (status === 'healthy') {
        return 'buy';
    }
    if (status === 'degraded') {
        return 'watch';
    }
    if (status === 'unhealthy') {
        return 'avoid';
    }
    return 'neutral';
}

function prettifyMode(value) {
    return String(value || '--')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (match) => match.toUpperCase());
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
    if (!value) {
        return '--';
    }
    return new Date(value).toLocaleString();
}

function formatShortDateTime(value) {
    if (!value) {
        return '--';
    }
    return new Date(value).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });
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
    if (element) {
        element.textContent = text;
    }
}

setInterval(() => {
    checkSystemHealth();
}, 30000);

setInterval(() => {
    refreshWorkspace();
}, 300000);
