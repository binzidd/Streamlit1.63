"""Scrollytelling earnings story — Streamlit V2 component. Part-to-whole + interactive drill-down."""
from __future__ import annotations
import streamlit as st

# ---------------------------------------------------------------------------
# HTML skeleton
# ---------------------------------------------------------------------------
_HTML = '<div id="st_scroll_root" style="width:100%;"></div>'

# ---------------------------------------------------------------------------
# JS module (D3 v7)
# ---------------------------------------------------------------------------
_JS = r"""
/* v8 */
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
    const root = parentElement.querySelector('#st_scroll_root');
    if (!root) return;
    root.innerHTML = '';

    const viewH    = window.innerHeight || 800;
    const monthly  = data.monthly  || [];
    const stock    = data.stock    || [];
    const kpis     = data.kpis     || {};
    const segments = data.segments || [];

    // ---------------------------------------------------------------- D3 load
    function loadD3() {
        return new Promise(function(resolve, reject) {
            if (window.d3) { resolve(); return; }
            var existing = document.querySelector('script[data-d3]');
            if (existing) {
                if (window.d3) { resolve(); return; }
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
                // Guard: script already completed but window.d3 still missing
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
    // d3-sankey@0.12.3 exports into window.d3 (adds .sankey, .sankeyLinkHorizontal etc.)
    // so after load we alias window.d3sankey = window.d3 so callers can use dsk.sankey().
    function loadD3Sankey() {
        return new Promise(function(resolve, reject) {
            // Already loaded: window.d3.sankey is available
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
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-d3sankey', '1');
            s.src = 'https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js';
            s.onload = function() {
                // d3-sankey adds .sankey/.sankeyLinkHorizontal to window.d3
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

    // Return a real teardown to the V2 component runtime.
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
    };

    // =====================================================================
    // MAIN BUILD
    // =====================================================================
    function buildStory() {
        var d3 = window.d3;

        // ------------------------------------------------ segment config
        var SEG_COLORS = {
            'Retail Banking Services':         '#2a78d6',
            'Business Banking':                '#eb6834',
            'Institutional Banking & Markets': '#1baf7a',
            'New Zealand (ASB)':               '#eda100',
        };
        var SEG_SHORT = {
            'Retail Banking Services':         'Retail',
            'Business Banking':                'Business',
            'Institutional Banking & Markets': 'IB&M',
            'New Zealand (ASB)':               'NZ',
        };
        // Short key used for drill-down data fields
        var SEG_KEY = {
            'Retail Banking Services':         'retail',
            'Business Banking':                'business',
            'Institutional Banking & Markets': 'ibm',
            'New Zealand (ASB)':               'nz',
        };
        var SEG_TINTS = {
            'Retail Banking Services':         '#2a78d61a',
            'Business Banking':                '#eb68341a',
            'Institutional Banking & Markets': '#1baf7a1a',
            'New Zealand (ASB)':               '#eda1001a',
        };

        // KPI display helpers
        var incomeGrowth = kpis.income_growth_pct != null ? kpis.income_growth_pct.toFixed(0) : '?';
        var priceGrowth  = kpis.price_growth_pct  != null ? kpis.price_growth_pct.toFixed(0)  : '?';

        // ------------------------------------------------ step copy (8 steps, idx 0-7)
        var STEPS = [
            {
                n: '00 / 07',
                headline: 'Five years. Four divisions. One unbroken growth story.',
                body: 'Australia\'s largest bank navigated a rate-hiking cycle, a credit shock, and a market re-rating — and came out ahead on every metric that matters.',
            },
            {
                n: '01 / 07',
                headline: 'Group income grew 24% in four years',
                body: 'Group operating income grew from A$27B in FY22 to nearly A$33.5B by FY26. The trajectory was remarkably consistent: no single year delivered a step-change, but the compounding of 4–5% annual growth produced a result that rewarded patience.',
            },
            {
                n: '02 / 07',
                headline: 'Four engines power the group',
                body: 'Retail Banking leads at 45% of income. Business Banking contributes 24% with superior cost efficiency (CTI 38%). Institutional Banking & Markets delivers steady fee income at 18%. New Zealand (ASB) tracks the domestic cycle at 13%.',
            },
            {
                n: '03 / 07',
                headline: 'Unstacked: divergence becomes clear',
                body: 'Retail Banking\'s scale dominates, but Business Banking\'s steeper angle reflects its higher margin efficiency. IB&M is the steadiest line — fee income insulates it from rate-cycle noise. New Zealand tracks its own domestic cycle.',
            },
            {
                n: '04 / 07',
                headline: 'Pick a division to explore',
                body: 'Each division has a different anatomy of earnings. Click a segment below to see how its revenue, costs, and profit layer together. If you skip this step, the next chapter defaults to Retail Banking Services.',
                interactive: true,
            },
            {
                n: '05 / 07',
                headline: 'Anatomy of earnings',
                body: 'Three forces determine every dollar of operating income: net interest income earned on the loan book, fee and other income layered on top, and operating expenses that consume the revenue stack. The gap that remains is operating income — the engine of dividends and growth.',
            },
            {
                n: '06 / 07',
                headline: 'Market verdict — share price',
                body: 'The market voted with its feet. A strong 2024 run-up — driven by earnings beats — pushed the stock to new highs before a mild 2025 plateau as credit normalisation concerns weighed on sentiment. The cumulative return still comfortably outpaced the broader market index.',
            },
            {
                n: '07 / 07',
                headline: 'Five years in six numbers',
                body: 'Five years of rate cycles, a credit stress, and a market re-rating close with the bank ahead on every front. The numbers below are the trailing twelve-month snapshot — a synthetic illustration of what sustained compound growth looks like in Australian banking.',
            },
        ];

        // ------------------------------------------------ closure state
        var selectedSeg = parentElement._selectedSeg || 'Retail Banking Services';
        var currentStep = -1;

        // ------------------------------------------------ scroll container
        var scrollContainer = root;
        scrollContainer.style.cssText = [
            'position:relative',
            'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
            'background:#f8fafc',
        ].join(';');

        var inner = document.createElement('div');
        inner.style.cssText = [
            'display:flex',
            'align-items:flex-start',
            'position:relative',
            'overflow-y:scroll',
            'height:' + viewH + 'px',
        ].join(';');
        scrollContainer.appendChild(inner);

        // ---- LEFT sticky chart column (62%)
        var chartCol = document.createElement('div');
        chartCol.style.cssText = [
            'width:62%',
            'position:sticky',
            'top:0',
            'height:' + viewH + 'px',
            'flex-shrink:0',
            'display:flex',
            'flex-direction:column',
            'align-items:center',
            'justify-content:center',
            'padding:20px 12px 20px 24px',
            'box-sizing:border-box',
            'background:#f8fafc',
        ].join(';');
        inner.appendChild(chartCol);

        // chart title
        var chartTitle = document.createElement('div');
        chartTitle.style.cssText = [
            'font-size:0.72rem',
            'font-variant:small-caps',
            'letter-spacing:0.08em',
            'color:#64748b',
            'margin-bottom:6px',
            'align-self:flex-start',
            'margin-left:56px',
            'transition:opacity 0.4s',
        ].join(';');
        chartTitle.textContent = 'Group Operating Income — FY22 to FY26';
        chartCol.appendChild(chartTitle);

        // SVG
        var svgHeight = viewH - 80;
        var margin = { top:24, right:80, bottom:44, left:64 };

        var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.style.cssText = 'width:100%;height:' + svgHeight + 'px;overflow:visible;';
        chartCol.appendChild(svgEl);

        var svg = d3.select(svgEl);

        // ---- KPI overlay
        var kpiOverlay = document.createElement('div');
        kpiOverlay.style.cssText = [
            'position:absolute',
            'top:0',
            'left:0',
            'width:100%',
            'height:100%',
            'display:grid',
            'grid-template-columns:1fr 1fr 1fr',
            'grid-template-rows:auto auto',
            'gap:12px',
            'padding:40px 32px',
            'box-sizing:border-box',
            'pointer-events:none',
            'opacity:0',
            'transition:opacity 0.6s',
            'align-content:center',
        ].join(';');
        chartCol.appendChild(kpiOverlay);

        // KPI card specs
        var KPI_SPECS = [
            { label:'Share Price',      prefix:'A$', suffix:'',  decimals:2, key:'share_price' },
            { label:'P/E Ratio',        prefix:'',   suffix:'x', decimals:1, key:'pe_ratio' },
            { label:'Dividend Yield',   prefix:'',   suffix:'%', decimals:2, key:'div_yield' },
            { label:'EPS (trailing)',   prefix:'A$', suffix:'',  decimals:4, key:'eps' },
            { label:'Annual Income',    prefix:'A$', suffix:'B', decimals:1, key:'annual_income_b' },
            { label:'Annual Cash NPAT', prefix:'A$', suffix:'B', decimals:1, key:'annual_npat_b' },
        ];
        var kpiValEls = [];
        KPI_SPECS.forEach(function(spec, ci) {
            var card = document.createElement('div');
            card.style.cssText = [
                'background:white',
                'border-radius:12px',
                'padding:18px',
                'border:1px solid #e2e8f0',
                'box-shadow:0 2px 8px rgba(0,0,0,0.06)',
                'display:flex',
                'flex-direction:column',
                'gap:6px',
            ].join(';');
            var lbl = document.createElement('div');
            lbl.textContent = spec.label;
            lbl.style.cssText = 'font-size:0.7rem;font-variant:small-caps;letter-spacing:0.06em;color:#64748b;';
            var val = document.createElement('div');
            val.className = 'kpi-value';
            val.style.cssText = 'font-size:1.3rem;font-weight:800;color:#0f172a;';
            val.textContent = spec.prefix + '0' + spec.suffix;
            card.appendChild(lbl);
            card.appendChild(val);
            kpiOverlay.appendChild(card);
            kpiValEls.push({ el: val, spec: spec });
        });

        // ---- RIGHT steps column (38%)
        var stepsCol = document.createElement('div');
        stepsCol.style.cssText = [
            'width:38%',
            'flex-shrink:0',
            'padding:0 24px 80px 16px',
            'box-sizing:border-box',
            'padding-top:20vh',
        ].join(';');
        inner.appendChild(stepsCol);

        // inject badge button styles
        var styleEl = document.createElement('style');
        styleEl.textContent = [
            '.seg-badge { cursor:pointer; border-radius:20px; padding:9px 18px; font-weight:600; font-size:0.82rem; color:#0f172a; margin:4px; min-height:44px; transition:background 0.2s, color 0.2s; }',
            '.seg-badge:hover { filter:brightness(0.92); }',
            '.seg-badge.active { color:white !important; }',
        ].join('\n');
        document.head.appendChild(styleEl);
        parentElement._styleEl = styleEl;

        var stepEls = [];
        var step4BadgesContainer = null;

        STEPS.forEach(function(step, i) {
            var card = document.createElement('div');
            card.dataset.step = String(i);
            card.style.cssText = [
                'background:white',
                'border-radius:12px',
                'padding:20px 24px',
                'border:1px solid #e2e8f0',
                'margin-bottom:24px',
                'min-height:' + (i === 0 ? Math.round(viewH * 0.8) : Math.round(viewH * 0.7)) + 'px',
                'display:flex',
                'flex-direction:column',
                'justify-content:center',
                'opacity:' + (i === 0 ? '1' : '0.35'),
                'transition:opacity 0.4s',
            ].join(';');

            var counter = document.createElement('div');
            counter.textContent = step.n;
            counter.style.cssText = 'font-variant:small-caps;font-size:0.72rem;letter-spacing:0.08em;color:#94a3b8;margin-bottom:10px;';

            var headline = document.createElement('div');
            headline.textContent = step.headline;
            headline.style.cssText = 'font-size:1.2rem;font-weight:800;color:#0f172a;line-height:1.35;margin-bottom:12px;';

            var body = document.createElement('div');
            body.textContent = step.body;
            body.style.cssText = 'font-size:0.87rem;color:#475569;line-height:1.7;';

            card.appendChild(counter);
            card.appendChild(headline);
            card.appendChild(body);

            // Step 4 interactive badges
            if (step.interactive) {
                var hint = document.createElement('div');
                hint.style.cssText = 'font-size:0.78rem;color:#64748b;font-style:italic;margin-top:16px;margin-bottom:8px;';
                hint.textContent = 'Tap a segment to explore its earnings anatomy';
                card.appendChild(hint);

                var badgesWrap = document.createElement('div');
                badgesWrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;';
                step4BadgesContainer = badgesWrap;

                segments.forEach(function(seg) {
                    var col = SEG_COLORS[seg] || '#888';
                    var btn = document.createElement('button');
                    btn.className = 'seg-badge';
                    btn.textContent = SEG_SHORT[seg] || seg;
                    btn.style.cssText = [
                        'background:' + (SEG_TINTS[seg] || '#eee'),
                        'border:1px solid ' + col + '44',
                        'border-left:4px solid ' + col,
                        'color:#0f172a',
                    ].join(';');
                    btn.dataset.seg = seg;
                    btn.addEventListener('click', function() {
                        selectSegment(seg);
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

        // Unified X domain
        var allDates = parsedMonthly.map(function(d) { return d._date; })
            .concat(parsedStock.map(function(d) { return d._date; }));
        var xScale = d3.scaleTime()
            .domain(d3.extent(allDates))
            .range([margin.left, getW() - margin.right]);

        // Y scales
        var maxIncome = d3.max(parsedMonthly, function(d) { return +d.operating_income; }) || 1;
        var yScaleIncome = d3.scaleLinear()
            .domain([0, maxIncome * 1.1])
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
            .domain([minStock * 0.92, maxStock * 1.05])
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
        var yAxisG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',0)')
            .call(d3.axisLeft(yScaleIncome).ticks(6)
                .tickFormat(function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B'); })
                .tickSizeOuter(0));
        yAxisG.select('.domain').remove();
        yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        yAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        function styleYAxis(yScale, isStock) {
            _lastYScale = yScale;
            var fmt = isStock
                ? function(d) { return 'A$' + d.toFixed(0); }
                : function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B'); };
            yAxisG.transition().duration(600).ease(d3.easeCubicInOut)
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(fmt).tickSizeOuter(0))
                .on('end', function() {
                    yAxisG.select('.domain').remove();
                    yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                    yAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                });
        }

        // =====================================================================
        // STEP 1: total income area + line (navy) — KEEP
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
            .attr('fill', 'rgba(51,65,85,0.10)')
            .attr('d', totalAreaGen)
            .attr('opacity', 0);

        var totalLinePath = g.append('path')
            .datum(parsedMonthly)
            .attr('fill', 'none')
            .attr('stroke', '#334155')
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

        // =====================================================================
        // STEP 2: ANIMATED TREEMAP — segment proportional split
        // =====================================================================

        // Compute annual totals per segment across full period
        var totalBySeg = {};
        segments.forEach(function(seg) { totalBySeg[seg] = 0; });
        parsedMonthly.forEach(function(d) {
            segments.forEach(function(seg) {
                totalBySeg[seg] += (+d[seg] || 0);
            });
        });
        var totalAll = segments.reduce(function(s, seg) { return s + totalBySeg[seg]; }, 0) || 1;

        // Container group for all treemap elements — positioned at chart area origin
        var treemapG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            .attr('opacity', 0);

        var treemapRects  = null;
        var treemapLabels = null;
        var treemapBuilt  = false;

        function buildTreemap() {
            var iW = innerW();
            var iH = innerH();

            // Clear previous content
            treemapG.selectAll('*').remove();

            var rootData = {
                name: 'Group',
                children: segments.map(function(seg) {
                    return { name: seg, value: totalBySeg[seg] };
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

            // Rects — start collapsed to full canvas, animate to treemap positions
            treemapRects = treemapG.selectAll('rect.tm-rect')
                .data(leaves)
                .enter()
                .append('rect')
                .attr('class', 'tm-rect')
                .attr('x', 0)
                .attr('y', 0)
                .attr('width', iW)
                .attr('height', iH)
                .attr('fill', function(d) { return SEG_COLORS[d.data.name] || '#888'; })
                .attr('stroke', 'white')
                .attr('stroke-width', 2)
                .attr('rx', 4)
                .attr('opacity', 0);

            // Animate rects in: fade in then transition to treemap position
            treemapRects
                .transition().duration(200).ease(d3.easeQuadIn)
                .attr('opacity', 1)
                .transition().duration(600).ease(d3.easeCubicInOut)
                .attr('x', function(d) { return d.x0; })
                .attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
                .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); });

            // Labels: short name + share %, centered in rect, hidden for small rects
            treemapLabels = treemapG.selectAll('g.tm-label')
                .data(leaves)
                .enter()
                .append('g')
                .attr('class', 'tm-label')
                .attr('opacity', 0)
                .attr('pointer-events', 'none');

            treemapLabels.each(function(d) {
                var w = d.x1 - d.x0;
                var h = d.y1 - d.y0;
                if (w < 80) return; // hide label for small rects
                var cx = d.x0 + w / 2;
                var cy = d.y0 + h / 2;
                var pct = (d.data.value / totalAll * 100).toFixed(1) + '%';
                var shortName = SEG_SHORT[d.data.name] || d.data.name;

                d3.select(this).append('text')
                    .attr('x', cx)
                    .attr('y', cy - 8)
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', Math.min(14, w / 6) + 'px')
                    .attr('font-weight', '700')
                    .attr('fill', 'white')
                    .text(shortName);

                d3.select(this).append('text')
                    .attr('x', cx)
                    .attr('y', cy + 12)
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', Math.min(12, w / 7) + 'px')
                    .attr('font-weight', '400')
                    .attr('fill', 'rgba(255,255,255,0.85)')
                    .text(pct);
            });

            // Fade labels in after rects fully settle (200ms fade-in + 600ms position = 800ms total, +50ms buffer)
            treemapLabels
                .transition().delay(850).duration(400)
                .attr('opacity', 1);

            treemapBuilt = true;
        }

        function hideTreemap() {
            treemapG.transition().duration(400).attr('opacity', 0);
        }

        // =====================================================================
        // STEP 3: STREAM GRAPH — five-year revenue flow
        // =====================================================================

        // Build stack with silhouette offset
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

        // Compute Y extent from all stacked values
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
            var col    = SEG_COLORS[seg] || '#888';
            var key    = SEG_KEY[seg];

            var p = g.append('path')
                .datum(series)
                .attr('fill', col)
                .attr('fill-opacity', 0.85)
                .attr('stroke', 'none')
                .attr('d', streamAreaGen)
                .attr('opacity', 0);

            streamPaths[seg] = p;

            // Label at rightmost data point
            var bg = g.append('rect').attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.8).attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '11px')
                .attr('font-weight', '700')
                .attr('fill', col)
                .attr('opacity', 0)
                .text(SEG_SHORT[seg] || seg);
            streamLabelEls[seg]  = lbl;
            streamLabelBgs[seg]  = bg;
        });

        function updateStreamLabels(opacity) {
            var lastIdx = stackInput.length - 1;
            if (lastIdx < 0) return;
            var lx = xScale(stackInput[lastIdx]._date) + 5;
            segments.forEach(function(seg, si) {
                var series = streamSeries[si];
                var band   = series[lastIdx];
                var cy     = (yScaleStream(band[0]) + yScaleStream(band[1])) / 2;
                var lbl    = streamLabelEls[seg];
                var bg     = streamLabelBgs[seg];
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
        // STEP 4: badge highlight (no new chart elements — uses segment lines)
        // =====================================================================

        // We still need the per-segment lines for step 3/4 highlight.
        // Build them using the un-stacked per-segment data.
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

        function selectSegment(seg) {
            selectedSeg = seg;
            parentElement._selectedSeg = seg;
            segments.forEach(function(s) {
                var isSel = s === seg;
                segLinePaths[s].path
                    .transition().duration(300).ease(d3.easeQuadOut)
                    .attr('opacity', isSel ? 1 : 0.2)
                    .attr('stroke-width', isSel ? 4.5 : 2);
                segLabelEls[s].transition().duration(300).attr('opacity', isSel ? 1 : 0.1);
                segLabelBgs[s].transition().duration(300).attr('opacity', isSel ? 0.9 : 0);
            });
            if (step4BadgesContainer) {
                step4BadgesContainer.querySelectorAll('.seg-badge').forEach(function(btn) {
                    var bseg = btn.dataset.seg;
                    var bcol = SEG_COLORS[bseg] || '#888';
                    if (bseg === seg) {
                        btn.classList.add('active');
                        btn.style.background = bcol;
                        btn.style.color = 'white';
                        btn.style.borderColor = bcol;
                    } else {
                        btn.classList.remove('active');
                        btn.style.background = SEG_TINTS[bseg] || '#eee';
                        btn.style.color = '#0f172a';
                        btn.style.borderColor = (SEG_COLORS[bseg] || '#888') + '44';
                        btn.style.borderLeft = '4px solid ' + (SEG_COLORS[bseg] || '#888');
                    }
                });
            }
            // If step 5 (Sankey) is visible, redraw it for the newly selected segment
            if (currentStep === 5 && window.d3sankey) {
                chartTitle.textContent = 'How ' + (SEG_SHORT[seg] || seg) + ' turns revenue into profit';
                drawSankey();
            }
        }

        // =====================================================================
        // STEP 5: SANKEY P&L DIAGRAM
        // =====================================================================

        // Container group for Sankey — positioned at chart area origin
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
            // Flow conservation: preProvision must equal totalRev - opexLink exactly
            var preProvision = Math.max(totalRev - totalOpex, 0);
            var opexLink = totalRev - preProvision;
            // Flow conservation: npat must equal preProvision - lieLink exactly
            var npat = Math.max(preProvision - totalLie, 0);
            var lieLink = preProvision - npat;

            return {
                totalNii:     totalNii,
                totalOther:   totalOther,
                opexLink:     opexLink,
                lieLink:      lieLink,
                totalRev:     totalRev,
                preProvision: preProvision,
                npat:         npat,
            };
        }

        function formatSankeyValue(v) {
            return 'A$' + d3.format('.3s')(v).replace('G','B');
        }

        function drawSankey() {
            if (!window.d3sankey) return;
            var dsk = window.d3sankey;
            var iW = innerW();
            var iH = innerH();
            var seg = selectedSeg;
            var segCol = SEG_COLORS[seg] || '#2a78d6';
            var sd = computeSankeyData(seg);

            // Clear previous content
            sankeyG.selectAll('*').remove();

            // Node definitions
            var nodeData = [
                { name: 'Net Interest Income' },   // 0
                { name: 'Fee & Other Income' },    // 1
                { name: 'Gross Revenue' },          // 2
                { name: 'Operating Expenses' },    // 3
                { name: 'Pre-Provision Profit' },  // 4
                { name: 'Loan Impairment' },        // 5
                { name: 'Cash NPAT' },              // 6
            ];

            // Link definitions (flow conservation: in-flow === out-flow at every node)
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
                graph = sankeyLayout({ nodes: nodeData.map(function(d) { return Object.assign({}, d); }),
                                       links: linkData.map(function(d) { return Object.assign({}, d); }) });
            } catch(e) { return; }

            var nodes = graph.nodes;
            var links = graph.links;

            // Node color function
            function nodeColor(i) {
                if (i === 0 || i === 1) return '#0d9488'; // teal source nodes
                if (i === 2) return segCol;               // hub = segment color
                if (i === 3 || i === 5) return '#dc2626'; // red drains
                return '#16a34a';                          // green profit nodes
            }

            // Link color function
            function linkColor(link) {
                var ti = link.target.index !== undefined ? link.target.index : link.target;
                if (ti === 3 || ti === 5) return 'rgba(220,38,38,0.35)';
                return d3.color(segCol) ? d3.color(segCol).copy({opacity: 0.4}).formatRgb() : segCol + '66';
            }

            // Draw links
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

            // Animate links in with stagger
            linkEls.transition()
                .duration(500)
                .delay(function(d, i) { return i * 100; })
                .ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            // Draw nodes
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

            // Node labels
            var nodeLabelG = sankeyG.append('g').attr('class', 'sankey-node-labels');
            nodes.forEach(function(d, i) {
                var isRight = d.x0 > iW / 2;
                var lx = isRight ? d.x1 + 6 : d.x0 - 6;
                var ly = (d.y0 + d.y1) / 2;
                var anchor = isRight ? 'start' : 'end';

                nodeLabelG.append('text')
                    .attr('x', lx)
                    .attr('y', ly - 5)
                    .attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', '10px')
                    .attr('font-weight', '700')
                    .attr('fill', '#334155')
                    .attr('opacity', 0)
                    .text(d.name)
                    .transition().delay(600).duration(400).attr('opacity', 1);

                nodeLabelG.append('text')
                    .attr('x', lx)
                    .attr('y', ly + 8)
                    .attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle')
                    .attr('font-size', '9px')
                    .attr('font-weight', '400')
                    .attr('fill', '#64748b')
                    .attr('opacity', 0)
                    .text(function() {
                        var val = d.value || 0;
                        return formatSankeyValue(val);
                    })
                    .transition().delay(700).duration(400).attr('opacity', 1);
            });
        }

        function hideSankey() {
            sankeyG.transition().duration(400).attr('opacity', 0);
        }

        // =====================================================================
        // STEP 6: Stock price area + line + 20-week moving average
        // =====================================================================
        var stockAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(function() { return yScaleStock(minStock * 0.92); })
            .y1(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var stockLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var stockAreaPath = g.append('path')
            .datum(parsedStock)
            .attr('fill', 'rgba(15,76,129,0.12)')
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
            var window20 = parsedStock.slice(Math.max(0, i - 19), i + 1);
            return {
                _date: d._date,
                value: d3.mean(window20, function(x) { return x.value; })
            };
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

        // MA label at last point
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

        // Peak annotation
        var peakRow = parsedStock.length ? parsedStock.reduce(function(a, b) { return b.value > a.value ? b : a; }) : null;
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
                .attr('fill', '#0F4C81')
                .text('FY24 peak');
        }

        // =====================================================================
        // HELPER: hide all data elements
        // =====================================================================
        function hideAll(fast) {
            var dur = fast ? 200 : 400;
            totalAreaPath.transition().duration(dur).attr('opacity', 0);
            totalLinePath.transition().duration(dur).attr('opacity', 0);
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
            kpiOverlay.style.opacity = '0';
        }

        // =====================================================================
        // STEP ACTIVATIONS
        // =====================================================================
        function activateStep(idx) {
            stepEls.forEach(function(el, i) {
                el.style.opacity = i === idx ? '1' : '0.35';
            });

            var t = d3.transition().duration(400).ease(d3.easeCubicInOut);

            // ----------- Step 0: empty axes -----------
            if (idx === 0) {
                chartTitle.textContent = 'Group Operating Income — FY22 to FY26';
                chartTitle.style.opacity = '1';
                hideAll(false);
                totalLineAnimated = false;
                stockAnimated = false;
                segments.forEach(function(seg) { segAnimated[seg] = false; });
                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ----------- Step 1: total income area + line (navy) -----------
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
                kpiOverlay.style.opacity = '0';

                totalAreaPath.transition(t).attr('opacity', 1);
                if (!totalLineAnimated) {
                    totalLineAnimated = true;
                    totalLinePath.attr('opacity', 1)
                        .attr('stroke-dashoffset', totalLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0);
                } else {
                    totalLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                }

                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ----------- Step 2: animated treemap -----------
            } else if (idx === 2) {
                chartTitle.textContent = 'Group Operating Income — proportional split';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition().duration(300).attr('opacity', 0);
                totalLinePath.transition().duration(300).attr('opacity', 0);
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
                kpiOverlay.style.opacity = '0';

                // Hide axes for treemap
                xAxisG.transition(t).attr('opacity', 0);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                // Build and show treemap — set group visible immediately so rects
                // animate themselves; avoids ghost rects from deferred callback racing
                treemapG.attr('opacity', 1);
                // Skip rebuild if treemap was already built at the current dimensions
                if (!treemapBuilt) { buildTreemap(); }

            // ----------- Step 3: stream graph -----------
            } else if (idx === 3) {
                chartTitle.textContent = 'Revenue streams — five-year flow';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
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
                kpiOverlay.style.opacity = '0';

                // Restore axes for stream graph
                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 0); // stream graph hides Y axis (silhouette)
                gridG.transition(t).attr('opacity', 0);  // no gridlines for stream

                // Animate stream bands in with stagger
                segments.forEach(function(seg, si) {
                    streamPaths[seg]
                        .transition().delay(si * 80).duration(700).ease(d3.easeCubicInOut)
                        .attr('opacity', 0.85);
                });
                setTimeout(function() { if (currentStep === 3) { updateStreamLabels(1); } }, 900);

            // ----------- Step 4: interactive badge selection -----------
            } else if (idx === 4) {
                chartTitle.textContent = 'Segment Operating Income';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                hideStreamGraph();
                hideSankey();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Restore axes
                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);

                var resetT = d3.transition().duration(400).ease(d3.easeCubicInOut);
                segments.forEach(function(seg) {
                    var lp = segLinePaths[seg];
                    lp.path.transition(resetT)
                        .attr('opacity', 0.85)
                        .attr('stroke-width', 3)
                        .attr('stroke-dashoffset', 0);
                });
                updateSegmentLabels(1, yScaleSegs);

                // Delay selectSegment until after resetT (400ms) so dashoffset
                // animation completes before selectSegment interrupts with its own transition.
                setTimeout(function() {
                    if (currentStep === 4) { selectSegment(selectedSeg); }
                }, 450);

                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ----------- Step 5: Sankey P&L diagram -----------
            } else if (idx === 5) {
                var seg = selectedSeg;
                chartTitle.textContent = 'How ' + (SEG_SHORT[seg] || seg) + ' turns revenue into profit';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
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
                kpiOverlay.style.opacity = '0';

                // Hide regular axes — Sankey uses its own layout
                xAxisG.transition(t).attr('opacity', 0);
                yAxisG.transition(t).attr('opacity', 0);
                gridG.transition(t).attr('opacity', 0);

                // Reset sankeyG and redraw (selectedSeg may have changed)
                // Clear stale DOM nodes synchronously before the fade-in to avoid ghost flash
                hideSankey();
                sankeyG.selectAll('*').remove();
                sankeyG.attr('opacity', 0);

                function doDrawSankey() {
                    sankeyG.transition().duration(300).attr('opacity', 1)
                        .on('end', function() { drawSankey(); });
                }

                if (window.d3sankey) {
                    doDrawSankey();
                } else {
                    loadD3Sankey().then(doDrawSankey).catch(function() {
                        chartTitle.textContent = 'Sankey chart failed to load';
                    });
                }

            // ----------- Step 6: share price + moving average -----------
            } else if (idx === 6) {
                chartTitle.textContent = 'Share Price (A$)';
                chartTitle.style.opacity = '1';

                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideSankey();
                kpiOverlay.style.opacity = '0';

                // Restore axes
                xAxisG.transition(t).attr('opacity', 1);
                yAxisG.transition(t).attr('opacity', 1);
                gridG.transition(t).attr('opacity', 1);

                stockAreaPath.transition(t).attr('opacity', 1);
                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0);
                    peakAnnotG.transition().delay(1000).duration(400).attr('opacity', 1);
                    // Fade in MA line 700ms after main line appears
                    maLine
                        .transition().delay(700).duration(600).ease(d3.easeCubicOut)
                        .attr('opacity', 0.9);
                    if (maLabelEl) {
                        maLabelEl
                            .transition().delay(1200).duration(400)
                            .attr('opacity', 1);
                    }
                } else {
                    stockLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    peakAnnotG.transition(t).attr('opacity', 1);
                    maLine.transition(t).attr('opacity', 0.9);
                    if (maLabelEl) maLabelEl.transition(t).attr('opacity', 1);
                }

                styleYAxis(yScaleStock, true);
                drawGridlines(yScaleStock);

            // ----------- Step 7: KPI scorecard -----------
            } else if (idx === 7) {
                hideTreemap();
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                hideStreamGraph();
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideSankey();

                // Restore axes (stock backdrop)
                xAxisG.transition(t).attr('opacity', 0.3);
                yAxisG.transition(t).attr('opacity', 0.3);
                gridG.transition(t).attr('opacity', 0.3);

                chartTitle.style.opacity = '0.3';
                stockAreaPath.transition(t).attr('opacity', 0.12);
                stockLinePath.transition(t).attr('opacity', 0.12);
                maLine.transition(t).attr('opacity', 0);
                if (maLabelEl) maLabelEl.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0.15);
                kpiOverlay.style.opacity = '1';

                kpiValEls.forEach(function(item, ci) {
                    var target = kpis[item.spec.key];
                    if (target == null) {
                        item.el.textContent = '—';
                        return;
                    }
                    d3.select(item.el)
                        .transition().duration(800).delay(ci * 100)
                        .tween('text', function() {
                            var node = this;
                            var interp = d3.interpolateNumber(0, target);
                            var prefix = item.spec.prefix;
                            var suffix = item.spec.suffix;
                            var dec    = item.spec.decimals;
                            return function(tt) {
                                node.textContent = prefix + interp(tt).toFixed(dec) + suffix;
                            };
                        });
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
            { root: inner, threshold: 0.3 }
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

                // Redraw static paths
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
                    var lastMa = movingAvgData[movingAvgData.length - 1];
                    maLabelEl.attr('x', xScale(lastMa._date) + 6).attr('y', yScaleStock(lastMa.value));
                }

                // Reposition peak annotation after xScale change
                if (peakRow) {
                    var px = xScale(peakRow._date);
                    var py = yScaleStock(peakRow.value);
                    peakAnnotG.select('line').attr('x1', px).attr('x2', px).attr('y1', py).attr('y2', py + 30);
                    peakAnnotG.select('text').attr('x', px).attr('y', py - 6);
                }

                // Reposition segment and stream labels after xScale change
                if (currentStep === 3) { updateStreamLabels(1); }
                if (currentStep === 4) { updateSegmentLabels(1, yScaleSegs); }

                // Rebuild layout-dependent charts if active
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
        Pixel height reserved by Streamlit. Defaults to 900px.
    """
    _scrollytelling_component(
        data=data,
        default=None,
        key=key,
        height=height,
    )
