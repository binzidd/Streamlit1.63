"""Bloomberg Red Meat editorial page — Streamlit V2 component.

Two-column scrollytelling: left 45% text (8 sections × 100vh), right 55%
chart repositioned via window.scroll (NOT sticky — sticky breaks in Streamlit).
"""
from __future__ import annotations
import json
import streamlit as st

# ---------------------------------------------------------------------------
# HTML skeleton
# ---------------------------------------------------------------------------
_HTML = '<div id="blm_root" style="width:100%;"></div>'

# ---------------------------------------------------------------------------
# JS module — blm_v2
# ---------------------------------------------------------------------------
_JS = r"""
/* blm_v2 */
export default function(component) {
    const { parentElement, data } = component;

    // ---------------------------------------------------------------- guard
    if (!data || !data.monthly || !data.monthly.length) return;

    // ---------------------------------------------------------------- cleanup
    ['_blmScroll','_blmResize','_blmKeydown','_blmStyleEl'].forEach(function(k) {
        if (parentElement[k]) {
            if (k === '_blmStyleEl') {
                try { parentElement[k].remove(); } catch(e) {}
            } else {
                var evtName = k === '_blmScroll' ? 'scroll' : k === '_blmResize' ? 'resize' : 'keydown';
                var target = (k === '_blmKeydown') ? document
                    : (k === '_blmResize') ? window
                    : (parentElement._blmScrollTarget || window);
                try { target.removeEventListener(evtName, parentElement[k]); } catch(e) {}
                if (k === '_blmScroll') { try { window.removeEventListener('scroll', parentElement[k]); } catch(e) {} }
            }
            parentElement[k] = null;
        }
    });
    if (parentElement._blmRO) {
        parentElement._blmRO.disconnect();
        parentElement._blmRO = null;
    }

    var root = parentElement.querySelector('#blm_root');
    if (!root) return;
    root.innerHTML = '';

    var monthly   = data.monthly   || [];
    var stock     = data.stock     || [];
    var kpis      = data.kpis      || {};
    var real_kpis = data.real_kpis || {};
    var segments  = data.segments  || [];
    var commentary = data.commentary || {};

    // ---------------------------------------------------------------- load D3
    function loadD3() {
        return new Promise(function(resolve, reject) {
            if (window.d3) { resolve(); return; }
            var ex = document.querySelector('script[data-d3]');
            if (ex) { ex.addEventListener('load', resolve); ex.addEventListener('error', reject); return; }
            var s = document.createElement('script');
            s.setAttribute('data-d3', '1');
            s.src = 'https://unpkg.com/d3@7/dist/d3.min.js';
            s.onload = resolve; s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    function loadD3Sankey() {
        return new Promise(function(resolve, reject) {
            if (window.d3 && window.d3.sankey) { window.d3sankey = window.d3; resolve(); return; }
            var ex = document.querySelector('script[data-d3sankey]');
            if (ex) {
                ex.addEventListener('load', function() { window.d3sankey = window.d3; resolve(); });
                ex.addEventListener('error', reject);
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-d3sankey', '1');
            s.src = 'https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js';
            s.onload = function() { window.d3sankey = window.d3; resolve(); };
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    loadD3().then(loadD3Sankey).then(buildStory).catch(function(err) {
        root.innerHTML = '<p style="color:red;padding:24px;">D3 failed: ' + err + '</p>';
    });

    return function() {
        ['_blmScroll','_blmResize'].forEach(function(k) {
            if (parentElement[k]) {
                var evtName = k === '_blmScroll' ? 'scroll' : 'resize';
                var target = (k === '_blmScroll') ? (parentElement._blmScrollTarget || window) : window;
                try { target.removeEventListener(evtName, parentElement[k]); } catch(e) {}
                if (k === '_blmScroll') { try { window.removeEventListener('scroll', parentElement[k]); } catch(e) {} }
                parentElement[k] = null;
            }
        });
        if (parentElement._blmKeydown) {
            try { document.removeEventListener('keydown', parentElement._blmKeydown); } catch(e) {}
            parentElement._blmKeydown = null;
        }
        if (parentElement._blmRO) { parentElement._blmRO.disconnect(); parentElement._blmRO = null; }
    };

    // =====================================================================
    // MAIN BUILD
    // =====================================================================
    function buildStory() {
        var d3 = window.d3;

        var viewH = Math.max(700, window.innerHeight || 900);
        var NUM_CHAPTERS = 8; // splash (0) + 7 content chapters

        // ---- Chapter backgrounds
        var CH_BG = [
            '#1e3a5f',  // 0 splash navy
            '#ffffff',  // 1 white
            '#f1f5f9',  // 2 slate
            '#ffffff',  // 3 white
            '#1e3a5f',  // 4 navy
            '#0f172a',  // 5 dark
            '#ffffff',  // 6 white
            '#1e3a5f',  // 7 navy
        ];

        // ---- Commentary (from Python via data.commentary, fallback built-in)
        var BUILT_IN_COMMENTARY = {
            0: { key_stat: 'A$30.2B', key_label: 'Cash Operating Income',
                 headline: 'CBA Posts Record A$30.2B Operating Income in FY26',
                 pull_quote: 'A$30.2B — five-year income record',
                 body: 'Cash operating income rose to A$30.2B, up from ~A$22B five years ago, driven by the NII engine at 84.7% of revenue. The franchise demonstrated durability through rate cycles, compounding income at ~6% CAGR since FY21.' },
            1: { key_stat: '+11%', key_label: 'Business Banking NPAT growth',
                 headline: 'Business Banking Leads Group at +11% NPAT',
                 pull_quote: '+11% Business Banking — standout division',
                 body: 'Business Banking delivered 11% NPAT growth on disciplined volume growth and repricing, offsetting NZ\'s 7% decline on macro headwinds. Retail held firm despite LIE up 39% from an ultra-low base.' },
            2: { key_stat: '84.7%', key_label: 'NII share of income',
                 headline: 'NII Commands 84.7% of Revenue Amid Margin Pressure',
                 pull_quote: '84.7% NII share — highest among major banks',
                 body: 'NII of A$25.6B dominates the revenue mix at 84.7%, an unusually high share versus global peers, while other income of A$4.6B covers fees, trading and insurance. Structural NIM pressure from deposit repricing remains the key watch item.' },
            3: { key_stat: '3.39%', key_label: 'Business Banking NIM best-in-class',
                 headline: 'Business Banking NIM at 3.39% Towers Over Group Average',
                 pull_quote: '3.39% Business NIM — 134bps above group',
                 body: 'Business Banking\'s 3.39% NIM leads the group\'s 2.05% by 134bps, reflecting disciplined SME repricing and lower deposit competition. Retail NIM faces ongoing fixed-rate roll-off drag, while NZ margins are compressed by competition and provisioning.' },
            4: { key_stat: '45.5%', key_label: 'CTI minus 20bps',
                 headline: 'CTI Tightens 20bps to 45.5% as Productivity Gains Show',
                 pull_quote: '45.5% CTI — record pre-provision profit of A$16.5B',
                 body: 'Opex of A$13.8B against A$30.2B income delivers a 45.5% CTI, improving 20bps year-on-year, with pre-provision profit at a record A$16.5B. Technology and compliance remain the largest cost drivers but the productivity overlay is working.' },
            5: { key_stat: '~20x', key_label: 'PE premium to peers',
                 headline: "CBA's ~20x PE Premium Tests Patience at Cycle Peak",
                 pull_quote: '~20x PE — can the franchise premium hold?',
                 body: 'CBA trades at ~20x forward earnings versus peers at 13-15x, supported by earnings quality, franchise dominance and a 505c DPS at a 78% payout ratio. NIM headwinds and rising credit costs raise questions about whether that premium is fully earned.' },
            6: { key_stat: '14.0%', key_label: 'Cash ROE plus 50bps',
                 headline: 'ROE Rises 50bps to 14.0% as CBA Reaffirms Quality Tag',
                 pull_quote: '14.0% ROE — highest-returning major bank',
                 body: 'Cash NPAT of A$11.0B, ROE of 14.0% (+50bps), EPS of 656.9c and DPS of 505c confirm CBA as Australia\'s highest-returning major bank. CET1 at 12.0% (-30bps) stays comfortably above APRA\'s 11.25% unquestionably strong benchmark.' },
        };

        function getCommentary(idx) {
            var raw = commentary && commentary[String(idx)];
            if (!raw) raw = BUILT_IN_COMMENTARY[idx] || {};
            return raw;
        }

        // ---- Segment config
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
        var REAL_DIV_NIM  = { 'Retail Banking Services': 2.50, 'Business Banking': 3.39, 'Institutional Banking and Markets': 0.87, 'New Zealand (ASB)': 2.30 };
        var REAL_DIV_CTI  = { 'Retail Banking Services': 39.3, 'Business Banking': 32.2, 'Institutional Banking and Markets': 40.6, 'New Zealand (ASB)': 46.4 };
        var REAL_DIV_NPAT = { 'Retail Banking Services': 5587, 'Business Banking': 4544, 'Institutional Banking and Markets': 1258, 'New Zealand (ASB)': 1112 };

        var FY26_KPI_TILES = [
            { label: 'Cash NPAT',        value: '$10.98B',  change: '▲7%',    good: true,  sub: 'FY26 cash basis' },
            { label: 'NIM',              value: '2.05%',    change: '▼3bps',  good: false, sub: 'Net interest margin' },
            { label: 'CTI',              value: '45.5%',    change: '▼20bps', good: true,  sub: 'Cost-to-income ratio' },
            { label: 'ROE',              value: '14.0%',    change: '▲50bps', good: true,  sub: 'Return on equity' },
            { label: 'CET1 (APRA)',      value: '12.0%',    change: '▼30bps', good: false, sub: 'Capital adequacy' },
            { label: 'EPS (cash)',       value: '656.9c',   change: '▲7%',    good: true,  sub: 'Basic, continuing ops' },
            { label: 'DPS',             value: '505c',     change: '▲4%',    good: true,  sub: 'FY26 total, fully franked' },
            { label: 'LIE rate',         value: '8bps',     change: '▲1bp',   good: false, sub: 'Of gross loans & advances' },
            { label: 'Pre-prov. profit', value: '$16.5B',   change: '▲6%',    good: true,  sub: 'Pre-provision profit' },
        ];

        // ---------------------------------------------------------------- inject fonts/styles
        var styleEl = document.createElement('style');
        styleEl.textContent = [
            '@import url("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600;700&display=swap");',
            '#blm_outer { display:flex; width:100%; min-height:' + (NUM_CHAPTERS * viewH) + 'px; position:relative; box-sizing:border-box; }',
            '#blm_left  { width:45%; flex-shrink:0; }',
            '#blm_right { width:55%; flex-shrink:0; position:relative; }',
            '#blm_chart_col { position:absolute; top:0; left:0; width:100%; height:' + viewH + 'px; }',
            '.blm-section { min-height:' + viewH + 'px; display:flex; flex-direction:column; justify-content:center; padding:64px 56px 64px 64px; box-sizing:border-box; }',
            '.blm-eyebrow { font-family:"Inter",sans-serif; font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:16px; opacity:0.7; }',
            '.blm-key-stat { font-family:"Playfair Display",Georgia,serif; font-size:64px; font-weight:900; line-height:1.0; margin-bottom:8px; }',
            '.blm-key-label { font-family:"Inter",sans-serif; font-size:13px; font-weight:500; letter-spacing:0.05em; margin-bottom:28px; opacity:0.75; }',
            '.blm-headline { font-family:"Playfair Display",Georgia,serif; font-size:28px; font-weight:700; line-height:1.25; margin-bottom:20px; }',
            '.blm-pull { font-family:"Playfair Display",Georgia,serif; font-style:italic; font-size:17px; line-height:1.5; padding-left:20px; margin-bottom:24px; }',
            '.blm-body { font-family:"Inter",sans-serif; font-size:14px; line-height:1.7; }',
            '.blm-hr { border:none; border-top:1px solid rgba(255,255,255,0.25); margin:24px 0; width:80px; }',
            '.blm-light .blm-eyebrow { color:#64748b; }',
            '.blm-light .blm-key-stat { color:#1e3a5f; }',
            '.blm-light .blm-key-label { color:#475569; }',
            '.blm-light .blm-headline { color:#1e3a5f; }',
            '.blm-light .blm-pull { color:#334155; border-left:3px solid #2a78d6; }',
            '.blm-light .blm-body { color:#475569; }',
            '.blm-dark .blm-eyebrow { color:rgba(255,255,255,0.65); }',
            '.blm-dark .blm-key-stat { color:#ffffff; }',
            '.blm-dark .blm-key-label { color:rgba(255,255,255,0.7); }',
            '.blm-dark .blm-headline { color:#93c5fd; }',
            '.blm-dark .blm-pull { color:#cbd5e1; border-left:3px solid #60a5fa; }',
            '.blm-dark .blm-body { color:#cbd5e1; }',
        ].join('\n');
        document.head.appendChild(styleEl);
        parentElement._blmStyleEl = styleEl;

        // ---------------------------------------------------------------- outer layout
        var outer = document.createElement('div');
        outer.id = 'blm_outer';
        root.appendChild(outer);

        // ---- Left column: 8 text sections
        var leftCol = document.createElement('div');
        leftCol.id = 'blm_left';
        outer.appendChild(leftCol);

        // Splash section (chapter 0)
        var splashSection = document.createElement('div');
        splashSection.className = 'blm-section blm-dark';
        splashSection.style.cssText = 'background:#1e3a5f;min-height:' + viewH + 'px;align-items:center;text-align:center;justify-content:center;';
        splashSection.innerHTML = [
            '<div style="font-family:Inter,sans-serif;font-size:18px;font-weight:300;color:rgba(255,255,255,0.7);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:24px;">Commonwealth Bank</div>',
            '<div style="font-family:\'Playfair Display\',Georgia,serif;font-size:96px;font-weight:900;color:#ffffff;line-height:1.0;margin-bottom:12px;">A$30.2B</div>',
            '<div style="font-family:Inter,sans-serif;font-size:18px;font-weight:300;color:rgba(255,255,255,0.85);letter-spacing:0.04em;margin-bottom:24px;">FY26 Full Year Earnings</div>',
            '<hr class="blm-hr" style="margin:24px auto;">',
            '<div style="font-family:Inter,sans-serif;font-size:12px;color:rgba(255,255,255,0.45);letter-spacing:0.06em;">Seven chapters. Scroll to explore.</div>',
        ].join('');
        leftCol.appendChild(splashSection);

        // Chapters 1–7
        var CHAPTER_NUMS = ['01','02','03','04','05','06','07'];
        for (var ci = 1; ci < NUM_CHAPTERS; ci++) {
            var comm = getCommentary(ci - 1); // commentary keys 0-6 map to chapters 1-7
            var bg = CH_BG[ci];
            var isDark = (bg === '#1e3a5f' || bg === '#0f172a');
            var themeClass = isDark ? 'blm-dark' : 'blm-light';

            var sec = document.createElement('div');
            sec.className = 'blm-section ' + themeClass;
            sec.style.cssText = 'background:' + bg + ';';
            sec.setAttribute('data-chapter', String(ci));

            var eyebrow = document.createElement('div');
            eyebrow.className = 'blm-eyebrow';
            eyebrow.textContent = 'Chapter ' + CHAPTER_NUMS[ci - 1];

            var keyStat = document.createElement('div');
            keyStat.className = 'blm-key-stat';
            keyStat.textContent = comm.key_stat || '';

            var keyLabel = document.createElement('div');
            keyLabel.className = 'blm-key-label';
            keyLabel.textContent = comm.key_label || '';

            var headline = document.createElement('div');
            headline.className = 'blm-headline';
            headline.textContent = comm.headline || '';

            var pull = document.createElement('div');
            pull.className = 'blm-pull';
            pull.textContent = comm.pull_quote || '';

            var body = document.createElement('div');
            body.className = 'blm-body';
            body.textContent = comm.body || '';

            sec.appendChild(eyebrow);
            sec.appendChild(keyStat);
            sec.appendChild(keyLabel);
            sec.appendChild(headline);
            sec.appendChild(pull);
            sec.appendChild(body);
            leftCol.appendChild(sec);
        }

        // ---- Right column: chart column (manually repositioned)
        var rightCol = document.createElement('div');
        rightCol.id = 'blm_right';
        outer.appendChild(rightCol);

        var chartCol = document.createElement('div');
        chartCol.id = 'blm_chart_col';
        chartCol.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:' + viewH + 'px;overflow:hidden;';
        rightCol.appendChild(chartCol);

        // ---------------------------------------------------------------- D3 setup
        var parseDate = d3.timeParse('%Y-%m-%d');

        var parsedMonthly = monthly.map(function(d) {
            return Object.assign({}, d, { _date: parseDate(d.date) });
        }).filter(function(d) { return d._date; });

        var parsedStock = stock.map(function(d) {
            return { _date: parseDate(d.date), value: +d.value };
        }).filter(function(d) { return d._date; });

        var cW = Math.max(400, (parentElement.offsetWidth || 1200) * 0.55);
        var cH = viewH;
        var margin = { top: 60, right: 60, bottom: 70, left: 64 };

        var allDates = parsedMonthly.map(function(d) { return d._date; })
            .concat(parsedStock.map(function(d) { return d._date; }));
        var xScale = d3.scaleTime()
            .domain(d3.extent(allDates))
            .range([margin.left, cW - margin.right]);

        var maxIncome = d3.max(parsedMonthly, function(d) { return +d.operating_income; }) || 1;
        var yScaleIncome = d3.scaleLinear()
            .domain([0, maxIncome * 1.12])
            .range([cH - margin.bottom, margin.top]);

        var maxSegVal = d3.max(segments, function(seg) {
            return d3.max(parsedMonthly, function(d) { return +d[seg] || 0; });
        }) || maxIncome * 0.5;
        var yScaleSegs = d3.scaleLinear()
            .domain([0, maxSegVal * 1.18])
            .range([cH - margin.bottom, margin.top]);

        var maxStock = d3.max(parsedStock, function(d) { return d.value; }) || 1;
        var minStock = d3.min(parsedStock, function(d) { return d.value; }) || 0;
        var yScaleStock = d3.scaleLinear()
            .domain([minStock * 0.95, maxStock * 1.05])
            .range([cH - margin.bottom, margin.top]);

        // ---------------------------------------------------------------- SVG layer
        var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.setAttribute('width', '100%');
        svgEl.setAttribute('height', cH);
        svgEl.style.cssText = 'position:absolute;inset:0;pointer-events:none;';
        chartCol.appendChild(svgEl);
        var svg = d3.select(svgEl);
        var g = svg.append('g');

        // ---- Background rect (changes with chapter)
        var bgRect = svg.insert('rect', ':first-child')
            .attr('width', '100%').attr('height', cH)
            .attr('fill', '#1e3a5f');

        // ---- Grid
        var gridG = g.append('g').attr('class', 'blm-grid');
        function drawGrid(yScale) {
            var ticks = yScale.ticks(5);
            gridG.selectAll('line').data(ticks).join('line')
                .attr('x1', margin.left).attr('x2', cW - margin.right)
                .attr('y1', function(d) { return yScale(d); })
                .attr('y2', function(d) { return yScale(d); })
                .attr('stroke', 'rgba(100,116,139,0.25)')
                .attr('stroke-dasharray', '4,3')
                .attr('stroke-width', 1);
        }

        // ---- Axes
        var xAxisG = g.append('g')
            .attr('transform', 'translate(0,' + (cH - margin.bottom) + ')')
            .attr('opacity', 0);
        var yAxisG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',0)')
            .attr('opacity', 0);

        function styleAxis(axG) {
            axG.select('.domain').remove();
            axG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
            axG.selectAll('line').attr('stroke', '#475569');
        }

        function showAxes(yScale, isStock) {
            var fmt = isStock
                ? function(d) { return 'A$' + d.toFixed(0); }
                : function(d) { return 'A$' + d3.format('.2s')(d).replace('G','B'); };
            xAxisG.interrupt().transition().duration(500).attr('opacity', 1)
                .call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0))
                .on('end', function() { styleAxis(xAxisG); });
            yAxisG.interrupt().transition().duration(500).attr('opacity', 1)
                .call(d3.axisLeft(yScale).ticks(5).tickFormat(fmt).tickSizeOuter(0))
                .on('end', function() { styleAxis(yAxisG); });
            drawGrid(yScale);
        }
        function hideAxes() {
            xAxisG.interrupt().transition().duration(300).attr('opacity', 0);
            yAxisG.interrupt().transition().duration(300).attr('opacity', 0);
            gridG.selectAll('line').remove();
        }

        // ==============================================================
        // CHART 1: Group OI area + line (navy bg) — chapter 1
        // ==============================================================
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
            .attr('fill', 'rgba(42,120,214,0.15)')
            .attr('d', totalAreaGen).attr('opacity', 0);
        var totalLinePath = g.append('path')
            .datum(parsedMonthly)
            .attr('fill', 'none').attr('stroke', '#2a78d6').attr('stroke-width', 2.5)
            .attr('d', totalLineGen).attr('opacity', 0);

        var totalLineLen = 0;
        requestAnimationFrame(function() {
            try { totalLineLen = totalLinePath.node().getTotalLength(); } catch(e) {}
            totalLinePath.attr('stroke-dasharray', totalLineLen + ' ' + totalLineLen)
                .attr('stroke-dashoffset', totalLineLen);
        });
        var totalAnimated = false;

        var annotG = g.append('g').attr('opacity', 0);
        var ANNOTS = [
            { date: '2022-05-01', label: 'Rate hiking begins', color: '#60a5fa' },
            { date: '2023-11-01', label: 'Peak 4.35%',         color: '#60a5fa' },
            { date: '2025-02-01', label: 'RBA ↓ easing',       color: '#34d399' },
        ];
        ANNOTS.forEach(function(ann) {
            var ad = parseDate(ann.date);
            if (!ad) return;
            var ax = xScale(ad);
            annotG.append('line').attr('x1', ax).attr('x2', ax)
                .attr('y1', margin.top).attr('y2', cH - margin.bottom)
                .attr('stroke', ann.color).attr('stroke-width', 1).attr('stroke-dasharray', '4,4');
            annotG.append('text').attr('x', ax + 3).attr('y', margin.top + 14)
                .attr('font-size', '9px').attr('font-weight', '600').attr('fill', ann.color)
                .text(ann.label);
        });
        var lastM = parsedMonthly.length ? parsedMonthly[parsedMonthly.length - 1] : null;
        if (lastM) {
            var epx = xScale(lastM._date), epy = yScaleIncome(+lastM.operating_income);
            annotG.append('circle').attr('cx', epx).attr('cy', epy).attr('r', 5).attr('fill', '#2a78d6');
            annotG.append('text').attr('x', epx + 8).attr('y', epy).attr('dy', '0.35em')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', '#93c5fd')
                .text('FY26: A$30.2B ▲6%');
        }

        // ==============================================================
        // CHART 2: Divisional TREEMAP — chapter 2
        // ==============================================================
        var totalBySeg = {};
        segments.forEach(function(seg) { totalBySeg[seg] = 0; });
        parsedMonthly.forEach(function(d) {
            segments.forEach(function(seg) { totalBySeg[seg] += (+d[seg] || 0); });
        });
        var totalAll = segments.reduce(function(s, seg) { return s + totalBySeg[seg]; }, 0) || 1;

        var tmG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            .attr('opacity', 0);
        var tmBuilt = false;

        function buildTreemap() {
            var iW = cW - margin.left - margin.right;
            var iH = cH - margin.top - margin.bottom;
            tmG.selectAll('*').remove();
            var rootData = {
                name: 'Group',
                children: segments.map(function(seg) {
                    return { name: seg, value: totalBySeg[seg], npat: REAL_DIV_NPAT[seg] || 0, short: SEG_SHORT[seg] || seg };
                })
            };
            var hier = d3.hierarchy(rootData).sum(function(d) { return d.value || 0; })
                .sort(function(a, b) { return b.value - a.value; });
            d3.treemap().size([iW, iH]).padding(4).round(true)(hier);
            var leaves = hier.leaves();

            var rects = tmG.selectAll('rect').data(leaves).enter().append('rect')
                .attr('x', function(d) { return d.x0; }).attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
                .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); })
                .attr('fill', function(d) { return SEG_COLORS[d.data.name] || '#888'; })
                .attr('stroke', 'white').attr('stroke-width', 2).attr('rx', 4).attr('opacity', 0);
            rects.transition().duration(400).delay(function(d,i){ return i*100; })
                .attr('opacity', 1);

            var lblGs = tmG.selectAll('g.tml').data(leaves).enter().append('g')
                .attr('class', 'tml').attr('opacity', 0).attr('pointer-events', 'none');
            lblGs.each(function(d) {
                var w = d.x1 - d.x0, h = d.y1 - d.y0;
                if (w < 80) return;
                var cx = d.x0 + w/2, cy = d.y0 + h/2;
                var pct = (d.data.value / totalAll * 100).toFixed(1) + '%';
                var incStr = d.data.value > 1e9 ? 'A$' + (d.data.value/1e9).toFixed(1) + 'B' : 'A$' + d3.format('.3s')(d.data.value);
                var npat = d.data.npat ? '$' + (d.data.npat/1000).toFixed(2) + 'B NPAT' : '';
                d3.select(this).append('text').attr('x', cx).attr('y', cy - 14)
                    .attr('text-anchor', 'middle').attr('font-size', Math.min(13, w/5) + 'px')
                    .attr('font-weight', '700').attr('fill', 'white').text(d.data.short);
                d3.select(this).append('text').attr('x', cx).attr('y', cy + 2)
                    .attr('text-anchor', 'middle').attr('font-size', Math.min(11, w/6) + 'px')
                    .attr('fill', 'rgba(255,255,255,0.9)').text(incStr + ' · ' + pct);
                if (h > 60 && npat) {
                    d3.select(this).append('text').attr('x', cx).attr('y', cy + 16)
                        .attr('text-anchor', 'middle').attr('font-size', Math.min(10, w/7) + 'px')
                        .attr('fill', 'rgba(255,255,255,0.7)').text(npat);
                }
            });
            lblGs.transition().delay(700).duration(400).attr('opacity', 1);
            tmBuilt = true;
        }

        // ==============================================================
        // CHART 3: STREAM GRAPH — chapter 3
        // ==============================================================
        var STACK_KEYS = segments.map(function(s) { return SEG_KEY[s]; });
        var stackInput = parsedMonthly.map(function(d) {
            var row = { _date: d._date, date: d.date };
            segments.forEach(function(seg) { row[SEG_KEY[seg]] = +d[seg] || 0; });
            return row;
        });

        var streamStack = d3.stack().keys(STACK_KEYS)
            .order(d3.stackOrderNone).offset(d3.stackOffsetSilhouette);
        var streamSeries = streamStack(stackInput);

        var streamYExt = [Infinity, -Infinity];
        streamSeries.forEach(function(s) {
            s.forEach(function(d) {
                if (d[0] < streamYExt[0]) streamYExt[0] = d[0];
                if (d[1] > streamYExt[1]) streamYExt[1] = d[1];
            });
        });
        if (!isFinite(streamYExt[0])) streamYExt = [-maxIncome*0.5, maxIncome*0.5];

        var yScaleStream = d3.scaleLinear().domain(streamYExt).range([cH - margin.bottom, margin.top]);

        var streamAreaGen = d3.area()
            .x(function(d) { return xScale(d.data._date); })
            .y0(function(d) { return yScaleStream(d[0]); })
            .y1(function(d) { return yScaleStream(d[1]); })
            .curve(d3.curveMonotoneX);

        var streamPaths = {}, streamLblEls = {};
        segments.forEach(function(seg, si) {
            var col = SEG_COLORS[seg] || '#888';
            streamPaths[seg] = g.append('path').datum(streamSeries[si])
                .attr('fill', col).attr('fill-opacity', 0.82)
                .attr('d', streamAreaGen).attr('opacity', 0);
            streamLblEls[seg] = g.append('text')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', col)
                .attr('opacity', 0).text(SEG_SHORT[seg] || seg);
        });
        function updateStreamLabels(op) {
            var li = stackInput.length - 1;
            if (li < 0) return;
            var lx = xScale(stackInput[li]._date) + 5;
            segments.forEach(function(seg, si) {
                var band = streamSeries[si][li];
                var cy = (yScaleStream(band[0]) + yScaleStream(band[1])) / 2;
                streamLblEls[seg].attr('x', lx).attr('y', cy).attr('dy', '0.35em').attr('opacity', op);
            });
        }

        // ==============================================================
        // CHART 4: DIVISION CARDS OVERLAY — chapter 4
        // ==============================================================
        var divCardsEl = document.createElement('div');
        divCardsEl.style.cssText = 'position:absolute;inset:0;display:none;align-items:center;justify-content:center;z-index:5;';
        chartCol.appendChild(divCardsEl);
        var divGrid = document.createElement('div');
        divGrid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:14px;width:580px;max-width:90%;';
        divCardsEl.appendChild(divGrid);
        var selectedSeg = segments[0] || 'Retail Banking Services';
        var divCardEls = {};

        segments.forEach(function(seg, i) {
            var col = SEG_COLORS[seg] || '#888';
            var nim  = REAL_DIV_NIM[seg]  != null ? REAL_DIV_NIM[seg].toFixed(2) + '%' : '—';
            var cti  = REAL_DIV_CTI[seg]  != null ? REAL_DIV_CTI[seg].toFixed(1) + '%' : '—';
            var npat = REAL_DIV_NPAT[seg] != null ? '$' + (REAL_DIV_NPAT[seg]/1000).toFixed(2) + 'B' : '—';
            var card = document.createElement('div');
            card.style.cssText = 'background:rgba(255,255,255,0.08);backdrop-filter:blur(12px);border-radius:12px;padding:22px 24px;border:2px solid rgba(255,255,255,0.12);cursor:pointer;transition:all 0.25s ease;transform:scale(0.85);opacity:0;';
            card.innerHTML = [
                '<div style="font-size:12px;font-weight:700;color:rgba(255,255,255,0.65);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">' + (SEG_SHORT[seg] || seg) + '</div>',
                '<div style="font-size:26px;font-weight:900;font-family:\'Playfair Display\',serif;color:' + col + ';margin-bottom:8px;">' + npat + '</div>',
                '<div style="font-size:11px;color:rgba(255,255,255,0.5);">NIM <b style="color:rgba(255,255,255,0.8)">' + nim + '</b> &nbsp;|&nbsp; CTI <b style="color:rgba(255,255,255,0.8)">' + cti + '</b></div>',
            ].join('');
            card.addEventListener('click', function(e) {
                e.stopPropagation();
                selectedSeg = seg;
                updateDivCardStates();
            });
            card.addEventListener('mouseenter', function() {
                if (selectedSeg !== seg) {
                    card.style.borderColor = col + '88';
                    card.style.background = 'rgba(255,255,255,0.12)';
                }
            });
            card.addEventListener('mouseleave', function() {
                if (selectedSeg !== seg) {
                    card.style.borderColor = 'rgba(255,255,255,0.12)';
                    card.style.background = 'rgba(255,255,255,0.08)';
                }
            });
            divGrid.appendChild(card);
            divCardEls[seg] = card;
            card._animDelay = i * 70;
        });

        function updateDivCardStates() {
            segments.forEach(function(seg) {
                var card = divCardEls[seg];
                if (!card) return;
                var col = SEG_COLORS[seg] || '#888';
                if (seg === selectedSeg) {
                    card.style.borderColor = col;
                    card.style.background = col + '22';
                    card.style.boxShadow = '0 4px 24px ' + col + '44';
                } else {
                    card.style.borderColor = 'rgba(255,255,255,0.12)';
                    card.style.background = 'rgba(255,255,255,0.08)';
                    card.style.boxShadow = 'none';
                }
            });
        }
        function showDivCards() {
            divCardsEl.style.display = 'flex';
            updateDivCardStates();
            segments.forEach(function(seg) {
                var card = divCardEls[seg];
                if (!card) return;
                card.style.transform = 'scale(0.85)'; card.style.opacity = '0'; card.style.transition = 'none';
                setTimeout(function() {
                    card.style.transition = 'transform 0.4s cubic-bezier(0.34,1.2,0.64,1),opacity 0.35s ease,border-color 0.25s,background 0.25s,box-shadow 0.25s';
                    card.style.transform = 'scale(1)'; card.style.opacity = '1';
                }, card._animDelay || 0);
            });
        }
        function hideDivCards() { divCardsEl.style.display = 'none'; }

        // ==============================================================
        // CHART 5: SANKEY P&L — chapter 5
        // ==============================================================
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
            return { totalNii: totalNii, totalOther: totalOther, opexLink: opexLink, lieLink: lieLink, totalRev: totalRev, preProvision: preProvision, npat: npat };
        }

        function fmtSank(v) { return 'A$' + d3.format('.3s')(v).replace('G','B'); }

        function drawSankey() {
            if (!window.d3sankey) return;
            var dsk = window.d3sankey;
            var iW = cW - margin.left - margin.right;
            var iH = cH - margin.top - margin.bottom;
            var seg    = selectedSeg;
            var segCol = SEG_COLORS[seg] || '#2a78d6';
            var sd     = computeSankeyData(seg);
            var divNim  = REAL_DIV_NIM[seg];
            var divCti  = REAL_DIV_CTI[seg];
            var divNpat = REAL_DIV_NPAT[seg];

            sankeyG.selectAll('*').remove();

            var nodeData = [
                { name: 'Net Interest Income' },
                { name: 'Fee & Other Income' },
                { name: 'Gross Revenue' },
                { name: 'Operating Expenses' },
                { name: 'Pre-Provision Profit' },
                { name: 'Loan Impairment' },
                { name: 'Cash NPAT' },
            ];
            var linkData = [
                { source: 0, target: 2, value: sd.totalNii },
                { source: 1, target: 2, value: sd.totalOther },
                { source: 2, target: 3, value: sd.opexLink },
                { source: 2, target: 4, value: sd.preProvision },
                { source: 4, target: 5, value: sd.lieLink },
                { source: 4, target: 6, value: sd.npat },
            ];

            var graph;
            try {
                graph = dsk.sankey().nodeWidth(20).nodePadding(24)
                    .extent([[24, 24], [iW - 24, iH - 24]])({
                        nodes: nodeData.map(function(d) { return Object.assign({}, d); }),
                        links: linkData.map(function(d) { return Object.assign({}, d); })
                    });
            } catch(e) { return; }

            var nodes = graph.nodes, links = graph.links;

            function nColor(i) {
                if (i === 0 || i === 1) return '#0d9488';
                if (i === 2) return segCol;
                if (i === 3 || i === 5) return '#ef4444';
                return '#16a34a';
            }
            function lColor(link) {
                var ti = link.target.index !== undefined ? link.target.index : link.target;
                if (ti === 3 || ti === 5) return 'rgba(239,68,68,0.3)';
                return d3.color(segCol) ? d3.color(segCol).copy({opacity:0.35}).formatRgb() : segCol + '55';
            }

            var linkPath = dsk.sankeyLinkHorizontal();
            sankeyG.append('g').selectAll('path').data(links).enter().append('path')
                .attr('d', linkPath).attr('stroke', function(d) { return lColor(d); })
                .attr('stroke-width', function(d) { return Math.max(1, d.width); })
                .attr('fill', 'none').attr('opacity', 0)
                .transition().duration(500).delay(function(d,i){ return i*90; })
                .ease(d3.easeCubicInOut).attr('opacity', 1);

            sankeyG.append('g').selectAll('rect').data(nodes).enter().append('rect')
                .attr('x', function(d) { return d.x0; }).attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return d.x1 - d.x0; })
                .attr('height', function(d) { return Math.max(1, d.y1 - d.y0); })
                .attr('fill', function(d, i) { return nColor(i); })
                .attr('rx', 3).attr('opacity', 0)
                .transition().duration(400).delay(function(d,i){ return i*70; })
                .ease(d3.easeBackOut.overshoot(1.2)).attr('opacity', 1);

            var nlG = sankeyG.append('g');
            nodes.forEach(function(d, i) {
                var isRight = d.x0 > iW / 2;
                var lx = isRight ? d.x1 + 6 : d.x0 - 6;
                var ly = (d.y0 + d.y1) / 2;
                var anchor = isRight ? 'start' : 'end';
                nlG.append('text').attr('x', lx).attr('y', ly - 8)
                    .attr('text-anchor', anchor).attr('dominant-baseline', 'middle')
                    .attr('font-size', '10px').attr('font-weight', '700').attr('fill', '#e2e8f0').attr('opacity', 0)
                    .text(d.name).transition().delay(600).duration(400).attr('opacity', 1);
                nlG.append('text').attr('x', lx).attr('y', ly + 5)
                    .attr('text-anchor', anchor).attr('dominant-baseline', 'middle')
                    .attr('font-size', '9px').attr('fill', '#94a3b8').attr('opacity', 0)
                    .text(fmtSank(d.value || 0)).transition().delay(700).duration(400).attr('opacity', 1);
                if (i === 0 && divNim != null) {
                    nlG.append('text').attr('x', lx).attr('y', ly + 17)
                        .attr('text-anchor', anchor).attr('font-size', '8px').attr('font-weight', '600')
                        .attr('fill', '#34d399').attr('opacity', 0)
                        .text('NIM ' + divNim.toFixed(2) + '%')
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
                if (i === 6 && divNpat != null) {
                    nlG.append('text').attr('x', lx).attr('y', ly + 17)
                        .attr('text-anchor', anchor).attr('font-size', '8px').attr('font-weight', '600')
                        .attr('fill', '#4ade80').attr('opacity', 0)
                        .text('FY26: $' + (divNpat/1000).toFixed(3) + 'B')
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
            });
            if (divCti != null) {
                var opN = nodes[3];
                if (opN) {
                    sankeyG.append('text')
                        .attr('x', (opN.x0 + opN.x1)/2).attr('y', opN.y0 - 6)
                        .attr('text-anchor', 'middle').attr('font-size', '8px')
                        .attr('font-weight', '700').attr('fill', '#f87171').attr('opacity', 0)
                        .text('CTI ' + divCti.toFixed(1) + '%')
                        .transition().delay(900).duration(400).attr('opacity', 1);
                }
            }
        }

        // ==============================================================
        // CHART 6: STOCK + 20-WEEK MA — chapter 6
        // ==============================================================
        var stockAreaGen = d3.area()
            .x(function(d) { return xScale(d._date); })
            .y0(function() { return yScaleStock(minStock * 0.95); })
            .y1(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);
        var stockLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);

        var stockAreaPath = g.append('path').datum(parsedStock)
            .attr('fill', 'rgba(15,76,129,0.18)').attr('d', stockAreaGen).attr('opacity', 0);
        var stockLinePath = g.append('path').datum(parsedStock)
            .attr('fill', 'none').attr('stroke', '#3b82f6').attr('stroke-width', 2)
            .attr('d', stockLineGen).attr('opacity', 0);

        var stockLineLen = 0;
        requestAnimationFrame(function() {
            try { stockLineLen = stockLinePath.node().getTotalLength(); } catch(e) {}
            stockLinePath.attr('stroke-dasharray', stockLineLen + ' ' + stockLineLen)
                .attr('stroke-dashoffset', stockLineLen);
        });
        var stockAnimated = false;

        var movingAvgData = parsedStock.map(function(d, i) {
            var w20 = parsedStock.slice(Math.max(0, i - 19), i + 1);
            return { _date: d._date, value: d3.mean(w20, function(x) { return x.value; }) };
        });
        var maLineGen = d3.line()
            .x(function(d) { return xScale(d._date); })
            .y(function(d) { return yScaleStock(d.value); })
            .curve(d3.curveMonotoneX);
        var maLine = g.append('path').datum(movingAvgData)
            .attr('fill', 'none').attr('stroke', '#f97316').attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '5,3').attr('d', maLineGen).attr('opacity', 0);

        var maLabelEl = null;
        if (movingAvgData.length > 0) {
            var lastMa = movingAvgData[movingAvgData.length - 1];
            maLabelEl = g.append('text')
                .attr('x', xScale(lastMa._date) + 6).attr('y', yScaleStock(lastMa.value))
                .attr('dy', '0.35em').attr('font-size', '10px').attr('font-weight', '700')
                .attr('fill', '#f97316').attr('opacity', 0).text('20-wk MA');
        }

        var peakRow = parsedStock.length
            ? parsedStock.reduce(function(a, b) { return b.value > a.value ? b : a; }) : null;
        var peakG = g.append('g').attr('opacity', 0);
        if (peakRow) {
            var px = xScale(peakRow._date), py = yScaleStock(peakRow.value);
            peakG.append('line').attr('x1', px).attr('x2', px).attr('y1', py).attr('y2', py + 28)
                .attr('stroke', '#3b82f6').attr('stroke-width', 1).attr('stroke-dasharray', '3,2');
            peakG.append('text').attr('x', px).attr('y', py - 6).attr('text-anchor', 'middle')
                .attr('font-size', '9px').attr('font-weight', '700').attr('fill', '#93c5fd').text('FY24 peak');
        }

        // ==============================================================
        // CHART 7: KPI GRID — chapter 7 (DOM overlay)
        // ==============================================================
        var kpiGridEl = document.createElement('div');
        kpiGridEl.style.cssText = 'position:absolute;inset:0;display:none;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);gap:12px;padding:40px;box-sizing:border-box;background:#1e3a5f;';
        chartCol.appendChild(kpiGridEl);

        FY26_KPI_TILES.forEach(function(spec) {
            var tile = document.createElement('div');
            tile.style.cssText = 'background:rgba(255,255,255,0.06);backdrop-filter:blur(12px);border-radius:12px;padding:18px 20px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;gap:4px;transform:translateY(14px);opacity:0;transition:none;';
            tile.innerHTML = [
                '<div style="font-size:11px;font-weight:600;letter-spacing:0.07em;color:rgba(255,255,255,0.5);text-transform:uppercase;">' + spec.label + '</div>',
                '<div style="display:flex;align-items:baseline;gap:8px;">',
                '<div style="font-family:\'Playfair Display\',serif;font-size:1.55rem;font-weight:900;color:#ffffff;line-height:1.1;">' + spec.value + '</div>',
                '<div style="font-size:0.75rem;font-weight:700;color:' + (spec.good ? '#4ade80' : '#f87171') + ';">' + spec.change + '</div>',
                '</div>',
                '<div style="font-size:11px;color:rgba(255,255,255,0.4);">' + spec.sub + '</div>',
            ].join('');
            kpiGridEl.appendChild(tile);
        });

        var kpiFooter = document.createElement('div');
        kpiFooter.style.cssText = 'grid-column:1/-1;font-size:10px;color:rgba(255,255,255,0.25);text-align:center;align-self:end;';
        kpiFooter.textContent = 'Source: CBA Profit Announcement, year ended 30 June 2026. Chart data is illustrative.';
        kpiGridEl.appendChild(kpiFooter);

        function showKpiGrid() {
            kpiGridEl.style.display = 'grid';
            var tiles = kpiGridEl.querySelectorAll('div[style*="translateY"]');
            tiles.forEach(function(tile, ci) {
                setTimeout(function() {
                    tile.style.transition = 'transform 0.45s cubic-bezier(0.34,1.2,0.64,1),opacity 0.4s ease';
                    tile.style.transform = 'translateY(0)';
                    tile.style.opacity = '1';
                }, ci * 65);
            });
        }
        function hideKpiGrid() {
            kpiGridEl.style.display = 'none';
            var tiles = kpiGridEl.querySelectorAll('div[style*="opacity"]');
            tiles.forEach(function(tile) {
                tile.style.transform = 'translateY(14px)';
                tile.style.opacity = '0';
                tile.style.transition = 'none';
            });
        }

        // ==============================================================
        // CHAPTER ACTIVATION
        // ==============================================================
        var currentChapter = -1;

        function hideAllCharts() {
            totalAreaPath.interrupt().transition().duration(300).attr('opacity', 0);
            totalLinePath.interrupt().transition().duration(300).attr('opacity', 0);
            annotG.interrupt().transition().duration(300).attr('opacity', 0);
            tmG.interrupt().transition().duration(300).attr('opacity', 0);
            segments.forEach(function(seg) {
                streamPaths[seg].interrupt().transition().duration(300).attr('opacity', 0);
                streamLblEls[seg].interrupt().transition().duration(300).attr('opacity', 0);
            });
            hideDivCards();
            sankeyG.interrupt().transition().duration(300).attr('opacity', 0);
            stockAreaPath.interrupt().transition().duration(300).attr('opacity', 0);
            stockLinePath.interrupt().transition().duration(300).attr('opacity', 0);
            maLine.interrupt().transition().duration(300).attr('opacity', 0);
            if (maLabelEl) maLabelEl.interrupt().transition().duration(300).attr('opacity', 0);
            peakG.interrupt().transition().duration(300).attr('opacity', 0);
            hideKpiGrid();
            hideAxes();
        }

        function activateChapter(ch) {
            if (ch === currentChapter) return;
            currentChapter = ch;

            // Chart bg colour
            var chBg = CH_BG[ch] || '#ffffff';
            bgRect.transition().duration(500).attr('fill', chBg);

            // Hide all, then show what belongs to this chapter
            hideAllCharts();

            if (ch === 0) {
                // Splash: navy bg, no chart
                svgEl.style.opacity = '0';
                return;
            }

            svgEl.style.opacity = '1';

            if (ch === 1) {
                // Area income
                showAxes(yScaleIncome, false);
                totalAreaPath.interrupt().transition().duration(800).ease(d3.easeCubicInOut).attr('opacity', 1);
                if (!totalAnimated) {
                    totalAnimated = true;
                    totalLinePath.interrupt().attr('opacity', 1).attr('stroke-dashoffset', totalLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut).attr('stroke-dashoffset', 0)
                        .on('end', function() { annotG.interrupt().transition().duration(500).attr('opacity', 1); });
                } else {
                    totalLinePath.interrupt().transition().duration(400).attr('opacity', 1).attr('stroke-dashoffset', 0)
                        .on('end', function() { annotG.interrupt().transition().duration(400).attr('opacity', 1); });
                }
            } else if (ch === 2) {
                // Treemap
                tmG.interrupt().attr('opacity', 1);
                if (!tmBuilt) { buildTreemap(); }
                else {
                    tmG.selectAll('g.tml').interrupt().attr('opacity', 0)
                        .transition().delay(300).duration(400).attr('opacity', 1);
                }
            } else if (ch === 3) {
                // Stream graph
                showAxes(yScaleStream, false);
                segments.forEach(function(seg, si) {
                    streamPaths[seg].interrupt().transition().delay(si * 90).duration(700).ease(d3.easeCubicInOut).attr('opacity', 0.82);
                });
                setTimeout(function() { if (currentChapter === 3) { updateStreamLabels(1); } }, 900);
            } else if (ch === 4) {
                // Division cards
                svgEl.style.opacity = '0';
                bgRect.attr('fill', '#1e3a5f');
                showDivCards();
                hideDivCards(); // immediately re-show via showDivCards proper
                setTimeout(function() { showDivCards(); }, 50);
            } else if (ch === 5) {
                // Sankey
                bgRect.attr('fill', '#0f172a');
                sankeyG.selectAll('*').remove();
                if (window.d3sankey) {
                    drawSankey();
                    sankeyG.interrupt().transition().duration(300).attr('opacity', 1);
                } else {
                    loadD3Sankey().then(function() {
                        drawSankey();
                        sankeyG.interrupt().transition().duration(300).attr('opacity', 1);
                    });
                }
            } else if (ch === 6) {
                // Stock + MA
                showAxes(yScaleStock, true);
                stockAreaPath.interrupt().transition().duration(600).attr('opacity', 1);
                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath.interrupt().attr('opacity', 1).attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut).attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            peakG.interrupt().transition().duration(400).attr('opacity', 1);
                            maLine.interrupt().transition().duration(600).attr('opacity', 0.9);
                            if (maLabelEl) maLabelEl.interrupt().transition().delay(400).duration(400).attr('opacity', 1);
                        });
                } else {
                    stockLinePath.interrupt().transition().duration(400).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    peakG.interrupt().transition().duration(400).attr('opacity', 1);
                    maLine.interrupt().transition().duration(400).attr('opacity', 0.9);
                    if (maLabelEl) maLabelEl.interrupt().transition().duration(400).attr('opacity', 1);
                }
            } else if (ch === 7) {
                // KPI grid
                svgEl.style.opacity = '0';
                bgRect.attr('fill', '#1e3a5f');
                showKpiGrid();
            }
        }

        // ==============================================================
        // SCROLL DRIVER: manually reposition chart column
        // Streamlit scrolls inside section.stMain (NOT window) — find the
        // real scroll container and measure against it.
        // ==============================================================
        function findScrollContainer(el) {
            var node = el ? el.parentElement : null;
            while (node && node !== document.body) {
                var s = window.getComputedStyle(node);
                if ((s.overflowY === 'auto' || s.overflowY === 'scroll') &&
                    node.scrollHeight > node.clientHeight + 20) {
                    return node;
                }
                node = node.parentElement;
            }
            return document.querySelector('section.stMain') || window;
        }

        var scrollContainer = findScrollContainer(outer);

        function onScroll() {
            // scrolled = how far the top of `outer` has moved above the
            // scroll container's viewport top.
            var oRect = outer.getBoundingClientRect();
            var cTop = (scrollContainer === window || !scrollContainer.getBoundingClientRect)
                ? 0 : scrollContainer.getBoundingClientRect().top;
            var scrolled = Math.max(0, cTop - oRect.top);
            var totalH = NUM_CHAPTERS * viewH;
            var maxOffset = totalH - viewH;
            var offset = Math.min(scrolled, maxOffset);

            chartCol.style.top = offset + 'px';

            // Chapter detection — switch when a section is half-visible.
            var ch = Math.min(Math.floor((scrolled + viewH * 0.5) / viewH), NUM_CHAPTERS - 1);
            activateChapter(ch);
        }

        // Attach scroll listener to the REAL scroll container.
        var scrollHandler = function() { onScroll(); };
        scrollContainer.addEventListener('scroll', scrollHandler, { passive: true });
        // Also listen on window as a fallback (some layouts scroll the window).
        window.addEventListener('scroll', scrollHandler, { passive: true });
        parentElement._blmScroll = scrollHandler;
        parentElement._blmScrollTarget = scrollContainer;

        // Resize: rebuild scales, redraw
        var resizeHandler = function() {
            viewH = Math.max(700, window.innerHeight || 900);
            cW = Math.max(400, (parentElement.offsetWidth || 1200) * 0.55);
            xScale.range([margin.left, cW - margin.right]);
            yScaleIncome.range([cH - margin.bottom, margin.top]);
            yScaleSegs.range([cH - margin.bottom, margin.top]);
            yScaleStream.range([cH - margin.bottom, margin.top]);
            yScaleStock.range([cH - margin.bottom, margin.top]);

            totalAreaPath.attr('d', totalAreaGen);
            totalLinePath.attr('d', totalLineGen);
            segments.forEach(function(seg) { streamPaths[seg].attr('d', streamAreaGen); });
            stockAreaPath.attr('d', stockAreaGen);
            stockLinePath.attr('d', stockLineGen);
            maLine.attr('d', maLineGen);

            if (currentChapter === 2) { tmBuilt = false; buildTreemap(); }
            if (currentChapter === 3) { updateStreamLabels(1); }
            if (currentChapter === 5 && window.d3sankey) { drawSankey(); }
            if (maLabelEl && movingAvgData.length > 0) {
                var lMa2 = movingAvgData[movingAvgData.length - 1];
                maLabelEl.attr('x', xScale(lMa2._date) + 6).attr('y', yScaleStock(lMa2.value));
            }

            onScroll();
        };
        window.addEventListener('resize', resizeHandler);
        parentElement._blmResize = resizeHandler;

        // Resize observer for iframe width changes
        if (window.ResizeObserver) {
            var ro = new ResizeObserver(function() { resizeHandler(); });
            ro.observe(parentElement);
            parentElement._blmRO = ro;
        }

        // Initial render
        requestAnimationFrame(function() {
            svgEl.style.opacity = '0';
            onScroll();
        });

    } // end buildStory
}
"""

_bloomberg_editorial_component = st.components.v2.component(
    "bloomberg_editorial",
    html=_HTML,
    js=_JS,
    isolate_styles=False,
)


def st_bloomberg_editorial(
    data: dict,
    *,
    key: str = "bloomberg",
    height: int = 9000,
) -> None:
    """Render Bloomberg Red Meat editorial scrollytelling as a Streamlit V2 component.

    Parameters
    ----------
    data:
        Dictionary with keys:
            monthly     — same format as st_scrollytelling
            stock       — list of {date, value} weekly closes
            kpis        — computed KPI metrics dict
            real_kpis   — CBA FY26 actual KPIs dict
            segments    — ordered list of segment name strings
            commentary  — dict keyed "0"–"6" with headline/body/pull_quote/key_stat/key_label
    key:
        Unique Streamlit component key.
    height:
        Pixel height allocated by Streamlit. 9000 for 8 × ~100vh sections.
    """
    _bloomberg_editorial_component(
        data=data,
        default=None,
        key=key,
        height=height,
    )
