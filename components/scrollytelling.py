"""D3 v7 scrollytelling component — 'Five Years of Earnings'.

A self-contained scroll-driven narrative with a sticky D3 chart on the left
and step cards on the right. Uses st.components.v2.component() (no iframe).

Steps
-----
  0  Intro: axes visible, no data — "Five years of earnings"
  1  Total group income: grey area + line animated in
  2  Four segment lines appear, total fades out
  3  2023 credit shock: orange shading + annotation on Business Banking
  4  Cash NPAT dashed line added, all segments un-dimmed
  5  Crossfade to share price area chart (Y axis transitions smoothly)
  6  KPI scorecard overlay over faded chart
"""
from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# HTML skeleton — root div is the scroll container
# ---------------------------------------------------------------------------
_HTML = '<div id="st_scroll_root" style="width:100%;"></div>'

# ---------------------------------------------------------------------------
# JS module (D3 v7, raw string so Python f-string substitution is not applied)
# ---------------------------------------------------------------------------
_JS = r"""
/* v5 */
export default function(component) {
    const { parentElement, data } = component;

    // ------------------------------------------------------------------ guard
    if (!data || !data.monthly || !data.monthly.length) return;

    // ----------------------------------------------------------------- cleanup
    if (parentElement._storyObserver) {
        parentElement._storyObserver.disconnect();
        parentElement._storyObserver = null;
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
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-d3', '1');
            s.src = 'https://unpkg.com/d3@7/dist/d3.min.js';
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    loadD3().then(buildStory).catch(function(err) {
        root.innerHTML = '<p style="color:red;padding:12px;">D3 failed to load. Check network.</p>';
    });

    function buildStory() {
        var d3 = window.d3;

        // ------------------------------------------- segment colour palette
        var SEG_COLORS = {
            'Retail Banking Services':         '#2a78d6',
            'Business Banking':                '#eb6834',
            'Institutional Banking & Markets': '#1baf7a',
            'New Zealand (ASB)':               '#eda100',
        };
        var SEG_SHORT = {
            'Retail Banking Services':         'Retail',
            'Business Banking':                'Business Banking',
            'Institutional Banking & Markets': 'IB&M',
            'New Zealand (ASB)':               'New Zealand',
        };

        // ------------------------------------------- step narrative content
        // Fix 9 / Fix 13: use explicit null/undefined checks so a value of 0.0
        // renders as '0' rather than as the missing-data placeholder '?'.
        var incomeGrowth = kpis.income_growth_pct != null ? kpis.income_growth_pct.toFixed(0) : '?';
        var priceGrowth  = kpis.price_growth_pct  != null ? kpis.price_growth_pct.toFixed(0)  : '?';

        var STEPS = [
            {
                n: '01 / 07',
                headline: 'A bank that kept growing when others didn\'t',
                body: 'Group operating income rose from A$27B in FY22 to nearly A$33.5B by FY26 — a 24% expansion across one of the most turbulent stretches in modern banking, encompassing a rate-hiking cycle, a regional credit shock, and a stock rally that rewarded patient investors.',
            },
            {
                n: '02 / 07',
                headline: 'Total income grew ' + incomeGrowth + '% in four years',
                body: 'Group operating income compounded at roughly 4–5% annually, driven by higher rates, loan growth and fee expansion across all four divisions. The trajectory was remarkably consistent — no single year delivered a step-change, but the cumulative result was substantial.',
            },
            {
                n: '03 / 07',
                headline: 'Four segments, four growth trajectories',
                body: 'Retail Banking leads by scale at 45% of income. Business Banking punches above its 24% income share on margin efficiency (CTI 38%). IB&M delivers steady fee income at 18%. New Zealand (ASB) contributes 13% and tracks the domestic cycle closely.',
            },
            {
                n: '04 / 07',
                headline: 'Mid-2023: a credit shock hit Business Banking',
                body: 'Loan impairment charges in Business Banking spiked 2.4× between April and September 2023 as commercial credit conditions tightened. The orange shading marks the stress window. The other three segments held firm, demonstrating the portfolio diversification benefit.',
            },
            {
                n: '05 / 07',
                headline: 'Cash NPAT held through the cycle',
                body: 'Despite the impairment shock, group Cash NPAT remained resilient. Retail and IB&M margins more than offset the Business Banking drag, keeping after-tax profit on trend. The green dashed line shows Cash NPAT tracking consistently below — but parallel to — operating income.',
            },
            {
                n: '06 / 07',
                headline: 'Share price: +' + priceGrowth + '% over the period',
                body: 'The market re-rated the stock as rate tailwinds materialised. A strong 2024 run-up — driven by earnings beats — was followed by a brief 2025 plateau as credit normalisation concerns weighed on sentiment. The cumulative return still outpaced the broader market.',
            },
            {
                n: '07 / 07',
                headline: "Today’s scorecard",
                // Fix 16: close the story arc with editorial copy; the page-level
                // subtitle already carries the synthetic-data caveat so it does
                // not need to be repeated inside the narrative card.
                body: 'Five years of rate cycles, a credit stress and a market re-rating have left the bank with a ' + priceGrowth + '% higher share price, A$' + (kpis.annual_income_b != null ? kpis.annual_income_b.toFixed(1) : '?') + 'B in trailing income and a dividend yield of ' + (kpis.div_yield != null ? kpis.div_yield.toFixed(2) : '?') + '%. The numbers below reflect the synthetic trailing-twelve-month period used throughout this story.',
            },
        ];

        // ------------------------------------------- scroll container layout
        var scrollContainer = root;
        scrollContainer.style.cssText = [
            'overflow-y: scroll',
            'height: ' + viewH + 'px',
            'position: relative',
            'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            'background: #f8fafc',
        ].join(';');

        var inner = document.createElement('div');
        inner.style.cssText = 'display:flex; align-items:flex-start; position:relative;';
        scrollContainer.appendChild(inner);

        // ---- LEFT: sticky chart column (62%)
        var chartCol = document.createElement('div');
        chartCol.style.cssText = [
            'width: 62%',
            'position: sticky',
            'top: 0',
            'height: ' + viewH + 'px',
            'flex-shrink: 0',
            'display: flex',
            'flex-direction: column',
            'align-items: center',
            'justify-content: center',
            'padding: 20px 12px 20px 24px',
            'box-sizing: border-box',
            'background: #f8fafc',
        ].join(';');
        inner.appendChild(chartCol);

        // chart title label
        var chartTitle = document.createElement('div');
        chartTitle.style.cssText = [
            'font-size: 0.72rem',
            'font-variant: small-caps',
            'letter-spacing: 0.08em',
            'color: #64748b',
            'margin-bottom: 6px',
            'align-self: flex-start',
            'margin-left: 48px',
            'transition: opacity 0.4s',
        ].join(';');
        chartTitle.textContent = 'Group Operating Income';
        chartCol.appendChild(chartTitle);

        // SVG element
        var svgHeight = viewH - 80;
        // Fix 4 / Fix 15: increase right margin so end-of-line labels (~60px)
        // have room inside the SVG without overflowing into the steps column.
        var margin    = { top: 20, right: 70, bottom: 40, left: 60 };

        var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.style.cssText = 'width:100%; height:' + svgHeight + 'px; overflow:visible;';
        chartCol.appendChild(svgEl);

        var svg = d3.select(svgEl);

        // ---- KPI overlay (absolutely positioned over sticky chart column)
        // Fix 2 / Fix 14: append to chartCol (the sticky element) not to
        // scrollContainer — otherwise position:absolute is relative to the
        // scrollable document top and the overlay scrolls away with the content.
        // width:100% because chartCol is already 62% wide.
        var kpiOverlay = document.createElement('div');
        kpiOverlay.style.cssText = [
            'position: absolute',
            'top: 0',
            'left: 0',
            'width: 100%',
            'height: 100%',
            'display: grid',
            'grid-template-columns: 1fr 1fr 1fr',
            'grid-template-rows: auto auto',
            'gap: 12px',
            'padding: 32px',
            'box-sizing: border-box',
            'pointer-events: none',
            'opacity: 0',
            'transition: opacity 0.6s',
            'align-content: center',
        ].join(';');
        chartCol.appendChild(kpiOverlay);

        // Fix 9: explicit null/undefined checks so 0.0 renders as a real value
        // rather than the '—' missing-data placeholder.
        var kpiCards = [
            { label: 'Share Price',      value: kpis.share_price      != null ? 'A$' + kpis.share_price.toFixed(2)        : '—' },
            { label: 'P/E Ratio',        value: kpis.pe_ratio         != null ? kpis.pe_ratio.toFixed(1) + '×'             : '—' },
            { label: 'Div Yield',        value: kpis.div_yield        != null ? kpis.div_yield.toFixed(2) + '%'            : '—' },
            { label: 'EPS (trailing)',   value: kpis.eps              != null ? 'A$' + kpis.eps.toFixed(4)                 : '—' },
            { label: 'Annual Income',    value: kpis.annual_income_b  != null ? 'A$' + kpis.annual_income_b.toFixed(1) + 'B' : '—' },
            { label: 'Annual Cash NPAT', value: kpis.annual_npat_b    != null ? 'A$' + kpis.annual_npat_b.toFixed(1) + 'B'  : '—' },
        ];
        kpiCards.forEach(function(k) {
            var card = document.createElement('div');
            card.style.cssText = [
                'background: white',
                'border-radius: 12px',
                'padding: 18px',
                'border: 1px solid #e2e8f0',
                'box-shadow: 0 2px 8px rgba(0,0,0,0.06)',
                'display: flex',
                'flex-direction: column',
                'gap: 6px',
            ].join(';');
            var lbl = document.createElement('div');
            lbl.textContent = k.label;
            lbl.style.cssText = 'font-size:0.7rem; font-variant:small-caps; letter-spacing:0.06em; color:#64748b;';
            var val = document.createElement('div');
            val.textContent = k.value;
            val.style.cssText = 'font-size:1.3rem; font-weight:800; color:#0f172a;';
            card.appendChild(lbl);
            card.appendChild(val);
            kpiOverlay.appendChild(card);
        });

        // ---- RIGHT: steps column (38%)
        var stepsCol = document.createElement('div');
        stepsCol.style.cssText = [
            'width: 38%',
            'flex-shrink: 0',
            'padding: 0 24px 80px 16px',
            'box-sizing: border-box',
            'padding-top: 20vh',
        ].join(';');
        inner.appendChild(stepsCol);

        var stepEls = [];
        STEPS.forEach(function(step, i) {
            var card = document.createElement('div');
            card.style.cssText = [
                'background: white',
                'border-radius: 12px',
                'padding: 20px 24px',
                'border: 1px solid #e2e8f0',
                'margin-bottom: 24px',
                'min-height: ' + (i === 0 ? '80vh' : '70vh'),
                'display: flex',
                'flex-direction: column',
                'justify-content: center',
                'opacity: ' + (i === 0 ? '1' : '0.35'),
                'transition: opacity 0.4s',
            ].join(';');

            var counter = document.createElement('div');
            counter.textContent = step.n;
            counter.style.cssText = [
                'font-variant: small-caps',
                'font-size: 0.72rem',
                'letter-spacing: 0.08em',
                'color: #94a3b8',
                'margin-bottom: 10px',
            ].join(';');

            var headline = document.createElement('div');
            headline.textContent = step.headline;
            headline.style.cssText = [
                'font-size: 1.2rem',
                'font-weight: 800',
                'color: #0f172a',
                'line-height: 1.35',
                'margin-bottom: 12px',
            ].join(';');

            var body = document.createElement('div');
            body.textContent = step.body;
            body.style.cssText = [
                'font-size: 0.87rem',
                'color: #475569',
                'line-height: 1.7',
            ].join(';');

            card.appendChild(counter);
            card.appendChild(headline);
            card.appendChild(body);
            stepsCol.appendChild(card);
            stepEls.push(card);
        });

        // ------------------------------------------- D3 scales + axes
        var parseDate = d3.timeParse('%Y-%m-%d');

        var parsedMonthly = monthly.map(function(d) {
            return Object.assign({}, d, { _date: parseDate(d.date) });
        }).filter(function(d) { return d._date; });

        var parsedStock = stock.map(function(d) {
            return { _date: parseDate(d.date), value: +d.value };
        }).filter(function(d) { return d._date; });

        function getW() {
            // Fix 5: fall back to 600 if layout not yet complete (e.g. Firefox
            // before first paint).  rAF wrapping below ensures this is called
            // after layout in normal circumstances.
            return svgEl.getBoundingClientRect().width || 600;
        }

        // Fix 5: defer scale computation and all path appends until after one
        // animation frame so the SVG has been laid out and getW() returns the
        // real pixel width instead of 0 (which inverts the x range).
        requestAnimationFrame(function() {

        // Unified X domain covering both monthly and stock
        var allDates = parsedMonthly.map(function(d) { return d._date; })
            .concat(parsedStock.map(function(d) { return d._date; }));
        var xScale = d3.scaleTime()
            .domain(d3.extent(allDates))
            .range([margin.left, getW() - margin.right]);

        // Fix 7: add a ResizeObserver so the chart reflowes if Streamlit changes
        // the column width (sidebar toggle, window resize, etc.).
        if (window.ResizeObserver) {
            var _resizeObserver = new ResizeObserver(function() {
                var newW = getW();
                xScale.range([margin.left, newW - margin.right]);
                // Re-render x axis.
                xAxisG.call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
                xAxisG.select('.domain').remove();
                xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                xAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                // Redraw gridlines (uses getW() internally).
                if (_lastYScale) drawGridlines(_lastYScale);
                // Redraw all paths with updated x positions.
                if (totalAreaPath) totalAreaPath.attr('d', totalAreaGen);
                if (totalLinePath) totalLinePath.attr('d', totalLineGen);
                segments.forEach(function(seg) {
                    if (segLinePaths[seg]) segLinePaths[seg].path.attr('d', segLinePaths[seg].lineGen);
                });
                if (npatPath) npatPath.attr('d', npatLineGen);
                if (stockAreaPath) stockAreaPath.attr('d', stockAreaGen);
                if (stockLinePath) stockLinePath.attr('d', stockLineGen);
                // Reposition shock rect.
                var rx1 = xScale(new Date('2023-04-01'));
                var rx2 = xScale(new Date('2023-09-30'));
                if (shockRect) shockRect.attr('x', rx1).attr('width', rx2 - rx1);
            });
            _resizeObserver.observe(svgEl);
            // Store for cleanup alongside the IntersectionObserver.
            parentElement._resizeObserver = _resizeObserver;
        }

        var maxIncome = d3.max(parsedMonthly, function(d) { return +d.operating_income; }) || 1;
        var yScaleIncome = d3.scaleLinear()
            .domain([0, maxIncome * 1.1])
            .range([svgHeight - margin.bottom, margin.top]);

        // Separate scale for individual segment lines so they fill the chart
        // height instead of being squeezed into the bottom third.
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

        // Track last active yScale for resize redraws (Fix 7).
        var _lastYScale = yScaleIncome;

        var g = svg.append('g');

        // Gridlines
        var gridG = g.append('g').attr('class', 'grid');

        function drawGridlines(yScale) {
            gridG.selectAll('line').remove();
            var ticks = yScale.ticks(6);
            gridG.selectAll('line')
                .data(ticks)
                .join('line')
                .attr('x1', margin.left)
                .attr('x2', getW() - margin.right)
                .attr('y1', function(d) { return yScale(d); })
                .attr('y2', function(d) { return yScale(d); })
                .attr('stroke', '#e2e8f0')
                .attr('stroke-dasharray', '4,3')
                .attr('stroke-width', 1);
        }

        drawGridlines(yScaleIncome);

        // X axis
        var xAxisG = g.append('g')
            .attr('transform', 'translate(0,' + (svgHeight - margin.bottom) + ')')
            .call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
        xAxisG.select('.domain').remove();
        xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        xAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        // Y axis
        var yAxisG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',0)')
            .call(
                d3.axisLeft(yScaleIncome).ticks(6)
                    .tickFormat(function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B'); })
                    .tickSizeOuter(0)
            );
        yAxisG.select('.domain').remove();
        yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        yAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        // ------------------------------------------- chart elements

        // Total income area + line
        var totalAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(yScaleIncome(0))
            .y1(function(d) { return yScaleIncome(+d.operating_income); });

        var totalLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleIncome(+d.operating_income); });

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
        totalLinePath
            .attr('stroke-dasharray', totalLineLen + ' ' + totalLineLen)
            .attr('stroke-dashoffset', totalLineLen);

        var totalLineAnimated = false;

        // Helper: build a line generator for a segment using any Y scale
        function makeSegGen(seg, yScale) {
            return d3.line()
                .x(function(d) { return xScale(d._date); })
                .y(function(d) { return yScale(+d[seg] || 0); })
                .defined(function(d) { return d[seg] != null && !isNaN(d[seg]); })
                .curve(d3.curveMonotoneX);
        }

        // Segment lines — initially drawn on yScaleSegs so the draw-in
        // animation runs on the right scale from the start.
        var segLinePaths = {};
        var segAnimated  = {};
        segments.forEach(function(seg) {
            var lineGen = makeSegGen(seg, yScaleSegs);
            var p = g.append('path')
                .datum(parsedMonthly)
                .attr('fill', 'none')
                .attr('stroke', SEG_COLORS[seg] || '#888')
                .attr('stroke-width', 3)
                .attr('d', lineGen)
                .attr('opacity', 0);

            var len = 0;
            try { len = p.node().getTotalLength(); } catch(e) {}
            p.attr('stroke-dasharray', len + ' ' + len).attr('stroke-dashoffset', len);

            segLinePaths[seg] = { path: p, lineGen: lineGen, len: len };
            segAnimated[seg]  = false;
        });

        // Segment end-of-line labels — bold, large, with a white bg pill
        var segLabelEls = {};
        var segLabelBgs = {};
        segments.forEach(function(seg) {
            var bg = g.append('rect')
                .attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.85)
                .attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '12px')
                .attr('font-weight', '800')
                .attr('fill', SEG_COLORS[seg] || '#888')
                .attr('opacity', 0)
                .text(SEG_SHORT[seg] || seg);
            segLabelEls[seg] = lbl;
            segLabelBgs[seg] = bg;
        });

        // Credit shock rectangle (Apr–Sep 2023)
        var shockX1 = xScale(new Date('2023-04-01'));
        var shockX2 = xScale(new Date('2023-09-30'));
        var shockRect = g.append('rect')
            .attr('x', shockX1)
            .attr('y', margin.top)
            .attr('width', shockX2 - shockX1)
            .attr('height', svgHeight - margin.top - margin.bottom)
            .attr('fill', 'rgba(235,104,52,0.13)')
            .attr('opacity', 0);

        // Shock annotation group
        var shockAnnotG = g.append('g').attr('opacity', 0);
        var annotX = (shockX1 + shockX2) / 2;
        var annotY = margin.top + 10;
        shockAnnotG.append('line')
            .attr('x1', annotX).attr('x2', annotX)
            .attr('y1', annotY + 18).attr('y2', annotY + 44)
            .attr('stroke', '#eb6834').attr('stroke-width', 1.5).attr('stroke-dasharray', '3,2');
        shockAnnotG.append('text')
            .attr('x', annotX).attr('y', annotY)
            .attr('text-anchor', 'middle')
            .attr('font-size', '0.65rem')
            .attr('font-weight', '700')
            .attr('fill', '#eb6834')
            .text('Credit shock');
        shockAnnotG.append('text')
            .attr('x', annotX).attr('y', annotY + 12)
            .attr('text-anchor', 'middle')
            .attr('font-size', '0.6rem')
            .attr('fill', '#eb6834')
            .text('Apr–Sep 2023');

        // Cash NPAT dashed line
        var npatLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleSegs(+d.cash_npat || 0); });

        var npatPath = g.append('path')
            .datum(parsedMonthly)
            .attr('fill', 'none')
            .attr('stroke', '#1baf7a')
            .attr('stroke-width', 2)
            .attr('d', npatLineGen)
            .attr('opacity', 0);

        var npatLen = 0;
        try { npatLen = npatPath.node().getTotalLength(); } catch(e) {}
        npatPath.attr('stroke-dasharray', npatLen + ' ' + npatLen).attr('stroke-dashoffset', npatLen);
        var npatAnimated = false;

        // NPAT end label
        var lastNpatRow = parsedMonthly[parsedMonthly.length - 1];
        var npatLabel = g.append('text')
            .attr('font-size', '12px').attr('font-weight', '800').attr('fill', '#1baf7a')
            .attr('opacity', 0);
        if (lastNpatRow) {
            npatLabel
                .attr('x', xScale(lastNpatRow._date) + 6)
                .attr('y', yScaleSegs(+lastNpatRow.cash_npat || 0))
                .attr('dy', '0.35em')
                .text('Cash NPAT');
        }

        // Stock area + line
        var stockAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(yScaleStock(0))
            .y1(function(d) { return yScaleStock(d.value); });

        var stockLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); });

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
        stockLinePath
            .attr('stroke-dasharray', stockLineLen + ' ' + stockLineLen)
            .attr('stroke-dashoffset', stockLineLen);
        var stockAnimated = false;

        // ------------------------------------------- helpers

        function styleYAxis(yScale, isStock) {
            _lastYScale = yScale; // Fix 7: track for ResizeObserver redraws.
            var fmt = isStock
                ? function(d) { return 'A$' + d.toFixed(0); }
                : function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B'); };
            // Fix 1: chain .on('end') onto the SAME transition to avoid D3 v7
            // pre-emption — a second .transition() call on the same selection
            // cancels the first before it can call the axis.
            yAxisG.transition().duration(600).ease(d3.easeCubicInOut)
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(fmt).tickSizeOuter(0))
                .on('end', function() {
                    yAxisG.select('.domain').remove();
                    yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                    yAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                });
        }

        function updateSegmentLabels(opacity, yScale) {
            var yS = yScale || yScaleSegs;
            var lastRow = parsedMonthly[parsedMonthly.length - 1];
            if (!lastRow) return;
            // De-collide overlapping labels: sort by y, enforce 18px gap.
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
                // Size bg rect to text bounds
                try {
                    var bb = el.node().getBBox();
                    bg.attr('x', bb.x - 2).attr('y', bb.y - 1)
                      .attr('width', bb.width + 4).attr('height', bb.height + 2)
                      .attr('opacity', opacity * 0.9);
                } catch(e) {
                    bg.attr('opacity', 0);
                }
            });
        }

        // ------------------------------------------- step activation
        var currentStep = -1;

        function activateStep(idx) {
            if (idx === currentStep) return;
            currentStep = idx;

            stepEls.forEach(function(el, i) {
                el.style.opacity = i === idx ? '1' : '0.35';
            });

            var dur = 1100;
            var ease = d3.easeCubicOut;
            var t = d3.transition().duration(600).ease(d3.easeCubicInOut);

            // ---- Step 0: intro — axes only, no data ----
            if (idx === 0) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', totalLineLen);
                totalLineAnimated = false;

                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0).attr('stroke-dashoffset', segLinePaths[seg].len);
                    segAnimated[seg] = false;
                });
                updateSegmentLabels(0);
                shockRect.transition(t).attr('opacity', 0);
                shockAnnotG.transition(t).attr('opacity', 0);
                npatPath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', npatLen);
                npatLabel.transition(t).attr('opacity', 0);
                npatAnimated = false;
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', stockLineLen);
                stockAnimated = false;
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ---- Step 1: total group income animated in ----
            } else if (idx === 1) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 1);
                if (!totalLineAnimated) {
                    totalLineAnimated = true;
                    totalLinePath.attr('opacity', 1)
                        .attr('stroke-dashoffset', totalLineLen)
                        .transition().duration(dur).ease(ease)
                        .attr('stroke-dashoffset', 0);
                } else {
                    totalLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                }
                segments.forEach(function(seg) {
                    // Fix 6: also reset dashoffset so re-entering step 2 always
                    // starts the draw animation from the beginning, not from a
                    // mid-animation interrupted position.
                    segLinePaths[seg].path.transition(t).attr('opacity', 0).attr('stroke-dashoffset', segLinePaths[seg].len);
                    segAnimated[seg] = false;
                });
                updateSegmentLabels(0);
                shockRect.transition(t).attr('opacity', 0);
                shockAnnotG.transition(t).attr('opacity', 0);
                npatPath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', npatLen);
                npatLabel.transition(t).attr('opacity', 0);
                npatAnimated = false;
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', stockLineLen);
                stockAnimated = false;
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);

            // ---- Step 2: four segment lines appear, total fades ----
            } else if (idx === 2) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);

                segments.forEach(function(seg) {
                    if (!segAnimated[seg]) {
                        segAnimated[seg] = true;
                        segLinePaths[seg].path
                            .attr('opacity', 1)
                            .attr('stroke-dashoffset', segLinePaths[seg].len)
                            .transition().duration(dur).ease(ease)
                            .attr('stroke-dashoffset', 0);
                    } else {
                        segLinePaths[seg].path.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    }
                });
                updateSegmentLabels(1, yScaleSegs);
                shockRect.transition(t).attr('opacity', 0);
                shockAnnotG.transition(t).attr('opacity', 0);
                npatPath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', npatLen);
                npatLabel.transition(t).attr('opacity', 0);
                npatAnimated = false;
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', stockLineLen);
                stockAnimated = false;
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ---- Step 3: credit shock highlight ----
            } else if (idx === 3) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);

                segments.forEach(function(seg) {
                    var isBB = seg === 'Business Banking';
                    segLinePaths[seg].path.transition(t)
                        .attr('opacity', isBB ? 1 : 0.15)
                        .attr('stroke-width', isBB ? 3.5 : 2)
                        .attr('stroke-dashoffset', 0);
                    segLabelEls[seg].transition(t).attr('opacity', isBB ? 1 : 0.1);
                    segLabelBgs[seg].transition(t).attr('opacity', isBB ? 0.9 : 0);
                    if (isBB) {
                        var lastRow = parsedMonthly[parsedMonthly.length - 1];
                        if (lastRow) {
                            segLabelEls[seg]
                                .attr('x', xScale(lastRow._date) + 6)
                                .attr('y', yScaleSegs(+lastRow[seg] || 0))
                                .attr('dy', '0.35em');
                        }
                    }
                });
                shockRect.transition(t).attr('opacity', 1);
                shockAnnotG.transition(t).attr('opacity', 1);
                npatPath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', npatLen);
                npatLabel.transition(t).attr('opacity', 0);
                npatAnimated = false;
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', stockLineLen);
                stockAnimated = false;
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ---- Step 4: un-dim all, add Cash NPAT ----
            } else if (idx === 4) {
                chartTitle.textContent = 'Group Operating Income';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t)
                        .attr('opacity', 1).attr('stroke-width', 3).attr('stroke-dashoffset', 0);
                });
                updateSegmentLabels(1, yScaleSegs);
                shockRect.transition(t).attr('opacity', 0.5);
                shockAnnotG.transition(t).attr('opacity', 0.5);

                if (!npatAnimated) {
                    npatAnimated = true;
                    // Fix 3 / Fix 10 / Fix 18: use full-length dasharray only for
                    // the draw-on animation, then switch to a real visual dash
                    // pattern ('6,3') in the .on('end') callback so the line
                    // matches the narrative ('green dashed line').
                    npatPath
                        .attr('stroke-dasharray', npatLen + ' ' + npatLen)
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', npatLen)
                        .transition().duration(dur).ease(ease)
                        .attr('stroke-dashoffset', 0)
                        .on('end', function() { npatPath.attr('stroke-dasharray', '6,3'); });
                } else {
                    // Already animated — jump to visible dashed state immediately.
                    npatPath.attr('stroke-dasharray', '6,3')
                        .transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                }
                npatLabel.transition(t).attr('opacity', 1);
                stockAreaPath.transition(t).attr('opacity', 0);
                stockLinePath.transition(t).attr('opacity', 0).attr('stroke-dashoffset', stockLineLen);
                stockAnimated = false;
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleSegs, false);
                drawGridlines(yScaleSegs);

            // ---- Step 5: crossfade to share price ----
            } else if (idx === 5) {
                chartTitle.textContent = 'Share Price (A$)';
                chartTitle.style.opacity = '1';

                totalAreaPath.transition(t).attr('opacity', 0);
                totalLinePath.transition(t).attr('opacity', 0);
                segments.forEach(function(seg) {
                    segLinePaths[seg].path.transition(t).attr('opacity', 0);
                });
                updateSegmentLabels(0);
                shockRect.transition(t).attr('opacity', 0);
                shockAnnotG.transition(t).attr('opacity', 0);
                npatPath.transition(t).attr('opacity', 0);
                npatLabel.transition(t).attr('opacity', 0);

                stockAreaPath.transition(t).attr('opacity', 1);
                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(dur).ease(ease)
                        .attr('stroke-dashoffset', 0);
                } else {
                    stockLinePath.transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                }
                kpiOverlay.style.opacity = '0';
                styleYAxis(yScaleStock, true);
                drawGridlines(yScaleStock);

            // ---- Step 6: KPI scorecard overlay ----
            } else if (idx === 6) {
                chartTitle.style.opacity = '0.3';
                stockAreaPath.transition(t).attr('opacity', 0.15);
                stockLinePath.transition(t).attr('opacity', 0.15);
                kpiOverlay.style.opacity = '1';
            }
        }

        // ------------------------------------------- IntersectionObserver
        // Fix 17: debounce via rAF — when the user scrolls quickly through
        // multiple cards, multiple intersection callbacks fire in the same frame.
        // We collect all intersecting entries, pick the one with the highest
        // intersectionRatio, then call activateStep once per animation frame.
        // Also lowers threshold to 0.3 so D3 transitions get more lead time.
        var _rafPending = false;
        var _pendingEntries = [];
        var observer = new IntersectionObserver(
            function(entries) {
                entries.forEach(function(e) { _pendingEntries.push(e); });
                if (!_rafPending) {
                    _rafPending = true;
                    requestAnimationFrame(function() {
                        _rafPending = false;
                        // Find the intersecting entry with the highest ratio.
                        var best = null;
                        _pendingEntries.forEach(function(e) {
                            if (e.isIntersecting) {
                                if (!best || e.intersectionRatio > best.intersectionRatio) {
                                    best = e;
                                }
                            }
                        });
                        _pendingEntries = [];
                        if (best) {
                            var idx = parseInt(best.target.getAttribute('data-step'), 10);
                            activateStep(idx);
                        }
                    });
                }
            },
            {
                // Fix — hardening: set root to the scroll container div, not null.
                root: scrollContainer,
                threshold: 0.3,
            }
        );

        stepEls.forEach(function(el, i) {
            el.setAttribute('data-step', String(i));
            observer.observe(el);
        });

        parentElement._storyObserver = observer;
        // Fix 20: reset currentStep before activateStep(0) on remount so the
        // idx === currentStep guard does not short-circuit the initial render.
        currentStep = -1;
        activateStep(0);

        // Fix 8: safety-net observer cleanup on page unload in case the
        // Streamlit harness does not call the returned cleanup function.
        window.addEventListener('unload', function() { observer.disconnect(); });

        }); // end requestAnimationFrame (Fix 5)

        // Cleanup function returned to Streamlit v2 harness
        return function() {
            if (parentElement._storyObserver) {
                parentElement._storyObserver.disconnect();
                parentElement._storyObserver = null;
            }
            // Fix 7: also disconnect ResizeObserver on cleanup.
            if (parentElement._resizeObserver) {
                parentElement._resizeObserver.disconnect();
                parentElement._resizeObserver = null;
            }
        };
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
            monthly  — list of dicts {date, operating_income, cash_npat, <segment cols>}
            stock    — list of dicts {date, value}
            kpis     — dict with share_price, pe_ratio, div_yield, eps,
                        annual_income_b, annual_npat_b, income_growth_pct, price_growth_pct
            segments — list[str] segment names in display order
    key:
        Unique Streamlit component key.
    height:
        Fix 12: pixel height reserved by Streamlit before JS runs, preventing a
        layout collapse/jump. Defaults to 900px. Pass the same value you want
        the scroll container to occupy.
    """
    _scrollytelling_component(
        data=data,
        default=None,
        key=key,
        height=height,
    )
