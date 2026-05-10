// Stock Predictor Web Interface JavaScript

const API_BASE = '';
let currentList = 'all-time-high';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadStockList(currentList);
    loadMarketIntelligence();
    checkSystemHealth();
});

// Initialize tab functionality
function initializeTabs() {
    const tabs = document.querySelectorAll('#listTabs .nav-link');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Load the selected list
            const listType = this.getAttribute('data-list');
            currentList = listType;
            loadStockList(listType);
        });
    });
}

// Handle search keypress
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

// Search for a specific stock
async function searchStock() {
    const symbol = document.getElementById('stockSearch').value.trim().toUpperCase();
    if (!symbol) {
        alert('Please enter a stock symbol');
        return;
    }

    const analysisDiv = document.getElementById('stockAnalysis');
    const symbolSpan = document.getElementById('analysisSymbol');
    
    symbolSpan.textContent = symbol;
    analysisDiv.style.display = 'block';
    
    // Show loading state
    document.getElementById('currentPrice').textContent = 'Loading...';
    document.getElementById('recommendation').textContent = 'Loading...';
    document.getElementById('confidence').textContent = 'Loading...';
    document.getElementById('targetPrice').textContent = 'Loading...';
    document.getElementById('analysisSummary').textContent = 'Analyzing stock data...';

    try {
        // Fetch stock data
        const [quoteResponse, recommendationResponse] = await Promise.all([
            fetch(`${API_BASE}/api/v1/stocks/${symbol}/quote`),
            fetch(`${API_BASE}/api/v1/stocks/${symbol}/recommendation`)
        ]);

        if (quoteResponse.ok && recommendationResponse.ok) {
            const quote = await quoteResponse.json();
            const recommendation = await recommendationResponse.json();

            // Update UI with data
            updateStockAnalysis(quote, recommendation);
        } else {
            throw new Error('Stock not found or service unavailable');
        }
    } catch (error) {
        console.error('Error fetching stock data:', error);
        document.getElementById('analysisSummary').textContent = 
            `Error: ${error.message}. This may be due to upstream market-data availability, rate limits, or an invalid stock symbol.`;
        document.getElementById('analysisSummary').className = 'alert alert-warning';
    }
}

// Update stock analysis display
function updateStockAnalysis(quote, recommendation) {
    const priceElement = document.getElementById('currentPrice');
    const recElement = document.getElementById('recommendation');
    const confElement = document.getElementById('confidence');
    const targetElement = document.getElementById('targetPrice');
    const summaryElement = document.getElementById('analysisSummary');

    // Update price with color coding
    priceElement.textContent = `$${quote.price?.toFixed(2) || 'N/A'}`;
    if (quote.change > 0) {
        priceElement.className = 'price-positive';
    } else if (quote.change < 0) {
        priceElement.className = 'price-negative';
    } else {
        priceElement.className = 'price-neutral';
    }

    // Update recommendation with styling
    const recType = recommendation.recommendation?.toUpperCase() || 'HOLD';
    recElement.textContent = recType;
    recElement.className = `recommendation-${recType.toLowerCase().replace('_', '-')}`;

    // Update confidence with color coding
    const confidence = (recommendation.confidence * 100).toFixed(0);
    confElement.textContent = `${confidence}%`;
    if (confidence >= 80) {
        confElement.className = 'confidence-high text-white rounded px-2';
    } else if (confidence >= 60) {
        confElement.className = 'confidence-medium text-white rounded px-2';
    } else {
        confElement.className = 'confidence-low text-white rounded px-2';
    }

    // Update target price
    targetElement.textContent = recommendation.target_price ? 
        `$${recommendation.target_price.toFixed(2)}` : 'N/A';

    // Update summary
    const reasoningText = Array.isArray(recommendation.reasoning) ? 
        recommendation.reasoning.join(' ') : 
        (recommendation.reasoning || 'Analysis complete. Check individual metrics for details.');
    
    summaryElement.textContent = reasoningText;
    summaryElement.className = 'alert alert-info';
}

// Load stock list
async function loadStockList(listType) {
    const stockListsDiv = document.getElementById('stockLists');
    
    // Show loading
    stockListsDiv.innerHTML = `
        <div class="loading">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading ${listType.replace('-', ' ')} stocks...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/api/v1/lists/${listType}?max_items=10`);
        
        if (response.ok) {
            const data = await response.json();
            displayStockList(data);
        } else {
            throw new Error('Failed to load stock list');
        }
    } catch (error) {
        console.error('Error loading stock list:', error);
        stockListsDiv.innerHTML = `
            <div class="alert alert-warning">
                <h6><i class="fas fa-exclamation-triangle"></i> Unable to load stock list</h6>
                <p>This may be due to live market-data availability, network issues, or upstream rate limits. The service is running but one or more data sources may be unavailable.</p>
                <p><strong>Available features:</strong> Individual stock search and system monitoring.</p>
            </div>
        `;
    }
}

// Display stock list
function displayStockList(data) {
    const stockListsDiv = document.getElementById('stockLists');
    
    if (!data.items || data.items.length === 0) {
        stockListsDiv.innerHTML = `
            <div class="alert alert-info">
                <h6><i class="fas fa-info-circle"></i> No data available</h6>
                <p>Stock list data is not available at the moment. This may be due to:</p>
                <ul>
                    <li>Upstream market-data limits or temporary outages</li>
                    <li>Rate limits from free data providers</li>
                    <li>Insufficient recent data for this screen</li>
                </ul>
                <p>You can still search for individual stocks using the search feature above.</p>
            </div>
        `;
        return;
    }

    const listTitle = data.title || `${currentList.replace('-', ' ').toUpperCase()} Stocks`;
    
    let html = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-list"></i> ${listTitle}
                    <span class="badge bg-primary ms-2">${data.total_items || data.items.length} stocks</span>
                </h5>
                <small class="text-muted">${data.description || 'AI-generated stock recommendations'}</small>
            </div>
            <div class="card-body">
                <div class="row">
    `;

    data.items.forEach((stock, index) => {
        const recClass = getRecommendationClass(stock.recommendation);
        const scoreColor = getScoreColor(stock.score);
        const reasoningText = Array.isArray(stock.reasoning)
            ? stock.reasoning.join(' ')
            : (stock.reasoning || '');
        
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card stock-card ${recClass}" onclick="searchStockFromList('${stock.symbol}')">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="fw-bold mb-1">${stock.symbol}</h6>
                                <small class="text-muted">${stock.company_name || 'Company'}</small>
                            </div>
                            <span class="badge ${scoreColor}">#${stock.rank || index + 1}</span>
                        </div>
                        
                        <div class="mb-2">
                            <div class="d-flex justify-content-between">
                                <span>Price:</span>
                                <strong>$${(stock.current_price || 0).toFixed(2)}</strong>
                            </div>
                            ${stock.change_percent ? `
                                <div class="d-flex justify-content-between">
                                    <span>Change:</span>
                                    <span class="${stock.change_percent > 0 ? 'price-positive' : 'price-negative'}">
                                        ${stock.change_percent > 0 ? '+' : ''}${stock.change_percent.toFixed(2)}%
                                    </span>
                                </div>
                            ` : ''}
                            ${stock.score ? `
                                <div class="d-flex justify-content-between">
                                    <span>Score:</span>
                                    <strong>${stock.score.toFixed(0)}/100</strong>
                                </div>
                            ` : ''}
                        </div>
                        
                        ${reasoningText ? `
                            <small class="text-muted">${reasoningText.substring(0, 120)}...</small>
                        ` : ''}
                        
                        <div class="mt-2">
                            <small class="text-primary">
                                <i class="fas fa-mouse-pointer"></i> Click for detailed analysis
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
                </div>
            </div>
        </div>
    `;

    stockListsDiv.innerHTML = html;
}

async function loadMarketIntelligence() {
    document.getElementById('topBullishIdeas').innerHTML = '<div class="text-muted">Refreshing bullish ideas...</div>';
    document.getElementById('topBearishIdeas').innerHTML = '<div class="text-muted">Refreshing bearish ideas...</div>';
    document.getElementById('majorStories').innerHTML = '<div class="text-muted">Refreshing major stories...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v1/market/intelligence/today?limit=5`);
        if (!response.ok) {
            throw new Error('Failed to load market intelligence');
        }

        const data = await response.json();
        document.getElementById('marketIntelTimestamp').textContent = `Updated ${new Date(data.asOf).toLocaleString()}`;
        renderIdeaList('topBullishIdeas', data.topBullish || [], 'success');
        renderIdeaList('topBearishIdeas', data.topBearish || [], 'danger');
        renderStoryList('majorStories', data.majorStories || []);
        renderPredictionScoreboard(data.scoreboard || {});
    } catch (error) {
        console.error('Error loading market intelligence:', error);
        document.getElementById('topBullishIdeas').innerHTML = '<div class="text-muted">Market intelligence is temporarily unavailable.</div>';
        document.getElementById('topBearishIdeas').innerHTML = '<div class="text-muted">Market intelligence is temporarily unavailable.</div>';
        document.getElementById('majorStories').innerHTML = '<div class="text-muted">Story feed is temporarily unavailable.</div>';
        document.getElementById('predictionScoreboard').innerHTML = '<div class="text-muted">Prediction tracker is temporarily unavailable.</div>';
        document.getElementById('marketIntelTimestamp').textContent = 'Intelligence unavailable';
    }
}

async function searchMarketNews() {
    const query = document.getElementById('newsSearchQuery').value.trim();
    if (!query) {
        return;
    }

    const resultsDiv = document.getElementById('newsSearchResults');
    resultsDiv.innerHTML = '<div class="text-muted">Searching live news...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v1/market/news/search?query=${encodeURIComponent(query)}&limit=8`);
        if (!response.ok) {
            throw new Error('Failed to search market news');
        }

        const data = await response.json();
        renderStoryList('newsSearchResults', data.results || []);
    } catch (error) {
        console.error('Error searching market news:', error);
        resultsDiv.innerHTML = '<div class="text-muted">Unable to search news right now.</div>';
    }
}

function renderIdeaList(containerId, ideas, tone) {
    const container = document.getElementById(containerId);
    if (!ideas.length) {
        container.innerHTML = '<div class="text-muted">No ranked ideas available right now.</div>';
        return;
    }

    container.innerHTML = ideas.map((idea, index) => {
        const metrics = idea.metrics || {};
        const evidenceLinks = (idea.supportingEvidence || []).filter((item) => item.url).slice(0, 3);
        const localModel = idea.localModelAnalysis || null;
        const confidencePct = idea.confidence ? `${Math.round(idea.confidence * 100)}%` : 'n/a';
        const peText = metrics.peRatio ? `P/E ${metrics.peRatio.toFixed(1)}` : 'P/E n/a';
        const changeClass = (idea.changePercent || 0) >= 0 ? 'price-positive' : 'price-negative';
        const badge = tone === 'success' ? 'bg-success' : 'bg-danger';

        return `
            <div class="surface" onclick="searchStockFromList('${idea.symbol}')" style="cursor:pointer;">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <h6 class="fw-bold mb-1">${index + 1}. ${idea.symbol}</h6>
                        <small>${idea.companyName || 'Company'}</small>
                    </div>
                    <span class="badge ${badge}">${idea.score.toFixed ? idea.score.toFixed(0) : idea.score}</span>
                </div>
                <div class="mt-2 d-flex justify-content-between">
                    <span>$${(idea.currentPrice || 0).toFixed(2)}</span>
                    <span class="${changeClass}">${idea.changePercent >= 0 ? '+' : ''}${(idea.changePercent || 0).toFixed(2)}%</span>
                </div>
                <div class="mt-2 d-flex justify-content-between">
                    <small>${confidencePct} confidence</small>
                    <small>${peText}</small>
                </div>
                <div class="mt-2">
                    <small class="text-muted">${(idea.reasoning || []).slice(0, 2).join(' ')}</small>
                </div>
                ${localModel ? `
                    <div class="mt-2">
                        <small><strong>Local model:</strong> ${localModel.verdict || 'n/a'} - ${localModel.thesisSummary || ''}</small>
                    </div>
                ` : ''}
                ${evidenceLinks.length ? `
                    <div class="mt-2">
                        ${evidenceLinks.map((item) => `
                            <div><a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.source || 'Source'}: ${item.title}</a></div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderStoryList(containerId, stories) {
    const container = document.getElementById(containerId);
    if (!stories.length) {
        container.innerHTML = '<div class="text-muted">No current stories available.</div>';
        return;
    }

    container.innerHTML = stories.map((story) => {
        const linkedStocks = (story.linkedStocks || []).slice(0, 5);
        return `
            <div class="surface">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <h6 class="fw-semibold mb-1">${story.title}</h6>
                        <small>${story.source || 'Source'} | ${story.topic || 'Market'} | ${new Date(story.publishedAt).toLocaleString()}</small>
                    </div>
                    <span class="badge ${story.directionalBias === 'up' ? 'bg-success' : story.directionalBias === 'down' ? 'bg-danger' : 'bg-secondary'}">
                        ${story.directionalBias || 'mixed'}
                    </span>
                </div>
                <div class="pill-row">
                    ${linkedStocks.map((linked) => `
                        <span class="story-pill">${linked.symbol}: ${linked.reason}</span>
                    `).join('')}
                </div>
                ${story.url ? `<div class="mt-2"><a href="${story.url}" target="_blank" rel="noopener noreferrer">Open story</a></div>` : ''}
            </div>
        `;
    }).join('');
}

function renderPredictionScoreboard(scoreboard) {
    const container = document.getElementById('predictionScoreboard');
    const badge = document.getElementById('predictionAccuracyBadge');

    if (!scoreboard || (!scoreboard.totalIdeas && !scoreboard.pendingIdeas)) {
        container.innerHTML = '<div class="text-muted">No tracked ideas yet. Refreshing the intelligence feed will start the evaluation log.</div>';
        badge.textContent = 'Pending';
        badge.className = 'badge bg-secondary';
        return;
    }

    const accuracyText = scoreboard.accuracyPct != null ? `${scoreboard.accuracyPct}% accuracy` : 'Awaiting evaluations';
    badge.textContent = accuracyText;
    badge.className = `badge ${scoreboard.accuracyPct == null ? 'bg-secondary' : scoreboard.accuracyPct >= 55 ? 'bg-success' : 'bg-warning'}`;

    container.innerHTML = `
        <div class="row text-center g-2 mb-3">
            <div class="col-4"><strong>${scoreboard.totalIdeas || 0}</strong><div><small>Total ideas</small></div></div>
            <div class="col-4"><strong>${scoreboard.evaluatedIdeas || 0}</strong><div><small>Evaluated</small></div></div>
            <div class="col-4"><strong>${scoreboard.pendingIdeas || 0}</strong><div><small>Pending</small></div></div>
        </div>
        <div class="story-list">
            ${(scoreboard.recentIdeas || []).slice(0, 4).map((idea) => `
                <div class="surface">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${idea.symbol} ${idea.direction === 'up' ? 'up' : 'down'}</h6>
                            <small>${idea.topic} | ${idea.catalyst}</small>
                        </div>
                        <span class="badge ${idea.status === 'correct' ? 'bg-success' : idea.status === 'incorrect' ? 'bg-danger' : 'bg-secondary'}">${idea.status}</span>
                    </div>
                    <div class="mt-2"><small>${idea.evaluationNotes || 'Waiting for the holding window to complete.'}</small></div>
                </div>
            `).join('')}
        </div>
    `;
}

// Search stock from list click
function searchStockFromList(symbol) {
    document.getElementById('stockSearch').value = symbol;
    searchStock();
    
    // Scroll to analysis section
    document.getElementById('stockAnalysis').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start' 
    });
}

// Get recommendation CSS class
function getRecommendationClass(recommendation) {
    if (!recommendation) return '';
    
    const rec = recommendation.toLowerCase();
    if (rec.includes('buy')) return 'recommendation-buy';
    if (rec.includes('sell')) return 'recommendation-sell';
    return 'recommendation-hold';
}

// Get score color class
function getScoreColor(score) {
    if (!score) return 'bg-secondary';
    
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-warning';
    return 'bg-danger';
}

// Check system health
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/v1/monitoring/health`);
        
        if (response.ok) {
            const health = await response.json();
            updateSystemStatus(health);
        } else {
            throw new Error('Health check failed');
        }
    } catch (error) {
        console.error('Health check error:', error);
        updateSystemStatus(null);
    }
}

// Update system status display
function updateSystemStatus(health) {
    const apiStatus = document.getElementById('apiStatus');
    const dataStatus = document.getElementById('dataStatus');
    const mlStatus = document.getElementById('mlStatus');
    const telemetryStatus = document.getElementById('telemetryStatus');

    if (!health) {
        apiStatus.textContent = 'Unknown';
        apiStatus.className = 'badge bg-warning';
        dataStatus.textContent = 'Unknown';
        dataStatus.className = 'badge bg-warning';
        mlStatus.textContent = 'Unknown';
        mlStatus.className = 'badge bg-warning';
        telemetryStatus.textContent = 'Telemetry Unknown';
        telemetryStatus.className = 'badge bg-warning';
        return;
    }

    const subsystems = health.subsystems || {};
    applyStatusBadge(apiStatus, subsystems.api?.status, {
        healthy: 'Online',
        degraded: 'Degraded',
        unhealthy: 'Offline',
        idle: 'Online'
    });
    applyStatusBadge(dataStatus, subsystems.data?.status, {
        healthy: 'Active',
        degraded: 'Limited',
        unhealthy: 'Inactive',
        idle: 'Active'
    });
    applyStatusBadge(mlStatus, subsystems.ml?.status, {
        healthy: 'Running',
        degraded: 'Partial',
        unhealthy: 'Stopped',
        idle: 'Idle'
    });
    applyStatusBadge(telemetryStatus, subsystems.observability?.status, {
        healthy: 'Telemetry Tracking',
        degraded: 'Telemetry Partial',
        unhealthy: 'Telemetry Down',
        idle: 'Telemetry Idle'
    });
}

function applyStatusBadge(element, status, labels) {
    const normalizedStatus = status || 'unknown';
    const text = labels[normalizedStatus] || 'Unknown';
    const classMap = {
        healthy: 'bg-success',
        degraded: 'bg-warning',
        unhealthy: 'bg-danger',
        idle: 'bg-secondary',
        unknown: 'bg-warning'
    };

    element.textContent = text;
    element.className = `badge ${classMap[normalizedStatus] || classMap.unknown}`;
}

// Refresh data every 30 seconds
setInterval(() => {
    checkSystemHealth();
}, 30000);

// Refresh market intelligence less frequently because it aggregates live news.
setInterval(() => {
    loadMarketIntelligence();
}, 300000);
