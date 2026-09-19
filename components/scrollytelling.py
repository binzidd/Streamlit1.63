"""Scrollytelling earnings story — Streamlit V2 component. CFO-grade, grounded in CBA FY26 data."""
from __future__ import annotations
import streamlit as st

# ---------------------------------------------------------------------------
# HTML skeleton
# ---------------------------------------------------------------------------
_HTML = '<div id="st_scroll_root" style="width:100%;"></div>'

# ---------------------------------------------------------------------------
# JS module (D3 v7) — v9
# ---------------------------------------------------------------------------
_JS = r"""
/* v11 */
export default function(component) {
    const { parentElement, data } = component;

    // ------------------------------------------------------------------ guard
    if (!data || !data.monthly || !data.monthly.length) return;

    // ----------------------------------------------------------------- cleanup
    if (parentElement._storyObserver) {
        parentElement._storyObserver.disconnect();
        parentElement._storyObserver = null;
    }
    if (parentElement._resizeObserver) {
        parentElement._resizeObserver.disconnect();
        parentElement._resizeObserver = null;
    }
    if (parentElement._unloadHandler) {
        window.removeEventListener('unload', parentElement._unloadHandler);
        parentElement._unloadHandler = null;
    }
    if (parentElement._styleEl) {
        parentElement._styleEl.remove();
        parentElement._styleEl = null;
    }
    // Remove stale kpiGrid if present from a previous render
    if (parentElement._kpiGrid) {
        try { parentElement._kpiGrid.remove(); } catch(e) {}
        parentElement._kpiGrid = null;
    }
    // Remove stale scroll handler from a previous render
    if (parentElement._scrollHandler && parentElement._scrollEl) {
        parentElement._scrollEl.removeEventListener('scroll', parentElement._scrollHandler);
        parentElement._scrollHandler = null;
        parentElement._scrollEl = null;
    }
    const root = parentElement.querySelector('#st_scroll_root');
    if (!root) return;
    root.innerHTML = '';

    const viewH    = window.innerHeight || 900;
    const monthly  = data.monthly  || [];
    const stock    = data.stock    || [];
    const kpis      = data.kpis      || {};
    const real_kpis = data.real_kpis || {};  // passed from Python REAL_KPIS dict; available for future use
    const segments  = data.segments  || [];

    // ---------------------------------------------------------------- D3 load
    function loadD3() {
        return new Promise(function(resolve, reject) {
            if (window.d3) { resolve(); return; }
            var existing = document.querySelector('script[data-d3]');
            if (existing) {
                if (window.d3) { resolve(); return; }
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
                if (existing.readyState === 'loaded' || existing.readyState === 'complete') {
                    reject(new Error('d3 load failed'));
                }
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-d3', '1');
            s.src = 'https://unpkg.com/d3@7/dist/d3.min.js';
            s.onload  = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    // ---------------------------------------------------------------- d3-sankey load
    function loadD3Sankey() {
        return new Promise(function(resolve, reject) {
            if (window.d3 && window.d3.sankey) {
                window.d3sankey = window.d3;
                resolve();
                return;
            }
            var existing = document.querySelector('script[data-d3sankey]');
            if (existing) {
                if (window.d3 && window.d3.sankey) {
                    window.d3sankey = window.d3;
                    resolve();
                    return;
                }
                existing.addEventListener('load', function() {
                    window.d3sankey = window.d3;
                    resolve();
                });
                existing.addEventListener('error', reject);
                if (existing.readyState === 'loaded' || existing.readyState === 'complete') {
                    if (window.d3 && window.d3.sankey) {
                        window.d3sankey = window.d3;
                        resolve();
                    } else {
                        reject(new Error('d3-sankey load failed'));
                    }
                }
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-d3sankey', '1');
            s.src = 'https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js';
            s.onload = function() {
                window.d3sankey = window.d3;
                resolve();
            };
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    loadD3().then(buildStory).catch(function() {
        root.innerHTML = '<p style="color:red;padding:12px;">D3 failed to load.</p>';
    });

    // Return teardown to V2 component runtime
    return function() {
        if (parentElement._storyObserver) {
            parentElement._storyObserver.disconnect();
            parentElement._storyObserver = null;
        }
        if (parentElement._resizeObserver) {
            parentElement._resizeObserver.disconnect();
            parentElement._resizeObserver = null;
        }
        if (parentElement._unloadHandler) {
            window.removeEventListener('unload', parentElement._unloadHandler);
            parentElement._unloadHandler = null;
        }
        if (parentElement._styleEl) {
            parentElement._styleEl.remove();
            parentElement._styleEl = null;
        }
        if (parentElement._kpiGrid) {
            try { parentElement._kpiGrid.remove(); } catch(e) {}
            parentElement._kpiGrid = null;
        }
        if (parentElement._scrollHandler && parentElement._scrollEl) {
            parentElement._scrollEl.removeEventListener('scroll', parentElement._scrollHandler);
            parentElement._scrollHandler = null;
            parentElement._scrollEl = null;
        }
    };

    // =====================================================================
    // MAIN BUILD
    // =====================================================================
    function buildStory() {
        var d3 = window.d3;

        // ------------------------------------------------ Real CBA FY26 divisional data
        var REAL_DIV_NIM = {
            "Retail Banking Services": 2.50,
            "Business Banking": 3.39,
            "Institutional Banking and Markets": 0.87,
            "New Zealand (ASB)": 2.30
        };
        var REAL_DIV_CTI = {
            "Retail Banking Services": 39.3,
            "Business Banking": 32.2,
            "Institutional Banking and Markets": 40.6,
            "New Zealand (ASB)": 46.4
        };
        var REAL_DIV_NPAT = {
            "Retail Banking Services": 5587,
            "Business Banking": 4544,
            "Institutional Banking and Markets": 1258,
            "New Zealand (ASB)": 1112
        };

        // ------------------------------------------------ FY26 KPI scorecard data (hardcoded real values)
        var FY26_KPI_TILES = [
            { label: 'Cash NPAT',       value: '$10.98B', change: '▲7%',    up: true,  good: true,  sub: 'FY26 cash basis' },
            { label: 'NIM',             value: '2.05%',   change: '▼3bps',  up: false, good: false, sub: 'Net interest margin' },
            { label: 'CTI',             value: '45.5%',   change: '▼20bps', up: false, good: true,  sub: 'Cost-to-income ratio' },
            { label: 'ROE',             value: '14.0%',   change: '▲50bps', up: true,  good: true,  sub: 'Return on equity' },
            { label: 'CET1 (APRA)',     value: '12.0%',   change: '▼30bps', up: false, good: false, sub: 'Capital adequacy' },
            { label: 'EPS (cash)',      value: '656.9c',  change: '▲7%',    up: true,  good: true,  sub: 'Basic, continuing ops' },
            { label: 'DPS',             value: '505c',    change: '▲4%',    up: true,  good: true,  sub: 'FY26 total, fully franked' },
            { label: 'LIE rate',        value: '8bps',    change: '▲1bp',   up: true,  good: false, sub: 'Of gross loans & advances' },
            { label: 'Pre-prov. profit',value: '$16.5B',  change: '▲6%',    up: true,  good: true,  sub: 'Pre-provision profit' },
        ];

        // ------------------------------------------------ segment config
        var SEG_COLORS = {
            'Retail Banking Services':            '#2a78d6',
            'Business Banking':                   '#eb6834',
            'Institutional Banking and Markets':  '#1baf7a',
            'New Zealand (ASB)':                  '#eda100',
        };
        var SEG_SHORT = {
            'Retail Banking Services':            'Retail',
            'Business Banking':                   'Business',
            'Institutional Banking and Markets':  'IB&M',
            'New Zealand (ASB)':                  'NZ',
        };
        var SEG_KEY = {
            'Retail Banking Services':            'retail',
            'Business Banking':                   'business',
            'Institutional Banking and Markets':  'ibm',
            'New Zealand (ASB)':                  'nz',
        };
        var SEG_TINTS = {
            'Retail Banking Services':            '#2a78d61a',
            'Business Banking':                   '#eb68341a',
            'Institutional Banking and Markets':  '#1baf7a1a',
            'New Zealand (ASB)':                  '#eda1001a',
        };

        // ------------------------------------------------ step copy
        var STEPS = [
            {
                n: '00 / 07',
                headline: 'Five years. Four divisions. One unbroken growth story.',
                body: 'Australia\'s largest bank navigated a rate-hiking cycle, a credit shock, and a market re-rating — and came out ahead on every metric that matters.',
            },
            {
                n: '01 / 07',
                headline: 'Group income grew to A$30.2B in FY26',
                body: 'Group operating income rose 6% to A$30.2B, extending a compounding trajectory that delivered 24% cumulative growth from FY22. The rate-hiking cycle that began in May 2022 initially tailwinds NIM, peaked at 4.35% in November 2023, before the RBA began easing in February 2025.',
            },
            {
                n: '02 / 07',
                headline: 'Four engines power the group',
                body: 'Retail Banking leads at ~45% of income. Business Banking contributes with superior cost efficiency (CTI 32.2%). Institutional Banking & Markets delivers steady fee income. New Zealand (ASB) tracks its own domestic cycle — and was the weakest performer in FY26 (CTI +390bps).',
            },
            {
                n: '03 / 07',
                headline: 'Unstacked: divergence becomes clear',
                body: 'Retail Banking\'s scale dominates, but Business Banking\'s steeper angle reflects its higher margin efficiency (NIM 3.39%, +7bps). IB&M is the steadiest line — fee income insulates it from rate-cycle noise. New Zealand tracks its own domestic cycle with NIM compressing.',
            },
            {
                n: '04 / 07',
                headline: 'Pick a division to explore',
                body: 'Each division has a different anatomy of earnings. Click a segment below to see how its revenue, costs, and profit layer together. The next chapter defaults to Retail Banking Services if you skip.',
                interactive: true,
            },
            {
                n: '05 / 07',
                headline: 'Anatomy of earnings — FY26',
                body: 'Three forces determine every dollar of profit: net interest income on the loan book, fee and other income on top, and operating expenses that consume the stack. The gap that remains is pre-provision profit — the engine of dividends and growth.',
            },
            {
                n: '06 / 07',
                headline: 'Market verdict — share price',
                body: 'The market voted with its feet. A strong 2024 run-up driven by earnings beats pushed the stock to new highs before a mild 2025 plateau as credit normalisation concerns weighed. The cumulative return still comfortably outpaced the broader index.',
            },
            {
                n: '07 / 07',
                headline: 'FY26 in nine numbers',
                body: 'One rate cycle, a credit stress, and a market re-rating close with the bank ahead on every front. Cash NPAT rose 7% to $10.98B. ROE expanded 50bps to 14.0%. The board declared a fully franked DPS of 505 cents — up 4%.',
            },
        ];

        // ------------------------------------------------ closure state
        var selectedSeg = parentElement._selectedSeg || (segments[0] || 'Retail Banking Services');
        var currentStep = -1;
        var step4BadgesContainer = null;

        // ------------------------------------------------ scroll container
        // NOTE: position:sticky is broken inside Streamlit because multiple ancestor
        // elements have overflow:auto/hidden set by the framework.
        // SOLUTION: Use a JS-scroll-driven layout:
        //   - scrollContainer (root) is the scroll viewport (overflow-y:scroll)
        //   - inner is a flex wrapper (no overflow) that holds the full scrollable height
        //   - chartCol is position:absolute pinned to left=0,top=0 within scrollContainer
        //   - A scroll event listener updates chartCol.style.top to follow scrollTop
        //   - stepsCol is on the right with normal flow (takes the full content height)
        var scrollContainer = root;
        scrollContainer.style.cssText = [
            'position:relative',
            'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
            'background:#f8fafc',
            'overflow-y:auto',
            'height:' + viewH + 'px',
        ].join(';');

        // inner: a full-height flex wrapper
        var inner = scrollContainer;  // We use scrollContainer directly as the flex parent

        // ---- LEFT "sticky" chart column — absolutely positioned, JS-driven
        // Sits at position:absolute, left:0, top=scrollTop (updated on scroll)
        var chartCol = document.createElement('div');
        chartCol.style.cssText = [
            'width:63%',
            'position:absolute',
            'left:0',
            'top:0',
            'height:' + viewH + 'px',
            'display:flex',
            'flex-direction:column',
            'align-items:stretch',
            'padding:16px 12px 16px 24px',
            'box-sizing:border-box',
            'background:#f8fafc',
            'overflow:hidden',
            'z-index:1',
        ].join(';');
        scrollContainer.appendChild(chartCol);

        // Scroll handler: keep chartCol pinned to viewport top
        function onScrollUpdate() {
            chartCol.style.top = scrollContainer.scrollTop + 'px';
        }
        scrollContainer.addEventListener('scroll', onScrollUpdate, { passive: true });
        // Store for teardown
        parentElement._scrollHandler = onScrollUpdate;
        parentElement._scrollEl = scrollContainer;

        // ---- chart header area (title + KPI strip)
        var chartHeader = document.createElement('div');
        chartHeader.style.cssText = [
            'flex-shrink:0',
            'margin-bottom:6px',
            'padding-left:56px',
        ].join(';');
        chartCol.appendChild(chartHeader);

        // chart title
        var chartTitle = document.createElement('div');
        chartTitle.style.cssText = [
            'font-size:0.72rem',
            'font-variant:small-caps',
            'letter-spacing:0.08em',
            'color:#64748b',
            'margin-bottom:4px',
            'transition:opacity 0.4s',
        ].join(';');
        chartTitle.textContent = 'Group Operating Income — FY22 to FY26';
        chartHeader.appendChild(chartTitle);

        // ---- persistent KPI strip
        var kpiStrip = document.createElement('div');
        kpiStrip.style.cssText = [
            'font-size:10px',
            'color:#64748b',
            'letter-spacing:0.03em',
            'padding:3px 0 4px 0',
            'border-top:1px solid #e2e8f0',
            'border-bottom:1px solid #e2e8f0',
            'margin-bottom:4px',
            'white-space:nowrap',
            'overflow:hidden',
            'text-overflow:ellipsis',
        ].join(';');
        kpiStrip.innerHTML = [
            '<span style="font-weight:700;color:#0f172a;">NPAT</span> $10.98B <span style="color:#16a34a;">▲7%</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">NIM</span> 2.05% <span style="color:#dc2626;">▼3bps</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">CTI</span> 45.5% <span style="color:#16a34a;">▼20bps</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">ROE</span> 14.0% <span style="color:#16a34a;">▲50bps</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">CET1</span> 12.0% <span style="color:#dc2626;">▼30bps</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">EPS</span> 656.9c <span style="color:#16a34a;">▲7%</span>',
            '<span style="color:#cbd5e1;margin:0 6px;">|</span>',
            '<span style="font-weight:700;color:#0f172a;">DPS</span> 505c <span style="color:#16a34a;">▲4%</span>',
        ].join('');
        chartHeader.appendChild(kpiStrip);

        // SVG (fills remaining height below header)
        // Measure actual header height after DOM paint; fall back to 58px estimate
        var headerH = (chartHeader && chartHeader.offsetHeight > 0) ? chartHeader.offsetHeight : 58;
        var svgHeight = viewH - headerH - 32; // 32px = top+bottom padding
        var margin = { top: 24, right: 80, bottom: 44, left: 64 };

        var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.style.cssText = 'width:100%;height:' + svgHeight + 'px;overflow:visible;flex:1 1 auto;';
        chartCol.appendChild(svgEl);

        var svg = d3.select(svgEl);

        // ---- KPI grid (DOM tiles, overlaid on chartCol for step 7)
        var kpiGrid = document.createElement('div');
        kpiGrid.style.cssText = [
            'position:absolute',
            'top:0',
            'left:0',
            'width:100%',
            'height:100%',
            'display:none',
            'grid-template-columns:1fr 1fr 1fr',
            'grid-template-rows:1fr 1fr 1fr',
            'gap:10px',
            'padding:52px 20px 20px 20px',
            'box-sizing:border-box',
            'background:rgba(248,250,252,0.98)',
            'z-index:10',
            'align-content:center',
        ].join(';');
        chartCol.style.position = 'relative'; // ensure absolute child works
        chartCol.appendChild(kpiGrid);
        parentElement._kpiGrid = kpiGrid;

        // Build KPI tiles (static, animated on step 7 activate)
        var kpiTileEls = [];
        FY26_KPI_TILES.forEach(function(spec) {
            var tile = document.createElement('div');
            tile.style.cssText = [
                'background:white',
                'border-radius:10px',
                'padding:14px 16px',
                'border:1px solid #e2e8f0',
                'box-shadow:0 2px 8px rgba(0,0,0,0.05)',
                'display:flex',
                'flex-direction:column',
                'gap:3px',
                'min-height:0',
            ].join(';');

            var lbl = document.createElement('div');
            lbl.textContent = spec.label;
            lbl.style.cssText = 'font-size:0.68rem;font-variant:small-caps;letter-spacing:0.07em;color:#64748b;';

            var valRow = document.createElement('div');
            valRow.style.cssText = 'display:flex;align-items:baseline;gap:6px;';

            var valEl = document.createElement('div');
            valEl.textContent = spec.value;
            valEl.style.cssText = 'font-size:1.4rem;font-weight:800;color:#0f172a;line-height:1.1;';

            var chgEl = document.createElement('div');
            chgEl.textContent = spec.change;
            var chgColor = spec.good ? '#16a34a' : '#dc2626';
            chgEl.style.cssText = 'font-size:0.72rem;font-weight:700;color:' + chgColor + ';';

            valRow.appendChild(valEl);
            valRow.appendChild(chgEl);

            var subEl = document.createElement('div');
            subEl.textContent = spec.sub;
            subEl.style.cssText = 'font-size:0.63rem;color:#94a3b8;margin-top:1px;';

            tile.appendChild(lbl);
            tile.appendChild(valRow);
            tile.appendChild(subEl);
            kpiGrid.appendChild(tile);
            kpiTileEls.push({ tile: tile, valEl: valEl, spec: spec });
        });

        // KPI grid footer
        var kpiFooter = document.createElement('div');
        kpiFooter.style.cssText = [
            'grid-column:1 / -1',
            'font-size:0.6rem',
            'color:#94a3b8',
            'text-align:center',
            'align-self:end',
        ].join(';');
        kpiFooter.textContent = 'Source: CBA Profit Announcement, year ended 30 June 2026. Chart data is illustrative.';
        kpiGrid.appendChild(kpiFooter);

        // ---- RIGHT steps column (37%)
        // chartCol is position:absolute so stepsCol needs margin-left to clear it
        var stepsCol = document.createElement('div');
        stepsCol.style.cssText = [
            'width:37%',
            'margin-left:63%',
            'box-sizing:border-box',
            'padding:18vh 20px 80px 14px',
            'pointer-events:all',
        ].join(';');
        scrollContainer.appendChild(stepsCol);

        // inject badge button styles
        var styleEl = document.createElement('style');
        styleEl.textContent = [
            '.seg-badge {',
            '  cursor:pointer;',
            '  border-radius:20px;',
            '  padding:9px 16px;',
            '  font-weight:600;',
            '  font-size:0.80rem;',
            '  margin:4px;',
            '  min-height:40px;',
            '  transition:background 0.2s, color 0.2s, opacity 0.2s;',
            '  pointer-events:all;',
            '}',
            '.seg-badge:hover { filter:brightness(0.92); }',
            '.seg-badge.active { color:white !important; }',
        ].join('\n');
        document.head.appendChild(styleEl);
        parentElement._styleEl = styleEl;

        var stepEls = [];

        STEPS.forEach(function(step, i) {
            var card = document.createElement('div');
            card.dataset.step = String(i);
            var cardMinH = Math.round(viewH * 0.88);
            card.style.cssText = [
                'background:white',
                'border-radius:12px',
                'padding:20px 22px',
                'border:1px solid #e2e8f0',
                'margin-bottom:24px',
                'min-height:' + cardMinH + 'px',
                'display:flex',
                'flex-direction:column',
                'justify-content:center',
                'opacity:' + (i === 0 ? '1' : '0.35'),
                'transition:opacity 0.4s',
                'pointer-events:all',
            ].join(';');

            var counter = document.createElement('div');
            counter.textContent = step.n;
            counter.style.cssText = 'font-variant:small-caps;font-size:0.70rem;letter-spacing:0.08em;color:#94a3b8;margin-bottom:10px;';

            var headline = document.createElement('div');
            headline.textContent = step.headline;
            headline.style.cssText = 'font-size:1.15rem;font-weight:800;color:#0f172a;line-height:1.35;margin-bottom:12px;';

            var body = document.createElement('div');
            body.textContent = step.body;
            body.style.cssText = 'font-size:0.85rem;color:#475569;line-height:1.7;';

            card.appendChild(counter);
            card.appendChild(headline);
            card.appendChild(body);

            // Step 4 interactive badges
            if (step.interactive) {
                var hint = document.createElement('div');
                hint.style.cssText = 'font-size:0.76rem;color:#64748b;font-style:italic;margin-top:18px;margin-bottom:8px;';
                hint.textContent = 'Tap a segment to explore its earnings anatomy:';
                card.appendChild(hint);

                var badgesWrap = document.createElement('div');
                badgesWrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;pointer-events:all;';
                step4BadgesContainer = badgesWrap;

                segments.forEach(function(seg) {
                    var col = SEG_COLORS[seg] || '#888';
                    var btn = document.createElement('button');
                    btn.className = 'seg-badge';
                    btn.textContent = SEG_SHORT[seg] || seg;
                    btn.style.background = SEG_TINTS[seg] || '#eee';
                    btn.style.border = '1px solid ' + col + '44';
                    btn.style.borderLeft = '4px solid ' + col;
                    btn.style.color = '#0f172a';
                    btn.style.opacity = '1';
                    btn.dataset.seg = seg;
                    btn.addEventListener('click', function(event) {
                        event.stopPropagation();
                        selectSegment(seg);
                        highlightSelected(seg);
                    });
                    badgesWrap.appendChild(btn);
                });

                card.appendChild(badgesWrap);
            }

            stepsCol.appendChild(card);
            stepEls.push(card);
        });

        // ======================================================================
        // D3 scales + axes
        // ======================================================================
        requestAnimationFrame(function() {

        var parseDate = d3.timeParse('%Y-%m-%d');

        var parsedMonthly = monthly.map(function(d) {
            return Object.assign({}, d, { _date: parseDate(d.date) });
        }).filter(function(d) { return d._date; });

        var parsedStock = stock.map(function(d) {
            return { _date: parseDate(d.date), value: +d.value };
        }).filter(function(d) { return d._date; });

        function getW() { return svgEl.getBoundingClientRect().width || 640; }
        function innerW() { return getW() - margin.left - margin.right; }
        function innerH() { return svgHeight - margin.top - margin.bottom; }

        // Unified X domain across all data
        var allDates = parsedMonthly.map(function(d) { return d._date; })
            .concat(parsedStock.map(function(d) { return d._date; }));
        var xScale = d3.scaleTime()
            .domain(d3.extent(allDates))
            .range([margin.left, getW() - margin.right]);

        // Y scales
        var maxIncome = d3.max(parsedMonthly, function(d) { return +d.operating_income; }) || 1;
        var yScaleIncome = d3.scaleLinear()
            .domain([0, maxIncome * 1.12])
            .range([svgHeight - margin.bottom, margin.top]);

        var maxSegVal = d3.max(segments, function(seg) {
            return d3.max(parsedMonthly, function(d) { return +d[seg] || 0; });
        }) || maxIncome * 0.5;
        var yScaleSegs = d3.scaleLinear()
            .domain([0, maxSegVal * 1.18])
            .range([svgHeight - margin.bottom, margin.top]);

        var maxStock = d3.max(parsedStock, function(d) { return d.value; }) || 1;
        var minStock = d3.min(parsedStock, function(d) { return d.value; }) || 0;
        var yScaleStock = d3.scaleLinear()
            .domain([minStock * 0.95, maxStock * 1.05])
            .range([svgHeight - margin.bottom, margin.top]);

        var _lastYScale = yScaleIncome;

        var g = svg.append('g');

        // ---- gridlines
        var gridG = g.append('g').attr('class', 'grid');

        function drawGridlines(yScale) {
            var ticks = yScale.ticks(6);
            gridG.selectAll('line')
                .data(ticks)
                .join('line')
                .attr('x1', margin.left)
                .attr('x2', getW() - margin.right)
                .attr('y1', function(d) { return yScale(d); })
                .attr('y2', function(d) { return yScale(d); })
                .attr('stroke', '#e2e8f0')
                .attr('stroke-opacity', 0.3)
                .attr('stroke-dasharray', '4,3')
                .attr('stroke-width', 1);
        }
        drawGridlines(yScaleIncome);

        // ---- X axis
        var xAxisG = g.append('g')
            .attr('transform', 'translate(0,' + (svgHeight - margin.bottom) + ')')
            .call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
        xAxisG.select('.domain').remove();
        xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        xAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        // ---- Y axis
        var incFmt = function(d) {
            return 'A$' + d3.format('.2s')(d).replace('G','B').replace('M','M');
        };
        var yAxisG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',0)')
            .call(d3.axisLeft(yScaleIncome).ticks(6).tickFormat(incFmt).tickSizeOuter(0));
        yAxisG.select('.domain').remove();
        yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        yAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        function styleYAxis(yScale, isStock) {
            _lastYScale = yScale;
            var fmt = isStock
                ? function(d) { return 'A$' + d.toFixed(0); }
                : function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B').replace('M','M'); };
            yAxisG.transition().duration(600).ease(d3.easeCubicInOut)
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(fmt).tickSizeOuter(0))
                .on('end', function() {
                    yAxisG.select('.domain').remove();
                    yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                    yAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                });
        }

        // =====================================================================
        // STEP 1: total income area + line (navy) + event annotations
        // =====================================================================
        var totalAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(yScaleIncome(0))
            .y1(function(d) { return yScaleIncome(+d.operating_income); })
            .curve(d3.curveMonotoneX);

        var totalLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleIncome(+d.operating_income); })
            .curve(d3.curveMonotoneX);

        var totalAreaPath = g.append('path')
            .datum(parsedMonthly)
            .attr('fill', 'rgba(30,58,95,0.09)')
            .attr('d', totalAreaGen)
            .attr('opacity', 0);

        var totalLinePath = g.append('path')
            .datum(parsedMonthly)
            .attr('fill', 'none')
            .attr('stroke', '#1e3a5f')
            .attr('stroke-width', 2.5)
            .attr('d', totalLineGen)
            .attr('opacity', 0);

        var totalLineLen = 0;
        try { totalLineLen = totalLinePath.node().getTotalLength(); } catch(e) {}
        if (totalLineLen === 0) {
            requestAnimationFrame(function() {
                try { totalLineLen = totalLinePath.node().getTotalLength(); } catch(e) {}
                totalLinePath
                    .attr('stroke-dasharray', totalLineLen + ' ' + totalLineLen)
                    .attr('stroke-dashoffset', totalLineLen);
            });
        } else {
            totalLinePath
                .attr('stroke-dasharray', totalLineLen + ' ' + totalLineLen)
                .attr('stroke-dashoffset', totalLineLen);
        }
        var totalLineAnimated = false;

        // ---- Event annotations group (fades in after line draw)
        var annotG = g.append('g').attr('opacity', 0).attr('class', 'annot-group');

        // Helper: parse annotation dates
        var annotParseDate = d3.timeParse('%Y-%m-%d');

        // Annotation definitions
        var ANNOTS = [
            { date: '2022-05-01', label: 'Rate hiking begins',  color: '#1e3a5f', desc: 'Rate hiking begins' },
            { date: '2023-11-01', label: 'Peak 4.35%',   color: '#1e3a5f', desc: 'Rates peak' },
            { date: '2025-02-01', label: 'RBA ↓ easing', color: '#16a34a', desc: 'First cut' },
        ];

        ANNOTS.forEach(function(ann) {
            var ad = annotParseDate(ann.date);
            if (!ad) return;
            var ax = xScale(ad);
            var top = margin.top;
            var bot = svgHeight - margin.bottom;

            annotG.append('line')
                .attr('x1', ax).attr('x2', ax)
                .attr('y1', top).attr('y2', bot)
                .attr('stroke', ann.color)
                .attr('stroke-width', 1)
                .attr('stroke-dasharray', '4 4');

            annotG.append('text')
                .attr('x', ax + 3)
                .attr('y', top + 4)
                .attr('font-size', '9px')
                .attr('font-weight', '600')
                .attr('fill', ann.color)
                .text(ann.label);
        });

        // Endpoint label at last data point
        var lastMonthly = parsedMonthly.length ? parsedMonthly[parsedMonthly.length - 1] : null;
        if (lastMonthly) {
            var epx = xScale(lastMonthly._date);
            var epy = yScaleIncome(+lastMonthly.operating_income);
            annotG.append('circle')
                .attr('cx', epx).attr('cy', epy)
                .attr('r', 4)
                .attr('fill', '#1e3a5f');
            annotG.append('text')
                .attr('x', epx + 8)
                .attr('y', epy)
                .attr('dy', '0.35em')
                .attr('font-size', '11px')
                .attr('font-weight', '700')
                .attr('fill', '#1e3a5f')
                .text('FY26: A$30.2B ▲6%');
        }

        // =====================================================================
        // STEP 2: ANIMATED TREEMAP — segment proportional split
        // =====================================================================
        var totalBySeg = {};
        segments.forEach(function(seg) { totalBySeg[seg] = 0; });
        parsedMonthly.forEach(function(d) {
            segments.forEach(function(seg) {
                totalBySeg[seg] += (+d[seg] || 0);
            });
        });
        var totalAll = segments.reduce(function(s, seg) { return s + totalBySeg[seg]; }, 0) || 1;

        var treemapG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            .attr('opacity', 0);

        var treemapBuilt = false;

        function buildTreemap() {
            var iW = innerW();
            var iH = innerH();
            treemapG.selectAll('*').remove();

            var rootData = {
                name: 'Group',
                children: segments.map(function(seg) {
                    return {
                        name: seg,
                        value: totalBySeg[seg],
                        npat: REAL_DIV_NPAT[seg] || 0,
                        short: SEG_SHORT[seg] || seg,
                    };
                })
            };

            var hierarchy = d3.hierarchy(rootData)
                .sum(function(d) { return d.value || 0; })
                .sort(function(a, b) { return b.value - a.value; });

            var treemapLayout = d3.treemap()
                .size([iW, iH])
                .padding(3)
                .round(true);

            treemapLayout(hierarchy);
            var leaves = hierarchy.leaves();

            var rects = treemapG.selectAll('rect.tm-rect')
                .data(leaves)
                .enter()
                .append('rect')
                .attr('class', 'tm-rect')
                .attr('x', 0).attr('y', 0)
                .attr('width', iW).attr('height', iH)
                .attr('fill', function(d) { return SEG_COLORS[d.data.name] || '#888'; })
                .attr('stroke', 'white').attr('stroke-width', 2)
                .attr('rx', 4).attr('opacity', 0);

            rects.transition().duration(200).ease(d3.easeQuadIn)
                .attr('opacity', 1)
                .transition().duration(600).ease(d3.easeCubicInOut)
                .attr('x', function(d) { return d.x0; })
                .attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
                .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); });

            var labelGs = treemapG.selectAll('g.tm-label')
                .data(leaves)
                .enter()
                .append('g')
                .attr('class', 'tm-label')
                .attr('opacity', 0)
                .attr('pointer-events', 'none');

            labelGs.each(function(d) {
                var w = d.x1 - d.x0;
                var h = d.y1 - d.y0;
                if (w < 80) return;
                var cx = d.x0 + w / 2;
                var cy = d.y0 + h / 2;
                var pct = (d.data.value / totalAll * 100).toFixed(1) + '%';
                var npat = d.data.npat ? '$' + (d.data.npat / 1000).toFixed(2) + 'B NPAT' : '';
                // Format absolute income value
                var incomeVal = d.data.value;
                var incomeStr = incomeVal > 1e9
                    ? 'A$' + (incomeVal / 1e9).toFixed(1) + 'B'
                    : 'A$' + d3.format('.3s')(incomeVal).replace('G','B');

                d3.select(this).append('text')
                    .attr('x', cx).attr('y', cy - 14)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', Math.min(13, w / 5) + 'px')
                    .attr('font-weight', '700')
                    .attr('fill', 'white')
                    .text(d.data.short);

                d3.select(this).append('text')
                    .attr('x', cx).attr('y', cy + 2)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', Math.min(11, w / 6) + 'px')
                    .attr('font-weight', '400')
                    .attr('fill', 'rgba(255,255,255,0.9)')
                    .text(incomeStr + ' · ' + pct);

                if (h > 60 && npat) {
                    d3.select(this).append('text')
                        .attr('x', cx).attr('y', cy + 16)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', Math.min(10, w / 7) + 'px')
                        .attr('font-weight', '400')
                        .attr('fill', 'rgba(255,255,255,0.75)')
                        .text(npat);
                }
            });

            labelGs.transition().delay(850).duration(400).attr('opacity', 1);
            treemapBuilt = true;
        }

        function hideTreemap() {
            treemapG.transition().duration(400).attr('opacity', 0);
        }

        // =====================================================================
        // STEP 3: STREAM GRAPH — five-year revenue flow
        // =====================================================================
        var STACK_KEYS = segments.map(function(s) { return SEG_KEY[s]; });

        var stackInput = parsedMonthly.map(function(d) {
            var row = { _date: d._date, date: d.date };
            segments.forEach(function(seg) {
                row[SEG_KEY[seg]] = +d[seg] || 0;
            });
            return row;
        });

        var streamStack = d3.stack()
            .keys(STACK_KEYS)
            .order(d3.stackOrderNone)
            .offset(d3.stackOffsetSilhouette);

        var streamSeries = streamStack(stackInput);

        var streamYExtent = [Infinity, -Infinity];
        streamSeries.forEach(function(series) {
            series.forEach(function(d) {
                if (d[0] < streamYExtent[0]) streamYExtent[0] = d[0];
                if (d[1] > streamYExtent[1]) streamYExtent[1] = d[1];
            });
        });
        if (!isFinite(streamYExtent[0])) streamYExtent = [-maxIncome * 0.5, maxIncome * 0.5];

        var yScaleStream = d3.scaleLinear()
            .domain(streamYExtent)
            .range([svgHeight - margin.bottom, margin.top]);

        var streamAreaGen = d3.area()
            .x(function(d) { return xScale(d.data._date); })
            .y0(function(d) { return yScaleStream(d[0]); })
            .y1(function(d) { return yScaleStream(d[1]); })
            .curve(d3.curveMonotoneX);

        var streamPaths   = {};
        var streamLabelBgs = {};
        var streamLabelEls = {};

        segments.forEach(function(seg, si) {
            var series = streamSeries[si];
            var col = SEG_COLORS[seg] || '#888';

            var p = g.append('path')
                .datum(series)
                .attr('fill', col)
                .attr('fill-opacity', 0.82)
                .attr('stroke', 'none')
                .attr('d', streamAreaGen)
                .attr('opacity', 0)
                .attr('class', 'stream-path')
                .attr('data-seg', seg);

            streamPaths[seg] = p;

            var bg = g.append('rect').attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.8).attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', col)
                .attr('opacity', 0).text(SEG_SHORT[seg] || seg);
            streamLabelEls[seg] = lbl;
            streamLabelBgs[seg] = bg;
        });

        function updateStreamLabels(opacity) {
            var lastIdx = stackInput.length - 1;
            if (lastIdx < 0) return;
            var lx = xScale(stackInput[lastIdx]._date) + 5;
            segments.forEach(function(seg, si) {
                var series = streamSeries[si];
                var band = series[lastIdx];
                var cy = (yScaleStream(band[0]) + yScaleStream(band[1])) / 2;
                var lbl = streamLabelEls[seg];
                var bg  = streamLabelBgs[seg];
                lbl.attr('x', lx).attr('y', cy).attr('dy', '0.35em').attr('opacity', opacity);
                try {
                    var bb = lbl.node().getBBox();
                    bg.attr('x', bb.x - 2).attr('y', bb.y - 1)
                      .attr('width', bb.width + 4).attr('height', bb.height + 2)
                      .attr('opacity', opacity * 0.85);
                } catch(e) { bg.attr('opacity', 0); }
            });
        }

        function hideStreamGraph() {
            segments.forEach(function(seg) {
                streamPaths[seg].transition().duration(400).attr('opacity', 0);
                streamLabelEls[seg].transition().duration(400).attr('opacity', 0);
                streamLabelBgs[seg].transition().duration(400).attr('opacity', 0);
            });
        }

        // =====================================================================
        // STEP 4: per-segment lines + badge highlight
        // =====================================================================
        var segLinePaths = {};
        var segLineGens  = {};
        var segAnimated  = {};
        var segLabelEls  = {};
        var segLabelBgs  = {};

        segments.forEach(function(seg) {
            var col = SEG_COLORS[seg] || '#888';
            var lineGen = d3.line()
                .x(function(d) { return xScale(d._date); })
                .y(function(d) { return yScaleSegs(+d[seg] || 0); })
                .defined(function(d) { return d[seg] != null && !isNaN(d[seg]); })
                .curve(d3.curveMonotoneX);

            segLineGens[seg] = lineGen;

            var p = g.append('path')
                .datum(parsedMonthly)
                .attr('fill', 'none')
                .attr('stroke', col)
                .attr('stroke-width', 3)
                .attr('d', lineGen)
                .attr('opacity', 0);

            var len = 0;
            try { len = p.node().getTotalLength(); } catch(e) {}
            if (len === 0) {
                (function(pRef, segRef) {
                    requestAnimationFrame(function() {
                        var l2 = 0;
                        try { l2 = pRef.node().getTotalLength(); } catch(e) {}
                        pRef.attr('stroke-dasharray', l2 + ' ' + l2)
                            .attr('stroke-dashoffset', l2);
                        segLinePaths[segRef].len = l2;
                    });
                })(p, seg);
            } else {
                p.attr('stroke-dasharray', len + ' ' + len)
                 .attr('stroke-dashoffset', len);
            }

            segLinePaths[seg] = { path: p, lineGen: lineGen, len: len };
            segAnimated[seg]  = false;

            var bg = g.append('rect').attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.85).attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', col).attr('opacity', 0)
                .text(SEG_SHORT[seg] || seg);
            segLabelEls[seg] = lbl;
            segLabelBgs[seg] = bg;
        });

        function updateSegmentLabels(opacity, yScale) {
            var yS = yScale || yScaleSegs;
            var lastRow = parsedMonthly[parsedMonthly.length - 1];
            if (!lastRow) return;
            var labelData = segments.map(function(seg) {
                return { seg: seg, y: yS(+lastRow[seg] || 0) };
            });
            labelData.sort(function(a, b) { return a.y - b.y; });
            for (var i = 1; i < labelData.length; i++) {
                if (labelData[i].y - labelData[i - 1].y < 18) {
                    labelData[i].y = labelData[i - 1].y + 18;
                }
            }
            var lx = xScale(lastRow._date) + 6;
            labelData.forEach(function(ld) {
                var el = segLabelEls[ld.seg];
                var bg = segLabelBgs[ld.seg];
                el.attr('x', lx).attr('y', ld.y).attr('dy', '0.35em').attr('opacity', opacity);
                try {
                    var bb = el.node().getBBox();
                    bg.attr('x', bb.x - 2).attr('y', bb.y - 1)
                      .attr('width', bb.width + 4).attr('height', bb.height + 2)
                      .attr('opacity', opacity * 0.9);
                } catch(e) { bg.attr('opacity', 0); }
            });
        }

        // highlight stream paths by selected segment
        function highlightSelected(seg) {
            selectedSeg = seg;
            parentElement._selectedSeg = seg;

            // Dim/highlight stream paths (if visible — step 3)
            segments.forEach(function(s) {
                var isSel = s === seg;
                streamPaths[s]
                    .transition().duration(300)
                    .attr('opacity', isSel ? 1 : 0.15)
                    .attr('stroke', isSel ? '#000' : 'none')
                    .attr('stroke-width', isSel ? 1 : 0);
            });

            // Update badges
            if (step4BadgesContainer) {
                step4BadgesContainer.querySelectorAll('.seg-badge').forEach(function(btn) {
                    var bseg = btn.dataset.seg;
                    var bcol = SEG_COLORS[bseg] || '#888';
                    if (bseg === seg) {
                        btn.classList.add('active');
                        btn.style.background = bcol;
                        btn.style.color = 'white';
                        btn.style.border = '1px solid ' + bcol;
                        btn.style.borderLeft = '4px solid ' + bcol;
                        btn.style.opacity = '1';
                    } else {
                        btn.classList.remove('active');
                        btn.style.background = SEG_TINTS[bseg] || '#eee';
                        btn.style.color = '#0f172a';
                        btn.style.border = '1px solid ' + (SEG_COLORS[bseg] || '#888') + '44';
                        btn.style.borderLeft = '4px solid ' + (SEG_COLORS[bseg] || '#888');
                        btn.style.opacity = '0.6';
                    }
                });
            }
        }

        function selectSegment(seg) {
            selectedSeg = seg;
            parentElement._selectedSeg = seg;

            // Highlight segment lines (step 4)
            segments.forEach(function(s) {
                var isSel = s === seg;
                segLinePaths[s].path
                    .transition().duration(300).ease(d3.easeQuadOut)
                    .attr('opacity', isSel ? 1 : 0.2)
                    .attr('stroke-width', isSel ? 4.5 : 2);
                segLabelEls[s].transition().duration(300).attr('opacity', isSel ? 1 : 0.15);
                segLabelBgs[s].transition().duration(300).attr('opacity', isSel ? 0.9 : 0);
            });

            // Redraw Sankey if step 5 is active
            if (currentStep === 5 && window.d3sankey) {
                chartTitle.textContent = 'How ' + (SEG_SHORT[seg] || seg) + ' turns revenue into profit — FY26';
                drawSankey();
            }
        }

        // =====================================================================
        // STEP 5: SANKEY P&L DIAGRAM — enhanced with real divisional metrics
        // =====================================================================
        var sankeyG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            .attr('opacity', 0);

        function computeSankeyData(seg) {
            var key = SEG_KEY[seg] || 'retail';
            var totalNii   = Math.max(d3.sum(parsedMonthly, function(d) { return +d['nii_'   + key] || 0; }), 1);
            var totalOther = Math.max(d3.sum(parsedMonthly, function(d) { return +d['other_' + key] || 0; }), 1);
            var totalOpex  = d3.sum(parsedMonthly, function(d) { return +d['opex_'  + key] || 0; });
            var totalLie   = d3.sum(parsedMonthly, function(d) { return +d['lie_'   + key] || 0; });
            var totalRev   = totalNii + totalOther;
            var preProvision = Math.max(totalRev - totalOpex, 0);
            var opexLink = totalRev - preProvision;
            var npat = Math.max(preProvision - totalLie, 0);
            var lieLink = preProvision - npat;

            return {
                totalNii: totalNii, totalOther: totalOther,
                opexLink: opexLink, lieLink: lieLink,
                totalRev: totalRev, preProvision: preProvision, npat: npat,
            };
        }

        function formatSankeyValue(v) {
            return 'A$' + d3.format('.3s')(v).replace('G','B').replace('M','M');
        }

        function drawSankey() {
            if (!window.d3sankey) return;
            var dsk = window.d3sankey;
            var iW  = innerW();
            var iH  = innerH();
            var seg = selectedSeg;
            var segCol = SEG_COLORS[seg] || '#2a78d6';
            var sd = computeSankeyData(seg);

            // Real metrics for annotations
            var divNim = REAL_DIV_NIM[seg];
            var divCti = REAL_DIV_CTI[seg];
            var divNpat = REAL_DIV_NPAT[seg];
            var divNimStr = divNim != null ? 'NIM ' + divNim.toFixed(2) + '%' : '';
            var divCtiStr = divCti != null ? 'CTI ' + divCti.toFixed(1) + '%' : '';

            sankeyG.selectAll('*').remove();

            var nodeData = [
                { name: 'Net Interest Income' },   // 0
                { name: 'Fee & Other Income' },    // 1
                { name: 'Gross Revenue' },          // 2
                { name: 'Operating Expenses' },    // 3
                { name: 'Pre-Provision Profit' },  // 4
                { name: 'Loan Impairment' },        // 5
                { name: 'Cash NPAT' },              // 6
            ];

            var linkData = [
                { source: 0, target: 2, value: sd.totalNii },
                { source: 1, target: 2, value: sd.totalOther },
                { source: 2, target: 3, value: sd.opexLink },
                { source: 2, target: 4, value: sd.preProvision },
                { source: 4, target: 5, value: sd.lieLink },
                { source: 4, target: 6, value: sd.npat },
            ];

            var sankeyLayout = dsk.sankey()
                .nodeWidth(20)
                .nodePadding(24)
                .extent([[24, 24], [iW - 24, iH - 24]]);

            var graph;
            try {
                graph = sankeyLayout({
                    nodes: nodeData.map(function(d) { return Object.assign({}, d); }),
                    links: linkData.map(function(d) { return Object.assign({}, d); })
                });
            } catch(e) { return; }

            var nodes = graph.nodes;
            var links = graph.links;

            function nodeColor(i) {
                if (i === 0 || i === 1) return '#0d9488';
                if (i === 2) return segCol;
                if (i === 3 || i === 5) return '#dc2626';
                return '#16a34a';
            }

            function linkColor(link) {
                var ti = link.target.index !== undefined ? link.target.index : link.target;
                if (ti === 3 || ti === 5) return 'rgba(220,38,38,0.32)';
                return d3.color(segCol) ? d3.color(segCol).copy({opacity: 0.38}).formatRgb() : segCol + '66';
            }

            var linkPath = dsk.sankeyLinkHorizontal();

            var linkEls = sankeyG.append('g').attr('class', 'sankey-links')
                .selectAll('path')
                .data(links)
                .enter()
                .append('path')
                .attr('d', linkPath)
                .attr('stroke', function(d) { return linkColor(d); })
                .attr('stroke-width', function(d) { return Math.max(1, d.width); })
                .attr('fill', 'none')
                .attr('opacity', 0);

            linkEls.transition().duration(500)
                .delay(function(d, i) { return i * 100; })
                .ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            var nodeEls = sankeyG.append('g').attr('class', 'sankey-nodes')
                .selectAll('rect')
                .data(nodes)
                .enter()
                .append('rect')
                .attr('x', function(d) { return d.x0; })
                .attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return d.x1 - d.x0; })
                .attr('height', function(d) { return Math.max(1, d.y1 - d.y0); })
                .attr('fill', function(d, i) { return nodeColor(i); })
                .attr('rx', 3)
                .attr('opacity', 0);

            nodeEls.transition().duration(400).attr('opacity', 1);

            var nodeLabelG = sankeyG.append('g').attr('class', 'sankey-node-labels');
            nodes.forEach(function(d, i) {
                var isRight = d.x0 > iW / 2;
                var lx = isRight ? d.x1 + 6 : d.x0 - 6;
                var ly = (d.y0 + d.y1) / 2;
                var anchor = isRight ? 'start' : 'end';

                nodeLabelG.append('text')
                    .attr('x', lx).attr('y', ly - 8)
                    .attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', '10px')
                    .attr('font-weight', '700')
                    .attr('fill', '#334155')
                    .attr('opacity', 0)
                    .text(d.name)
                    .transition().delay(600).duration(400).attr('opacity', 1);

                nodeLabelG.append('text')
                    .attr('x', lx).attr('y', ly + 5)
                    .attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', '9px')
                    .attr('font-weight', '400')
                    .attr('fill', '#64748b')
                    .attr('opacity', 0)
                    .text(formatSankeyValue(d.value || 0))
                    .transition().delay(700).duration(400).attr('opacity', 1);

                // Annotate NII node with NIM, NPAT node with NPAT
                if (i === 0 && divNimStr) {
                    nodeLabelG.append('text')
                        .attr('x', lx).attr('y', ly + 17)
                        .attr('text-anchor', anchor)
                        .attr('font-size', '8px')
                        .attr('font-weight', '600')
                        .attr('fill', '#0d9488')
                        .attr('opacity', 0)
                        .text(divNimStr)
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
                if (i === 6 && divNpat != null) {
                    var realStr = 'FY26 NPAT: $' + (divNpat / 1000).toFixed(3) + 'B';
                    nodeLabelG.append('text')
                        .attr('x', lx).attr('y', ly + 17)
                        .attr('text-anchor', anchor)
                        .attr('font-size', '8px')
                        .attr('font-weight', '600')
                        .attr('fill', '#16a34a')
                        .attr('opacity', 0)
                        .text(realStr)
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
            });

            // CTI annotation on OpEx link area
            if (divCtiStr) {
                var opexNode = nodes[3];
                if (opexNode) {
                    var ctiX = (opexNode.x0 + opexNode.x1) / 2;
                    var ctiY = (opexNode.y0 + opexNode.y1) / 2;
                    sankeyG.append('text')
                        .attr('x', ctiX).attr('y', ctiY - (opexNode.y1 - opexNode.y0) / 2 - 6)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '8px')
                        .attr('font-weight', '700')
                        .attr('fill', '#dc2626')
                        .attr('opacity', 0)
                        .text(divCtiStr)
                        .transition().delay(900).duration(400).attr('opacity', 1);
                }
            }
        }

        function hideSankey() {
            sankeyG.transition().duration(400).attr('opacity', 0);
        }

        // =====================================================================
        // STEP 6: Stock price area + line + 20-week moving average
        // =====================================================================
        var stockAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(function() { return yScaleStock(minStock * 0.95); })
            .y1(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var stockLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var stockAreaPath = g.append('path')
            .datum(parsedStock)
            .attr('fill', 'rgba(15,76,129,0.11)')
            .attr('d', stockAreaGen)
            .attr('opacity', 0);

        var stockLinePath = g.append('path')
            .datum(parsedStock)
            .attr('fill', 'none')
            .attr('stroke', '#0F4C81')
            .attr('stroke-width', 2)
            .attr('d', stockLineGen)
            .attr('opacity', 0);

        var stockLineLen = 0;
        try { stockLineLen = stockLinePath.node().getTotalLength(); } catch(e) {}
        if (stockLineLen === 0) {
            requestAnimationFrame(function() {
                try { stockLineLen = stockLinePath.node().getTotalLength(); } catch(e) {}
                stockLinePath
                    .attr('stroke-dasharray', stockLineLen + ' ' + stockLineLen)
                    .attr('stroke-dashoffset', stockLineLen);
            });
        } else {
            stockLinePath
                .attr('stroke-dasharray', stockLineLen + ' ' + stockLineLen)
                .attr('stroke-dashoffset', stockLineLen);
        }
        var stockAnimated = false;

        // 20-week moving average
        var movingAvgData = parsedStock.map(function(d, i) {
            var w20 = parsedStock.slice(Math.max(0, i - 19), i + 1);
            return { _date: d._date, value: d3.mean(w20, function(x) { return x.value; }) };
        });

        var maLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var maLine = g.append('path')
            .datum(movingAvgData)
            .attr('fill', 'none')
            .attr('stroke', '#f97316')
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '5,3')
            .attr('d', maLineGen)
            .attr('opacity', 0);

        var maLabelEl = null;
        if (movingAvgData.length > 0) {
            var lastMa = movingAvgData[movingAvgData.length - 1];
            maLabelEl = g.append('text')
                .attr('x', xScale(lastMa._date) + 6)
                .attr('y', yScaleStock(lastMa.value))
                .attr('dy', '0.35em')
                .attr('font-size', '10px')
                .attr('font-weight', '700')
                .attr('fill', '#f97316')
                .attr('opacity', 0)
                .text('20-wk MA');
        }

        var peakRow = parsedStock.length
            ? parsedStock.reduce(function(a, b) { return b.value > a.value ? b : a; })
            : null;
        var peakAnnotG = g.append('g').attr('opacity', 0);
        if (peakRow) {
            var px = xScale(peakRow._date);
            var py = yScaleStock(peakRow.value);
            peakAnnotG.append('line')
                .attr('x1', px).attr('x2', px)
                .attr('y1', py).attr('y2', py + 30)
                .attr('stroke', '#0F4C81').attr('stroke-width', 1).attr('stroke-dasharray', '3,2');
            peakAnnotG.append('text')
                .attr('x', px).attr('y', py - 6)
                .attr('text-anchor', 'middle')
                .attr('font-size', '0.6rem').attr('font-weight', '700')
                .attr('fill', '#0F4C81').text('FY24 peak');
        }

        // =====================================================================
        // HELPER: hide all data elements
        // =====================================================================
        function hideAll(fast) {
            var dur = fast ? 200 : 400;
            totalAreaPath.transition().duration(dur).attr('opacity', 0);
            totalLinePath.transition().duration(dur).attr('opacity', 0);
            annotG.transition().duration(dur).attr('opacity', 0);
            hideTreemap();
            hideStreamGraph();
            segments.forEach(function(seg) {
                segLinePaths[seg].path.transition().duration(dur).attr('opacity', 0);
                segLabelEls[seg].transition().duration(dur).attr('opacity', 0);
                segLabelBgs[seg].transition().duration(dur).attr('opacity', 0);
            });
            hideSankey();
            stockAreaPath.transition().duration(dur).attr('opacity', 0);
            stockLinePath.transition().duration(dur).attr('opacity', 0);
            maLine.transition().duration(dur).attr('opacity', 0);
            if (maLabelEl) maLabelEl.transition().duration(dur).attr('opacity', 0);
            peakAnnotG.transition().duration(dur).attr('opacity', 0);
            kpiGrid.style.display = 'none';
            svg.style('opacity', '1');
        }

        // =====================================================================
        // STEP ACTIVATIONS
        // =====================================================================
        function activateStep(idx) {
            stepEls.forEach(function(el, i) {
                el.style.opacity = i === idx ? '1' : '0.35';
            });

            var t = d3.transition().duration(400).ease(d3.easeCubicInOut);

            // --- Step 0: empty axes ---
            if (idx === 0) {
                chartTitle.textContent = 'Group Operating Income — FY22 to FY26';
                chartTitle.style.opacity = '1';
                hideAll(false);
                totalLineAnimated = false;
                stockAnimated = false;
                segments.forEach(function(seg) { segAnimated[seg] = false; });
                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);
                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);

            // --- Step 1: total income area + line + annotations ---
            } else if (idx === 1) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                hideTreemap();
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0)
                        .attr('stroke-dashoffset', segLinePaths[seg].len);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                    segAnimated[seg] = false;
                });
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);

                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

                totalAreaPath.transition(t).attr('opacity', 1);
                if (!totalLineAnimated) {
                    totalLineAnimated = true;
                    totalLinePath.attr('opacity', 1)
                        .attr('stroke-dashoffset', totalLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            // Fade in annotations after line draws
                            annotG.transition().duration(500).attr('opacity', 1);
                        });
                } else {
                    totalLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            annotG.transition().duration(400).attr('opacity', 1);
                        });
                }

            // --- Step 2: animated treemap ---
            } else if (idx === 2) {
                chartTitle.textContent = 'Group Operating Income — proportional split';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition().duration(300).attr('opacity', 0);
                totalLinePath.transition().duration(300).attr('opacity', 0);
                annotG.transition().duration(300).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition().duration(300).attr('opacity', 0);
                    segLabelEls[seg].transition().duration(300).attr('opacity', 0);
                    segLabelBgs[seg].transition().duration(300).attr('opacity', 0);
                });
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 0);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                treemapG.attr('opacity', 1);
                if (!treemapBuilt) { buildTreemap(); }

            // --- Step 3: stream graph ---
            } else if (idx === 3) {
                chartTitle.textContent = 'Revenue streams — five-year flow';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                annotG.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                // Keep _lastYScale current for resize/gridline accuracy even though axis is hidden
                styleYAxis(yScaleStream, false);
                // Hide axis labels after scale update (stream graph shows no Y axis)
                yAxisG.transition().duration(0).attr('opacity', 0);

                segments.forEach(function(seg, si) {
                    streamPaths[seg]
                        .transition().delay(si * 80).duration(700).ease(d3.easeCubicInOut)
                        .attr('opacity', 0.82);
                });
                setTimeout(function() { if (currentStep === 3) { updateStreamLabels(1); } }, 900);

            // --- Step 4: interactive badge selection ---
            } else if (idx === 4) {
                chartTitle.textContent = 'Segment Operating Income';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                annotG.transition(t).attr('opacity', 0);
                hideStreamGraph();
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);
                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

                var resetT = d3.transition().duration(400).ease(d3.easeCubicInOut);
                segments.forEach(function(seg) {
                    var lp = segLinePaths[seg];
                    lp.path.transition(resetT)
                        .attr('opacity', 0.85)
                        .attr('stroke-width', 3)
                        .attr('stroke-dashoffset', 0);
                });
                updateSegmentLabels(1, yScaleSegs);

                // Apply badge highlight state synchronously to avoid flash
                highlightSelected(selectedSeg);

                // Animate the chart lines after a short delay
                setTimeout(function() {
                    if (currentStep === 4) {
                        selectSegment(selectedSeg);
                    }
                }, 450);

            // --- Step 5: Sankey P&L diagram ---
            } else if (idx === 5) {
                var seg = selectedSeg;
                chartTitle.textContent = 'How ' + (SEG_SHORT[seg] || seg) + ' turns revenue into profit — FY26';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                annotG.transition(t).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(s) {
                    segLinePaths[s].path.transition(t).attr('opacity', 0);
                    segLabelEls[s].transition(t).attr('opacity', 0);
                    segLabelBgs[s].transition(t).attr('opacity', 0);
                });
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 0);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                hideSankey();
                sankeyG.selectAll('*').remove();
                sankeyG.attr('opacity', 0);

                function doDrawSankey() {
                    drawSankey();
                    sankeyG.transition().duration(300).attr('opacity', 1);
                }

                if (window.d3sankey) {
                    doDrawSankey();
                } else {
                    loadD3Sankey().then(doDrawSankey).catch(function() {
                        chartTitle.textContent = 'Sankey chart failed to load';
                    });
                }

            // --- Step 6: share price + moving average ---
            } else if (idx === 6) {
                chartTitle.textContent = 'Share Price (A$)';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                annotG.transition(t).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideSankey();
                kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);
                styleYAxis(yScaleStock, true);
                drawGridlines(yScaleStock);

                stockAreaPath.transition(t).attr('opacity', 1);
                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0);
                    peakAnnotG.transition().delay(1000).duration(400).attr('opacity', 1);
                    maLine.transition().delay(700).duration(600).ease(d3.easeCubicOut).attr('opacity', 0.9);
                    if (maLabelEl) maLabelEl.transition().delay(1200).duration(400).attr('opacity', 1);
                } else {
                    stockLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    peakAnnotG.transition(t).attr('opacity', 1);
                    maLine.transition(t).attr('opacity', 0.9);
                    if (maLabelEl) maLabelEl.transition(t).attr('opacity', 1);
                }

            // --- Step 7: CFO KPI dashboard ---
            } else if (idx === 7) {
                chartTitle.textContent = 'CBA FY26 — Key Performance Indicators';
                chartTitle.style.opacity = '1';

                // Hide all SVG content
                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                annotG.transition(t).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                xAxisG.transition(t).attr('opacity', 0);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                // Show KPI grid, hide SVG
                svg.style('opacity', '0');
                kpiGrid.style.display = 'grid';

                // Staggered tile pop-in animation
                kpiTileEls.forEach(function(item, ci) {
                    var tile = item.tile;
                    tile.style.transform = 'translateY(12px)';
                    tile.style.opacity = '0';
                    tile.style.transition = 'none';
                    setTimeout(function() {
                        tile.style.transition = 'transform 0.4s ease, opacity 0.4s ease';
                        tile.style.transform = 'translateY(0)';
                        tile.style.opacity = '1';
                    }, ci * 70);
                });
            }
        }

        // ======================================================================
        // IntersectionObserver
        // ======================================================================
        var _rafPending   = false;
        var _pendingEntries = [];

        var observer = new IntersectionObserver(
            function(entries) {
                entries.forEach(function(e) { _pendingEntries.push(e); });
                if (!_rafPending) {
                    _rafPending = true;
                    requestAnimationFrame(function() {
                        _rafPending = false;
                        var best = null;
                        _pendingEntries.forEach(function(e) {
                            if (e.isIntersecting) {
                                if (!best || e.intersectionRatio > best.intersectionRatio) best = e;
                            }
                        });
                        _pendingEntries = [];
                        if (best) {
                            var idx = parseInt(best.target.getAttribute('data-step'), 10);
                            if (idx !== currentStep) {
                                currentStep = idx;
                                activateStep(idx);
                            }
                        }
                    });
                }
            },
            { root: scrollContainer, threshold: 0.3 }
        );

        stepEls.forEach(function(el, i) {
            el.setAttribute('data-step', String(i));
            observer.observe(el);
        });

        parentElement._storyObserver = observer;

        // ResizeObserver
        if (window.ResizeObserver) {
            var ro = new ResizeObserver(function() {
                var newW = getW();
                xScale.range([margin.left, newW - margin.right]);
                xAxisG.call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
                xAxisG.select('.domain').remove();
                xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                xAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                if (_lastYScale) drawGridlines(_lastYScale);

                totalAreaPath.attr('d', totalAreaGen);
                totalLinePath.attr('d', totalLineGen);
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.attr('d', segLinePaths[seg].lineGen);
                    streamPaths[seg].attr('d', streamAreaGen);
                });
                stockAreaPath.attr('d', stockAreaGen);
                stockLinePath.attr('d', stockLineGen);
                maLine.attr('d', maLineGen);
                if (maLabelEl && movingAvgData.length > 0) {
                    var lMa = movingAvgData[movingAvgData.length - 1];
                    maLabelEl.attr('x', xScale(lMa._date) + 6).attr('y', yScaleStock(lMa.value));
                }
                if (peakRow) {
                    var rpx = xScale(peakRow._date);
                    var rpy = yScaleStock(peakRow.value);
                    peakAnnotG.select('line').attr('x1', rpx).attr('x2', rpx).attr('y1', rpy).attr('y2', rpy + 30);
                    peakAnnotG.select('text').attr('x', rpx).attr('y', rpy - 6);
                }
                if (currentStep === 3) { updateStreamLabels(1); }
                if (currentStep === 4) { updateSegmentLabels(1, yScaleSegs); }
                if (currentStep === 2) { treemapBuilt = false; buildTreemap(); }
                if (currentStep === 5 && window.d3sankey) { drawSankey(); }
            });
            ro.observe(svgEl);
            parentElement._resizeObserver = ro;
        }

        // Initial activation
        currentStep = -1;
        activateStep(0);

        var _unloadHandler = function() { observer.disconnect(); };
        window.addEventListener('unload', _unloadHandler);
        parentElement._unloadHandler = _unloadHandler;

        }); // end requestAnimationFrame
    }
}
"""

_scrollytelling_component = st.components.v2.component(
    "scrollytelling",
    html=_HTML,
    js=_JS,
    isolate_styles=False,
)


def st_scrollytelling(
    data: dict,
    *,
    key: str = "scrollytelling",
    height: int = 900,
) -> None:
    """Render the five-year earnings scrollytelling narrative as a Streamlit V2 component.

    Parameters
    ----------
    data:
        Dictionary with keys:
            monthly  — list of dicts {date, operating_income, cash_npat, <segment cols>,
                        nii_retail, other_retail, opex_retail, lie_retail,
                        nii_business, other_business, opex_business, lie_business,
                        nii_ibm, other_ibm, opex_ibm, lie_ibm,
                        nii_nz, other_nz, opex_nz, lie_nz}
            stock    — list of dicts {date, value}
            kpis     — dict with share_price, pe_ratio, div_yield, eps,
                        annual_income_b, annual_npat_b, income_growth_pct, price_growth_pct
            segments — list[str] segment names in display order
    key:
        Unique Streamlit component key.
    height:
        Pixel height reserved by Streamlit. Uses window.innerHeight for layout.
        Defaults to 900px.
    """
    _scrollytelling_component(
        data=data,
        default=None,
        key=key,
        height=height,
    )
