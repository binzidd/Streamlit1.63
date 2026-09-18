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
/* v7 */
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
                // D3 may have already finished loading between the window.d3 check
                // and finding the existing tag — check again before attaching a
                // listener that would never fire.
                if (window.d3) { resolve(); return; }
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
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

    loadD3().then(buildStory).catch(function() {
        root.innerHTML = '<p style="color:red;padding:12px;">D3 failed to load.</p>';
    });

    // Return a real teardown to the V2 component runtime.
    // buildStory runs asynchronously (after loadD3 resolves), so we expose a
    // stable function that delegates to whatever cleanup buildStory registered
    // on parentElement.
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
        // Restore selectedSeg across re-renders so user's badge selection survives.
        var selectedSeg = parentElement._selectedSeg || 'Retail Banking Services';
        var currentStep = -1;

        // ------------------------------------------------ scroll container
        // scrollContainer is a non-scrolling wrapper — overflow must NOT be set here
        // because position:sticky on chartCol only works when the nearest scrolling
        // ancestor is the direct parent of the sticky element.
        var scrollContainer = root;
        scrollContainer.style.cssText = [
            'position:relative',
            'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
            'background:#f8fafc',
        ].join(';');

        // inner IS the scroll container — chartCol (sticky) is a direct flex child of inner
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
        // position:sticky makes chartCol the containing block for absolutely-positioned
        // children (such as kpiOverlay), so we do NOT add a separate position:relative.
        // Only one position declaration — remove the duplicate from the original array.
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

        // KPI card specs — value filled by D3 count-up tween at step 7
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

        // inject badge button styles — store on parentElement so cleanup can remove it
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

        // Build per-segment drill-down y scales (computed lazily, cached)
        var yScaleDrillCache = {};
        function getYScaleDrill(seg) {
            if (yScaleDrillCache[seg]) return yScaleDrillCache[seg];
            var key = SEG_KEY[seg] || 'retail';
            var maxRev = d3.max(parsedMonthly, function(d) {
                return (+d['nii_' + key] || 0) + (+d['other_' + key] || 0);
            }) || 1;
            yScaleDrillCache[seg] = d3.scaleLinear()
                .domain([0, maxRev * 1.15])
                .range([svgHeight - margin.bottom, margin.top]);
            return yScaleDrillCache[seg];
        }

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

        // ==================================================================
        // Chart elements — all created upfront, toggled via opacity
        // ==================================================================

        // ---- Step 1: total income area + line
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

        // ---- Step 2: stacked area bands
        var STACK_KEYS = segments.map(function(s) { return SEG_KEY[s]; });
        // Build stack data: array of {date, _date, retail, business, ibm, nz}
        var stackInput = parsedMonthly.map(function(d) {
            var row = { _date: d._date, date: d.date };
            segments.forEach(function(seg) {
                row[SEG_KEY[seg]] = +d[seg] || 0;
            });
            return row;
        });

        var stack = d3.stack()
            .keys(STACK_KEYS)
            .order(d3.stackOrderNone)
            .offset(d3.stackOffsetNone);

        var stackedSeries = stack(stackInput);

        // One area generator per segment band
        var stackedAreaGens = {};
        var stackedPaths    = {};
        var stackedLabels   = {};
        var stackedLabelBgs = {};

        segments.forEach(function(seg, si) {
            var series = stackedSeries[si];
            var col    = SEG_COLORS[seg] || '#888';

            var areaGen = d3.area()
                .x(function(d) { return xScale(d.data._date); })
                .y0(function(d) { return yScaleIncome(d[0]); })
                .y1(function(d) { return yScaleIncome(d[1]); })
                .curve(d3.curveMonotoneX);

            stackedAreaGens[seg] = areaGen;

            var p = g.append('path')
                .datum(series)
                .attr('fill', col)
                .attr('fill-opacity', 0.75)
                .attr('stroke', 'white')
                .attr('stroke-width', 0.5)
                .attr('d', areaGen)
                .attr('opacity', 0);
            stackedPaths[seg] = p;

            // band label (right edge centroid)
            var bg = g.append('rect').attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.8).attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '11px')
                .attr('font-weight', '700')
                .attr('fill', col)
                .attr('opacity', 0)
                .text(SEG_SHORT[seg] || seg);
            stackedLabels[seg]   = lbl;
            stackedLabelBgs[seg] = bg;
        });

        function updateStackedLabels(opacity) {
            var lastIdx = stackInput.length - 1;
            if (lastIdx < 0) return;
            var lx = xScale(stackInput[lastIdx]._date) + 5;
            segments.forEach(function(seg, si) {
                var series = stackedSeries[si];
                var band   = series[lastIdx];
                var cy     = (yScaleIncome(band[0]) + yScaleIncome(band[1])) / 2;
                var lbl    = stackedLabels[seg];
                var bg     = stackedLabelBgs[seg];
                lbl.attr('x', lx).attr('y', cy).attr('dy', '0.35em').attr('opacity', opacity);
                try {
                    var bb = lbl.node().getBBox();
                    bg.attr('x', bb.x - 2).attr('y', bb.y - 1)
                      .attr('width', bb.width + 4).attr('height', bb.height + 2)
                      .attr('opacity', opacity * 0.85);
                } catch(e) { bg.attr('opacity', 0); }
            });
        }

        // ---- Step 3: individual segment lines
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

        // ---- Step 4 badge highlight function
        function selectSegment(seg) {
            selectedSeg = seg;
            parentElement._selectedSeg = seg;
            // Update D3 segment lines
            segments.forEach(function(s) {
                var isSel = s === seg;
                segLinePaths[s].path
                    .transition().duration(300).ease(d3.easeQuadOut)
                    .attr('opacity', isSel ? 1 : 0.2)
                    .attr('stroke-width', isSel ? 4.5 : 2);
                segLabelEls[s].transition().duration(300).attr('opacity', isSel ? 1 : 0.1);
                segLabelBgs[s].transition().duration(300).attr('opacity', isSel ? 0.9 : 0);
            });
            // Update badge styles
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
        }

        // ---- Step 5: drill-down paths (one set, reused for any selectedSeg)
        var drillNiiArea   = g.append('path').attr('fill', '#0d9488').attr('fill-opacity', 0.70).attr('opacity', 0).attr('stroke', 'none');
        var drillRevArea   = g.append('path').attr('fill', '#5eead4').attr('fill-opacity', 0.60).attr('opacity', 0).attr('stroke', 'none');
        var drillOpexArea  = g.append('path').attr('fill', '#ef4444').attr('fill-opacity', 0.50).attr('opacity', 0).attr('stroke', 'none');
        var drillOiLine    = g.append('path').attr('fill', 'none').attr('stroke', '#0f172a').attr('stroke-width', 3).attr('opacity', 0);
        var drillCtiLabel  = g.append('text').attr('font-size', '11px').attr('font-weight', '700').attr('fill', '#0f172a').attr('opacity', 0);
        var drillRevLabel  = g.append('text').attr('font-size', '11px').attr('fill', '#0d9488').attr('opacity', 0);
        var drillOiLabel   = g.append('text').attr('font-size', '11px').attr('fill', '#0f172a').attr('opacity', 0);
        var drillOpexLabel = g.append('text').attr('font-size', '11px').attr('fill', '#ef4444').attr('opacity', 0);

        var drillAnimated = false;

        function buildDrillDown(seg) {
            var key = SEG_KEY[seg] || 'retail';
            var yD  = getYScaleDrill(seg);

            // Area generators
            var niiAreaGen = d3.area()
                .x(function(d) { return xScale(d._date); })
                .y0(yD(0))
                .y1(function(d) { return yD(+d['nii_' + key] || 0); })
                .curve(d3.curveMonotoneX);

            var revAreaGen = d3.area()
                .x(function(d) { return xScale(d._date); })
                .y0(function(d) { return yD(+d['nii_' + key] || 0); })
                .y1(function(d) { return yD((+d['nii_' + key] || 0) + (+d['other_' + key] || 0)); })
                .curve(d3.curveMonotoneX);

            var opexAreaGen = d3.area()
                .x(function(d) { return xScale(d._date); })
                .y0(function(d) {
                    var rev  = (+d['nii_' + key] || 0) + (+d['other_' + key] || 0);
                    var opex = +d['opex_' + key] || 0;
                    return yD(rev - opex);
                })
                .y1(function(d) { return yD((+d['nii_' + key] || 0) + (+d['other_' + key] || 0)); })
                .curve(d3.curveMonotoneX);

            var oiLineGen = d3.line()
                .x(function(d) { return xScale(d._date); })
                .y(function(d) {
                    var rev  = (+d['nii_' + key] || 0) + (+d['other_' + key] || 0);
                    var opex = +d['opex_' + key] || 0;
                    return yD(rev - opex);
                })
                .curve(d3.curveMonotoneX);

            drillNiiArea.datum(parsedMonthly).attr('d', niiAreaGen);
            drillRevArea.datum(parsedMonthly).attr('d', revAreaGen);
            drillOpexArea.datum(parsedMonthly).attr('d', opexAreaGen);
            drillOiLine.datum(parsedMonthly).attr('d', oiLineGen);

            // set dashoffset for line draw animation
            var oiLen = 0;
            try { oiLen = drillOiLine.node().getTotalLength(); } catch(e) {}
            if (oiLen === 0) {
                requestAnimationFrame(function() {
                    try { oiLen = drillOiLine.node().getTotalLength(); } catch(e) {}
                    drillOiLine
                        .attr('stroke-dasharray', oiLen + ' ' + oiLen)
                        .attr('stroke-dashoffset', oiLen);
                });
            } else {
                drillOiLine
                    .attr('stroke-dasharray', oiLen + ' ' + oiLen)
                    .attr('stroke-dashoffset', oiLen);
            }

            // Labels — positioned at last data point
            var last = parsedMonthly[parsedMonthly.length - 1];
            var lx = last ? xScale(last._date) + 8 : margin.left;
            if (last) {
                var nii   = +last['nii_'   + key] || 0;
                var other = +last['other_' + key] || 0;
                var opex  = +last['opex_'  + key] || 0;
                var rev   = nii + other;
                var oi    = rev - opex;
                var cti   = rev > 0 ? (opex / rev * 100).toFixed(1) : '—';

                drillRevLabel
                    .attr('x', lx).attr('y', yD(rev)).attr('dy', '-4px')
                    .text('Revenue A$' + (rev / 1e9).toFixed(1) + 'B');
                drillOpexLabel
                    .attr('x', lx).attr('y', yD(rev - opex / 2)).attr('dy', '0.35em')
                    .text('Costs (CTI: ' + cti + '%)');
                drillOiLabel
                    .attr('x', lx).attr('y', yD(oi)).attr('dy', '0.35em')
                    .text('Op. Income');
                drillCtiLabel
                    .attr('x', lx).attr('y', yD(oi) - 18)
                    .text('CTI: ' + cti + '%');
            }

            // Sequential animated reveals
            drillNiiArea.attr('opacity', 0)
                .transition().duration(500).ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            drillRevArea.attr('opacity', 0)
                .transition().delay(300).duration(500).ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            drillOpexArea.attr('opacity', 0)
                .transition().delay(600).duration(500).ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            drillOiLine.attr('opacity', 0)
                .transition().delay(900).duration(800).ease(d3.easeCubicInOut)
                .attr('opacity', 1)
                .attr('stroke-dashoffset', 0);

            drillRevLabel.attr('opacity', 0)
                .transition().delay(1000).duration(400)
                .attr('opacity', 1);
            drillOpexLabel.attr('opacity', 0)
                .transition().delay(1100).duration(400)
                .attr('opacity', 1);
            drillOiLabel.attr('opacity', 0)
                .transition().delay(1150).duration(400)
                .attr('opacity', 1);
            drillCtiLabel.attr('opacity', 0)
                .transition().delay(1200).duration(400)
                .attr('opacity', 1);
        }

        function hideDrillDown() {
            drillNiiArea.transition().duration(300).attr('opacity', 0);
            drillRevArea.transition().duration(300).attr('opacity', 0);
            drillOpexArea.transition().duration(300).attr('opacity', 0);
            drillOiLine.transition().duration(300).attr('opacity', 0);
            drillCtiLabel.transition().duration(300).attr('opacity', 0);
            drillRevLabel.transition().duration(300).attr('opacity', 0);
            drillOiLabel.transition().duration(300).attr('opacity', 0);
            drillOpexLabel.transition().duration(300).attr('opacity', 0);
        }

        // ---- Step 6: stock area + line
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

        // ======================================================================
        // HELPER: hide all data elements except the ones we want
        // ======================================================================
        function hideAll(fast) {
            var dur = fast ? 200 : 400;
            totalAreaPath.transition().duration(dur).attr('opacity', 0);
            totalLinePath.transition().duration(dur).attr('opacity', 0);
            segments.forEach(function(seg) {
                stackedPaths[seg].transition().duration(dur).attr('opacity', 0);
                stackedLabels[seg].transition().duration(dur).attr('opacity', 0);
                stackedLabelBgs[seg].transition().duration(dur).attr('opacity', 0);
                segLinePaths[seg].path.transition().duration(dur).attr('opacity', 0);
                segLabelEls[seg].transition().duration(dur).attr('opacity', 0);
                segLabelBgs[seg].transition().duration(dur).attr('opacity', 0);
            });
            hideDrillDown();
            stockAreaPath.transition().duration(dur).attr('opacity', 0);
            stockLinePath.transition().duration(dur).attr('opacity', 0);
            peakAnnotG.transition().duration(dur).attr('opacity', 0);
            kpiOverlay.style.opacity = '0';
        }

        // ======================================================================
        // STEP ACTIVATIONS
        // ======================================================================
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
                drillAnimated = false;
                segments.forEach(function(seg) { segAnimated[seg] = false; });
                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ----------- Step 1: total income line -----------
            } else if (idx === 1) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                // Reset non-relevant
                segments.forEach(function(seg) {
                    stackedPaths[seg].transition(t).attr('opacity', 0);
                    stackedLabels[seg].transition(t).attr('opacity', 0);
                    stackedLabelBgs[seg].transition(t).attr('opacity', 0);
                    segLinePaths[seg].path.transition(t).attr('opacity', 0)
                        .attr('stroke-dashoffset', segLinePaths[seg].len);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                    segAnimated[seg] = false;
                });
                hideDrillDown();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Show total area immediately
                totalAreaPath.transition(t).attr('opacity', 1);
                // Draw total line once
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

            // ----------- Step 2: stacked area bands -----------
            } else if (idx === 2) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                // Fade out total + segment lines
                totalAreaPath.transition().duration(300).attr('opacity', 0);
                totalLinePath.transition().duration(300).attr('opacity', 0);
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition().duration(300).attr('opacity', 0);
                    segLabelEls[seg].transition().duration(300).attr('opacity', 0);
                    segLabelBgs[seg].transition().duration(300).attr('opacity', 0);
                });
                hideDrillDown();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Animate stacked bands in after a brief delay
                segments.forEach(function(seg) {
                    stackedPaths[seg]
                        .transition().delay(200).duration(900).ease(d3.easeCubicInOut)
                        .attr('opacity', 1);
                });
                setTimeout(function() { if (currentStep === 2) { updateStackedLabels(1); } }, 1100);

                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ----------- Step 3: individual segment lines (unstacked) -----------
            } else if (idx === 3) {
                chartTitle.textContent = 'Segment Operating Income';
                chartTitle.style.opacity = '1';

                // Fade stacked bands
                segments.forEach(function(seg) {
                    stackedPaths[seg].transition().duration(400).attr('opacity', 0);
                    stackedLabels[seg].transition().duration(400).attr('opacity', 0);
                    stackedLabelBgs[seg].transition().duration(400).attr('opacity', 0);
                });
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                hideDrillDown();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Draw segment lines
                segments.forEach(function(seg, si) {
                    var lp = segLinePaths[seg];
                    if (!segAnimated[seg]) {
                        segAnimated[seg] = true;
                        lp.path
                            .attr('stroke-width', 3)
                            .attr('opacity', 1)
                            .attr('stroke-dashoffset', lp.len)
                            .transition().duration(900).delay(si * 150).ease(d3.easeCubicOut)
                            .attr('stroke-dashoffset', 0);
                    } else {
                        lp.path.transition(t)
                            .attr('stroke-width', 3).attr('opacity', 1)
                            .attr('stroke-dashoffset', 0);
                    }
                });
                setTimeout(function() { if (currentStep === 3) { updateSegmentLabels(1, yScaleSegs); } }, 800);

                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ----------- Step 4: interactive selection -----------
            } else if (idx === 4) {
                chartTitle.textContent = 'Segment Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    stackedPaths[seg].transition(t).attr('opacity', 0);
                    stackedLabels[seg].transition(t).attr('opacity', 0);
                    stackedLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideDrillDown();
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Ensure segment lines are visible at equal weight, then apply
                // the selection highlight AFTER the reset transition completes
                // to avoid a race where both transitions fight over the same attrs.
                var resetT = d3.transition().duration(400).ease(d3.easeCubicInOut);
                segments.forEach(function(seg) {
                    var lp = segLinePaths[seg];
                    lp.path.transition(resetT)
                        .attr('opacity', 0.85)
                        .attr('stroke-width', 3)
                        .attr('stroke-dashoffset', 0);
                });
                updateSegmentLabels(1, yScaleSegs);

                // Apply the currently selected segment highlight after reset ends
                setTimeout(function() {
                    if (currentStep === 4) { selectSegment(selectedSeg); }
                }, 0);

                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ----------- Step 5: drill-down anatomy -----------
            } else if (idx === 5) {
                var seg = selectedSeg;
                var key = SEG_KEY[seg] || 'retail';
                chartTitle.textContent = 'Inside ' + seg;
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(s) {
                    stackedPaths[s].transition(t).attr('opacity', 0);
                    stackedLabels[s].transition(t).attr('opacity', 0);
                    stackedLabelBgs[s].transition(t).attr('opacity', 0);
                    segLinePaths[s].path.transition(t).attr('opacity', 0);
                    segLabelEls[s].transition(t).attr('opacity', 0);
                    segLabelBgs[s].transition(t).attr('opacity', 0);
                });
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0);
                peakAnnotG.transition(t).attr('opacity', 0);
                kpiOverlay.style.opacity = '0';

                // Build / rebuild drill-down (always rebuild on enter so selected seg is correct)
                hideDrillDown();
                drillAnimated = false;
                setTimeout(function() {
                    buildDrillDown(seg);
                    drillAnimated = true;
                }, 200);

                var yD = getYScaleDrill(seg);
                styleYAxis(yD, false);
                drawGridlines(yD);

            // ----------- Step 6: share price -----------
            } else if (idx === 6) {
                chartTitle.textContent = 'Share Price (A$)';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    stackedPaths[seg].transition(t).attr('opacity', 0);
                    stackedLabels[seg].transition(t).attr('opacity', 0);
                    stackedLabelBgs[seg].transition(t).attr('opacity', 0);
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideDrillDown();
                kpiOverlay.style.opacity = '0';

                stockAreaPath.transition(t).attr('opacity', 1);
                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0);
                    peakAnnotG.transition().delay(1000).duration(400).attr('opacity', 1);
                } else {
                    stockLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    peakAnnotG.transition(t).attr('opacity', 1);
                }

                styleYAxis(yScaleStock, true);
                drawGridlines(yScaleStock);

            // ----------- Step 7: KPI scorecard -----------
            } else if (idx === 7) {
                // Full reset first — clear all chart elements from any prior step to
                // prevent ghost artifacts (drill-down areas, stacked bands, segment lines).
                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    stackedPaths[seg].transition(t).attr('opacity', 0);
                    stackedLabels[seg].transition(t).attr('opacity', 0);
                    stackedLabelBgs[seg].transition(t).attr('opacity', 0);
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                    segLabelEls[seg].transition(t).attr('opacity', 0);
                    segLabelBgs[seg].transition(t).attr('opacity', 0);
                });
                hideDrillDown();

                chartTitle.style.opacity = '0.3';
                stockAreaPath.transition(t).attr('opacity', 0.12);
                stockLinePath.transition(t).attr('opacity', 0.12);
                peakAnnotG.transition(t).attr('opacity', 0.15);
                kpiOverlay.style.opacity = '1';

                // Count-up tween per KPI card
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
                totalAreaPath.attr('d', totalAreaGen);
                totalLinePath.attr('d', totalLineGen);
                segments.forEach(function(seg) {
                    stackedPaths[seg].attr('d', stackedAreaGens[seg]);
                    segLinePaths[seg].path.attr('d', segLinePaths[seg].lineGen);
                });
                stockAreaPath.attr('d', stockAreaGen);
                stockLinePath.attr('d', stockLineGen);
                // Redraw drill-down paths when step 5 is active
                if (currentStep === 5) { buildDrillDown(selectedSeg); }
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
