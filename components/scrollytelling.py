"""Scrollytelling earnings story — Streamlit V2 component. CFO-grade, grounded in CBA FY26 data. v12"""
from __future__ import annotations
import streamlit as st

# ---------------------------------------------------------------------------
# HTML skeleton
# ---------------------------------------------------------------------------
_HTML = '<div id="st_scroll_root" style="width:100%;"></div>'

# ---------------------------------------------------------------------------
# JS module (D3 v7) — v10
# ---------------------------------------------------------------------------
_JS = r"""
/* v13 */
export default function(component) {
    const { parentElement, data } = component;

    // ------------------------------------------------------------------ guard
    if (!data || !data.monthly || !data.monthly.length) return;

    // ----------------------------------------------------------------- cleanup previous render
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
    if (parentElement._keydownHandler) {
        document.removeEventListener('keydown', parentElement._keydownHandler);
        parentElement._keydownHandler = null;
    }
    // Remove stale kpiGrid if present from a previous render
    if (parentElement._kpiGrid) {
        try { parentElement._kpiGrid.remove(); } catch(e) {}
        parentElement._kpiGrid = null;
    }

    const root = parentElement.querySelector('#st_scroll_root');
    if (!root) return;
    root.innerHTML = '';

    const monthly   = data.monthly  || [];
    const stock     = data.stock    || [];
    const kpis      = data.kpis     || {};
    const real_kpis = data.real_kpis || {};
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

    loadD3().then(loadD3Sankey).then(buildStory).catch(function(err) {
        root.innerHTML = '<p style="color:red;padding:12px;">D3 failed to load: ' + err + '</p>';
    });

    // Return teardown to V2 component runtime
    return function() {
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
        if (parentElement._keydownHandler) {
            document.removeEventListener('keydown', parentElement._keydownHandler);
            parentElement._keydownHandler = null;
        }
        if (parentElement._kpiGrid) {
            try { parentElement._kpiGrid.remove(); } catch(e) {}
            parentElement._kpiGrid = null;
        }
    };

    // =====================================================================
    // MAIN BUILD
    // =====================================================================
    function buildStory() {
        var d3 = window.d3;

        // ------------------------------------------------ Dimensions
        var viewH = Math.max(600, window.innerHeight || 900);
        var W     = Math.max(900, parentElement.offsetWidth || 1440);
        var margin = { top: 70, right: 120, bottom: 90, left: 72 };
        var innerW = W - margin.left - margin.right;
        var innerH = viewH - margin.top - margin.bottom;

        // ------------------------------------------------ Real CBA FY26 divisional data
        var REAL_DIV_NIM = {
            "Retail Banking Services":            2.50,
            "Business Banking":                   3.39,
            "Institutional Banking and Markets":  0.87,
            "New Zealand (ASB)":                  2.30
        };
        var REAL_DIV_CTI = {
            "Retail Banking Services":            39.3,
            "Business Banking":                   32.2,
            "Institutional Banking and Markets":  40.6,
            "New Zealand (ASB)":                  46.4
        };
        var REAL_DIV_NPAT = {
            "Retail Banking Services":            5587,
            "Business Banking":                   4544,
            "Institutional Banking and Markets":  1258,
            "New Zealand (ASB)":                  1112
        };

        // ------------------------------------------------ FY26 KPI scorecard
        var FY26_KPI_TILES = [
            { label: 'Cash NPAT',        value: '$10.98B', change: '▲7%',    good: true,  sub: 'FY26 cash basis' },
            { label: 'NIM',              value: '2.05%',   change: '▼3bps',  good: false, sub: 'Net interest margin' },
            { label: 'CTI',              value: '45.5%',   change: '▼20bps', good: true,  sub: 'Cost-to-income ratio' },
            { label: 'ROE',              value: '14.0%',   change: '▲50bps', good: true,  sub: 'Return on equity' },
            { label: 'CET1 (APRA)',      value: '12.0%',   change: '▼30bps', good: false, sub: 'Capital adequacy' },
            { label: 'EPS (cash)',       value: '656.9c',  change: '▲7%',    good: true,  sub: 'Basic, continuing ops' },
            { label: 'DPS',              value: '505c',    change: '▲4%',    good: true,  sub: 'FY26 total, fully franked' },
            { label: 'LIE rate',         value: '8bps',    change: '▲1bp',   good: false, sub: 'Of gross loans & advances' },
            { label: 'Pre-prov. profit', value: '$16.5B',  change: '▲6%',    good: true,  sub: 'Pre-provision profit' },
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

        // ------------------------------------------------ Chapter metadata
        var CHAPTER_TITLES = [
            'Five Years of Income Growth',
            'Four Businesses, One Result',
            'Revenue Streams Over Time',
            'Pick a Division',
            'Where Every Dollar Goes',
            "The Market's Verdict",
            'CBA by the Numbers'
        ];

        var CHAPTER_INFO = [
            { num: '01', headline: 'Income up A$30.2B — six straight years of growth',    body: 'Net interest income rose 7% as the rate cycle matured. Other income (+4%) broadened the base. RBA rate annotations mark the key turning points.' },
            { num: '02', headline: 'Four businesses driving the result',                    body: 'Retail dominates revenue but Business Banking delivered 11% NPAT growth — the standout performer. The treemap shows each division\'s proportional contribution.' },
            { num: '03', headline: 'Revenue flows have shifted since 2022',                 body: 'Rate hikes reshaped the mix. NII expanded as margins widened, then stabilised as rates peaked. The stream shows how each division contributed through the cycle.' },
            { num: '04', headline: 'Select a division to explore',                          body: 'Click a division card to drill into its P&L anatomy. Each division has a distinct NIM, CTI, and risk profile.' },
            { num: '05', headline: 'P&L anatomy for the selected division',                 body: 'From revenue to profit — every dollar accounted for. NIM and CTI labels show real FY26 divisional data from the Profit Announcement.' },
            { num: '06', headline: "The market priced in the result early",                 body: "CBA's share price tracked earnings momentum. The 20-week moving average smooths short-term volatility to reveal the underlying trend." },
            { num: '07', headline: 'CBA FY26 — Key Performance Indicators',                body: 'All metrics from the Profit Announcement (year ended 30 June 2026). Nine KPIs that define the bank\'s financial position.' },
        ];

        // ------------------------------------------------ AI commentary
        var commentary = data.commentary || {};
        function getCommentary(i) { return commentary[String(i)] || commentary[i] || null; }

        // ------------------------------------------------ closure state
        var selectedSeg = parentElement._selectedSeg || (segments[0] || 'Retail Banking Services');
        var currentChapter = 0;
        var isTransitioning = false;
        var SEG_CARDS_DIV = null;
        var annotG = null;
        var kpiGrid = null;
        var kpiTileEls = [];

        // =====================================================================
        // DOM SHELL — all absolute-positioned inside parentElement
        // =====================================================================

        // --- root container ---
        parentElement.style.cssText = 'position:relative;width:100%;height:' + viewH + 'px;overflow:hidden;background:#f8fafc;font-family:"Inter",system-ui,sans-serif;';

        // --- SVG chart (full bleed) ---
        var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svgEl.setAttribute('width', '100%');
        svgEl.setAttribute('height', viewH);
        svgEl.style.position = 'absolute';
        svgEl.style.inset = '0';
        svgEl.style.pointerEvents = 'none';
        parentElement.appendChild(svgEl);
        var svg = d3.select(svgEl);

        // --- top bar ---
        var topBar = document.createElement('div');
        topBar.style.cssText = 'position:absolute;top:0;left:0;right:0;height:48px;display:flex;align-items:center;padding:0 32px;background:rgba(248,250,252,0.85);backdrop-filter:blur(12px);z-index:10;border-bottom:1px solid rgba(0,0,0,0.06);';
        parentElement.appendChild(topBar);

        var chapterCounter = document.createElement('span');
        chapterCounter.textContent = '01 / 07';
        chapterCounter.style.cssText = 'font-size:11px;font-weight:600;letter-spacing:0.12em;color:#94a3b8;text-transform:uppercase;min-width:60px;';
        topBar.appendChild(chapterCounter);

        var topDivider = document.createElement('div');
        topDivider.style.cssText = 'width:1px;height:16px;background:#e2e8f0;margin:0 16px;';
        topBar.appendChild(topDivider);

        var chapterTitle = document.createElement('span');
        chapterTitle.textContent = '';
        chapterTitle.style.cssText = 'font-size:14px;font-weight:600;color:#1e293b;flex:1;';
        topBar.appendChild(chapterTitle);

        var kpiStrip = document.createElement('span');
        kpiStrip.style.cssText = 'font-size:11px;color:#64748b;letter-spacing:0.02em;';
        kpiStrip.innerHTML = 'NPAT <b style="color:#1e3a5f">$10.98B</b> ▲7% &nbsp;|&nbsp; NIM <b style="color:#1e3a5f">2.05%</b> ▼3bps &nbsp;|&nbsp; CTI <b style="color:#16a34a">45.5%</b> ▼20bps &nbsp;|&nbsp; ROE <b style="color:#1e3a5f">14.0%</b> ▲50bps &nbsp;|&nbsp; CET1 <b style="color:#1e3a5f">12.0%</b>';
        topBar.appendChild(kpiStrip);

        // --- Chapter dots (right edge, vertical) ---
        var dotsWrap = document.createElement('div');
        dotsWrap.style.cssText = 'position:absolute;right:18px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:6px;z-index:10;';
        parentElement.appendChild(dotsWrap);
        var dotEls = [];
        CHAPTER_TITLES.forEach(function(title, i) {
            var dot = document.createElement('div');
            dot.title = title;
            dot.style.cssText = 'width:8px;height:8px;border-radius:50%;cursor:pointer;transition:all 0.3s ease;background:#cbd5e1;';
            dot.addEventListener('click', function() { goTo(i); });
            dotsWrap.appendChild(dot);
            dotEls.push(dot);
        });

        // --- Info card (bottom-left overlay) ---
        var infoCard = document.createElement('div');
        infoCard.style.cssText = 'position:absolute;bottom:72px;left:36px;width:340px;background:rgba(255,255,255,0.94);backdrop-filter:blur(16px);border-radius:14px;padding:20px 24px;box-shadow:0 8px 32px rgba(0,0,0,0.12);z-index:10;transition:opacity 0.35s ease,transform 0.45s cubic-bezier(0.34,1.2,0.64,1);opacity:0;transform:translateY(16px);pointer-events:none;';
        parentElement.appendChild(infoCard);

        var infoChapterNum = document.createElement('div');
        infoChapterNum.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:0.14em;color:#94a3b8;text-transform:uppercase;margin-bottom:6px;';
        infoCard.appendChild(infoChapterNum);

        var infoHeadline = document.createElement('div');
        infoHeadline.style.cssText = 'font-size:18px;font-weight:700;color:#0f172a;line-height:1.25;margin-bottom:8px;';
        infoCard.appendChild(infoHeadline);

        var infoBody = document.createElement('div');
        infoBody.style.cssText = 'font-size:13px;color:#475569;line-height:1.55;';
        infoCard.appendChild(infoBody);

        var infoKeyStat = document.createElement('div');
        infoKeyStat.className = 'info-key-stat';
        infoKeyStat.style.cssText = 'font-size:32px;color:#1e3a5f;font-family:Georgia,serif;font-weight:800;display:none;margin-top:10px;';
        infoCard.appendChild(infoKeyStat);

        var infoPullQuote = document.createElement('div');
        infoPullQuote.className = 'info-pull-quote';
        infoPullQuote.style.cssText = 'font-size:12px;font-style:italic;color:#1e3a5f;border-left:3px solid #2a78d6;padding:8px 12px;background:#f0f7ff;margin-top:8px;border-radius:0 6px 6px 0;display:none;';
        infoCard.appendChild(infoPullQuote);

        // --- Prev / Next arrows (bottom-right) ---
        var navRow = document.createElement('div');
        navRow.style.cssText = 'position:absolute;bottom:20px;right:36px;display:flex;gap:10px;z-index:10;';
        parentElement.appendChild(navRow);

        function makeArrowBtn(label, onclick) {
            var b = document.createElement('button');
            b.textContent = label;
            b.style.cssText = 'width:38px;height:38px;border-radius:50%;border:1.5px solid #cbd5e1;background:rgba(255,255,255,0.9);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:all 0.2s ease;color:#475569;';
            b.addEventListener('mouseenter', function() { b.style.background = '#1e3a5f'; b.style.color = '#fff'; b.style.borderColor = '#1e3a5f'; });
            b.addEventListener('mouseleave', function() { b.style.background = 'rgba(255,255,255,0.9)'; b.style.color = '#475569'; b.style.borderColor = '#cbd5e1'; });
            b.addEventListener('click', onclick);
            return b;
        }
        navRow.appendChild(makeArrowBtn('←', function() { goTo(currentChapter - 1); }));
        navRow.appendChild(makeArrowBtn('→', function() { goTo(currentChapter + 1); }));

        // --- Progress bar (very bottom) ---
        var progressTrack = document.createElement('div');
        progressTrack.style.cssText = 'position:absolute;bottom:0;left:0;right:0;height:3px;background:#e2e8f0;z-index:10;';
        parentElement.appendChild(progressTrack);
        var progressFill = document.createElement('div');
        progressFill.style.cssText = 'height:100%;background:linear-gradient(90deg,#2a78d6,#1baf7a);border-radius:0 2px 2px 0;transition:width 0.5s cubic-bezier(0.4,0,0.2,1);width:0%;';
        progressTrack.appendChild(progressFill);

        // =====================================================================
        // KPI GRID DOM (chapter 6)
        // =====================================================================

        // 5-year sparkline data (FY22 → FY26)
        var annual = data.annual || [];
        var SPARKLINE = {
            'Cash NPAT':        annual.map(function(y){return y.npat_m;}),
            'NIM':              annual.map(function(y){return y.nim_pct;}),
            'CTI':              annual.map(function(y){return y.cti_pct;}),
            'ROE':              annual.map(function(y){return y.roe_pct;}),
            'CET1 (APRA)':      annual.map(function(y){return y.cet1_pct;}),
            'EPS (cash)':       annual.map(function(y){return y.eps_cents;}),
            'DPS':              annual.map(function(y){return y.dps_cents;}),
            'LIE rate':         annual.map(function(y){return y.lie_m;}),
            'Pre-prov. profit': annual.map(function(y){return y.pre_prov_m;}),
        };

        function makeSparkline(values, accentColor) {
            var W = 200, H = 44, px = 2, py = 6, n = values.length;
            if (!values || n < 2) { var el = document.createElement('div'); return el; }
            var mn = Math.min.apply(null, values), mx = Math.max.apply(null, values);
            var rng = mx - mn || mx * 0.05 || 1;
            // Expand range slightly so line doesn't hug edges
            mn -= rng * 0.08; mx += rng * 0.08; rng = mx - mn;
            var pts = values.map(function(v, i) {
                return [px + (i / (n - 1)) * (W - 2 * px),
                        (H - py) - ((v - mn) / rng) * (H - 2 * py)];
            });
            // Smooth cubic bezier path
            function curvePath(pts) {
                var d = 'M' + pts[0][0] + ',' + pts[0][1];
                for (var i = 1; i < pts.length; i++) {
                    var cx = (pts[i-1][0] + pts[i][0]) / 2;
                    d += 'C' + cx + ',' + pts[i-1][1] + ',' + cx + ',' + pts[i][1] + ',' + pts[i][0] + ',' + pts[i][1];
                }
                return d;
            }
            var linePath = curvePath(pts);
            var areaPath = linePath + 'L' + pts[n-1][0] + ',' + H + 'L' + pts[0][0] + ',' + H + 'Z';
            var NS = 'http://www.w3.org/2000/svg';
            var svg = document.createElementNS(NS, 'svg');
            svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
            svg.setAttribute('preserveAspectRatio', 'none');
            svg.style.cssText = 'width:100%;height:44px;display:block;margin-top:8px;overflow:visible;';
            var area = document.createElementNS(NS, 'path');
            area.setAttribute('d', areaPath);
            area.setAttribute('fill', accentColor || '#1e3a5f');
            area.setAttribute('fill-opacity', '0.10');
            svg.appendChild(area);
            var line = document.createElementNS(NS, 'path');
            line.setAttribute('d', linePath);
            line.setAttribute('fill', 'none');
            line.setAttribute('stroke', accentColor || '#1e3a5f');
            line.setAttribute('stroke-width', '1.8');
            line.setAttribute('stroke-linecap', 'round');
            svg.appendChild(line);
            var dot = document.createElementNS(NS, 'circle');
            dot.setAttribute('cx', pts[n-1][0]); dot.setAttribute('cy', pts[n-1][1]);
            dot.setAttribute('r', '3'); dot.setAttribute('fill', accentColor || '#1e3a5f');
            svg.appendChild(dot);
            return svg;
        }

        kpiGrid = document.createElement('div');
        kpiGrid.style.cssText = 'position:absolute;top:48px;left:0;right:0;bottom:0;display:none;grid-template-columns:1fr 1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:14px;padding:32px 60px 60px 60px;box-sizing:border-box;background:#f8fafc;z-index:9;align-content:center;';
        parentElement.appendChild(kpiGrid);
        parentElement._kpiGrid = kpiGrid;

        kpiTileEls = [];
        FY26_KPI_TILES.forEach(function(spec) {
            var tile = document.createElement('div');
            tile.style.cssText = 'background:white;border-radius:12px;padding:18px 20px;border:1px solid #e2e8f0;box-shadow:0 2px 10px rgba(0,0,0,0.06);display:flex;flex-direction:column;gap:4px;';

            var lbl = document.createElement('div');
            lbl.textContent = spec.label;
            lbl.style.cssText = 'font-size:11px;font-weight:600;letter-spacing:0.07em;color:#64748b;text-transform:uppercase;';

            var valRow = document.createElement('div');
            valRow.style.cssText = 'display:flex;align-items:baseline;gap:8px;';

            var valEl = document.createElement('div');
            valEl.textContent = spec.value;
            valEl.style.cssText = 'font-size:1.55rem;font-weight:800;color:#0f172a;line-height:1.1;';

            var chgEl = document.createElement('div');
            chgEl.textContent = spec.change;
            var chgColor = spec.good ? '#16a34a' : '#dc2626';
            chgEl.style.cssText = 'font-size:0.78rem;font-weight:700;color:' + chgColor + ';';

            valRow.appendChild(valEl);
            valRow.appendChild(chgEl);

            var subEl = document.createElement('div');
            subEl.textContent = spec.sub;
            subEl.style.cssText = 'font-size:11px;color:#94a3b8;margin-top:2px;';

            tile.appendChild(lbl);
            tile.appendChild(valRow);
            tile.appendChild(subEl);

            var sparkVals = SPARKLINE[spec.label];
            if (sparkVals && sparkVals.length) {
                tile.appendChild(makeSparkline(sparkVals, spec.good ? '#1e3a5f' : '#dc2626'));
            }

            kpiGrid.appendChild(tile);
            kpiTileEls.push({ tile: tile, valEl: valEl, spec: spec });
        });

        var kpiFooter = document.createElement('div');
        kpiFooter.style.cssText = 'grid-column:1 / -1;font-size:10px;color:#94a3b8;text-align:center;align-self:end;';
        kpiFooter.textContent = 'Source: CBA Profit Announcement, year ended 30 June 2026. Chart data is illustrative.';
        kpiGrid.appendChild(kpiFooter);

        // =====================================================================
        // CHAPTER STATE MACHINE
        // =====================================================================
        function updateUI() {
            var pct = ((currentChapter + 1) / CHAPTER_TITLES.length * 100).toFixed(1);
            progressFill.style.width = pct + '%';
            chapterCounter.textContent = String(currentChapter + 1).padStart(2, '0') + ' / ' + String(CHAPTER_TITLES.length).padStart(2, '0');
            chapterTitle.textContent = CHAPTER_TITLES[currentChapter];
            dotEls.forEach(function(d, i) {
                d.style.background = i === currentChapter ? '#1e3a5f' : '#cbd5e1';
                d.style.transform  = i === currentChapter ? 'scale(1.4)' : 'scale(1)';
            });
            var info = CHAPTER_INFO[currentChapter];
            infoChapterNum.textContent = info.num + ' — ' + CHAPTER_TITLES[currentChapter];
            var cm = getCommentary(currentChapter);
            var fallback = CHAPTER_INFO[currentChapter] || {};
            infoHeadline.textContent = cm ? cm.headline : (fallback.headline || CHAPTER_TITLES[currentChapter]);
            infoBody.textContent     = cm ? cm.body     : (fallback.body || '');
            if (cm && cm.key_stat) {
                infoKeyStat.textContent  = cm.key_stat;
                infoKeyStat.style.display = 'block';
            } else {
                infoKeyStat.style.display = 'none';
            }
            if (cm && cm.pull_quote) {
                infoPullQuote.textContent  = cm.pull_quote;
                infoPullQuote.style.display = 'block';
            } else {
                infoPullQuote.style.display = 'none';
            }
            // Spring-in the info card
            infoCard.style.opacity          = '0';
            infoCard.style.transform        = 'translateY(16px)';
            infoCard.style.pointerEvents    = 'none';
            setTimeout(function() {
                infoCard.style.opacity       = '1';
                infoCard.style.transform     = 'translateY(0)';
                infoCard.style.pointerEvents = 'auto';
            }, 350);
        }

        function goTo(idx) {
            if (idx < 0 || idx >= CHAPTER_TITLES.length) return;
            if (isTransitioning) return;
            isTransitioning = true;
            var prev = currentChapter;
            currentChapter = idx;
            // Crossfade: blur-out SVG, swap, blur-in
            d3.select(svgEl).transition().duration(180).ease(d3.easeQuadOut)
                .style('filter', 'blur(5px) opacity(0.6)')
                .on('end', function() {
                    deactivateStep(prev);
                    activateStep(currentChapter);
                    updateUI();
                    d3.select(svgEl).transition().duration(320).ease(d3.easeQuadOut)
                        .style('filter', 'blur(0px) opacity(1)')
                        .on('end', function() { isTransitioning = false; });
                });
        }

        // --- Keyboard navigation ---
        var keydownHandler = function(e) {
            if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); goTo(currentChapter + 1); }
            if (e.key === 'ArrowLeft')                   { e.preventDefault(); goTo(currentChapter - 1); }
        };
        document.addEventListener('keydown', keydownHandler);
        parentElement._keydownHandler = keydownHandler;

        // --- Touch/swipe ---
        var touchStartX = 0;
        parentElement.addEventListener('touchstart', function(e) { touchStartX = e.touches[0].clientX; }, { passive: true });
        parentElement.addEventListener('touchend', function(e) {
            var dx = e.changedTouches[0].clientX - touchStartX;
            if (Math.abs(dx) > 50) goTo(currentChapter + (dx < 0 ? 1 : -1));
        }, { passive: true });

        // --- Wheel/trackpad navigation ---
        var wheelAccum = 0, wheelTimer = null;
        parentElement.addEventListener('wheel', function(e) {
            e.preventDefault();
            wheelAccum += e.deltaY;
            clearTimeout(wheelTimer);
            wheelTimer = setTimeout(function() {
                if (Math.abs(wheelAccum) > 40) goTo(currentChapter + (wheelAccum > 0 ? 1 : -1));
                wheelAccum = 0;
            }, 80);
        }, {passive: false});

        // --- Click on bare SVG/background advances ---
        parentElement.addEventListener('click', function(e) {
            if (e.target === parentElement || e.target === svgEl || e.target.tagName === 'svg') {
                goTo(currentChapter + 1);
            }
        });

        // =====================================================================
        // D3 SCALES + AXES
        // =====================================================================
        var parseDate = d3.timeParse('%Y-%m-%d');

        var parsedMonthly = monthly.map(function(d) {
            return Object.assign({}, d, { _date: parseDate(d.date) });
        }).filter(function(d) { return d._date; });

        var parsedStock = stock.map(function(d) {
            return { _date: parseDate(d.date), value: +d.value };
        }).filter(function(d) { return d._date; });

        // Unified X domain
        var allDates = parsedMonthly.map(function(d) { return d._date; })
            .concat(parsedStock.map(function(d) { return d._date; }));
        var xScale = d3.scaleTime()
            .domain(d3.extent(allDates))
            .range([margin.left, W - margin.right]);

        // Y scales
        var maxIncome = d3.max(parsedMonthly, function(d) { return +d.operating_income; }) || 1;
        var yScaleIncome = d3.scaleLinear()
            .domain([0, maxIncome * 1.12])
            .range([viewH - margin.bottom, margin.top]);

        var maxSegVal = d3.max(segments, function(seg) {
            return d3.max(parsedMonthly, function(d) { return +d[seg] || 0; });
        }) || maxIncome * 0.5;
        var yScaleSegs = d3.scaleLinear()
            .domain([0, maxSegVal * 1.18])
            .range([viewH - margin.bottom, margin.top]);

        var maxStock = d3.max(parsedStock, function(d) { return d.value; }) || 1;
        var minStock = d3.min(parsedStock, function(d) { return d.value; }) || 0;
        var yScaleStock = d3.scaleLinear()
            .domain([minStock * 0.95, maxStock * 1.05])
            .range([viewH - margin.bottom, margin.top]);

        var _lastYScale = yScaleIncome;

        var g = svg.append('g');

        // ---- Gridlines
        var gridG = g.append('g').attr('class', 'grid');
        function drawGridlines(yScale) {
            var ticks = yScale.ticks(6);
            gridG.selectAll('line').data(ticks).join('line')
                .attr('x1', margin.left)
                .attr('x2', W - margin.right)
                .attr('y1', function(d) { return yScale(d); })
                .attr('y2', function(d) { return yScale(d); })
                .attr('stroke', '#e2e8f0')
                .attr('stroke-opacity', 0.4)
                .attr('stroke-dasharray', '4,3')
                .attr('stroke-width', 1);
        }
        drawGridlines(yScaleIncome);

        // ---- X axis
        var xAxisG = g.append('g')
            .attr('transform', 'translate(0,' + (viewH - margin.bottom) + ')')
            .call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
        xAxisG.select('.domain').remove();
        xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
        xAxisG.selectAll('line').attr('stroke', '#e2e8f0');

        // ---- Y axis
        var incFmt = function(d) {
            return 'A$' + d3.format('.2s')(d).replace('G', 'B').replace('M', 'M');
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
                : function(d) { return 'A$' + d3.format('.2s')(d).replace('G', 'B'); };
            yAxisG.interrupt().transition().duration(600).ease(d3.easeCubicInOut)
                .call(d3.axisLeft(yScale).ticks(6).tickFormat(fmt).tickSizeOuter(0))
                .on('end', function() {
                    yAxisG.select('.domain').remove();
                    yAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                    yAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                });
        }

        // =====================================================================
        // CHAPTER 0: Group OI area + line (navy) + RBA annotations
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
        requestAnimationFrame(function() {
            try { totalLineLen = totalLinePath.node().getTotalLength(); } catch(e) {}
            totalLinePath
                .attr('stroke-dasharray', totalLineLen + ' ' + totalLineLen)
                .attr('stroke-dashoffset', totalLineLen);
        });
        var totalLineAnimated = false;

        // ---- Annotation group (fades in AFTER line draw)
        annotG = g.append('g').attr('opacity', 0).attr('class', 'annot-group');

        // COVID era shading region
        var covidStart = parseDate('2020-01-01'), covidEnd = parseDate('2022-05-01');
        if (covidStart && covidEnd) {
            var cx0 = xScale(covidStart), cx1 = xScale(covidEnd);
            annotG.append('rect')
                .attr('x', cx0).attr('y', margin.top)
                .attr('width', Math.max(0, cx1 - cx0))
                .attr('height', viewH - margin.top - margin.bottom)
                .attr('fill', 'rgba(59,130,246,0.07)')
                .attr('pointer-events', 'none');
            annotG.append('text')
                .attr('x', cx0 + 4).attr('y', margin.top + 26)
                .attr('font-size', '8px').attr('font-weight', '600')
                .attr('fill', 'rgba(59,130,246,0.55)')
                .text('COVID-19 era');
        }

        var ANNOTS = [
            { date: '2022-02-24', label: 'Russia-Ukraine war', color: '#f59e0b', sw: 1.2 },
            { date: '2022-05-01', label: 'Rate hiking begins',  color: '#1e3a5f', sw: 1 },
            { date: '2023-03-10', label: 'SVB collapse',        color: '#7c3aed', sw: 1.2 },
            { date: '2023-11-01', label: 'Peak 4.35%',          color: '#ef4444', sw: 1 },
            { date: '2025-02-01', label: 'RBA ↓ easing',        color: '#16a34a', sw: 1 },
        ];
        ANNOTS.forEach(function(ann) {
            var ad = parseDate(ann.date);
            if (!ad) return;
            var ax  = xScale(ad);
            var top = margin.top;
            var bot = viewH - margin.bottom;
            annotG.append('line')
                .attr('x1', ax).attr('x2', ax)
                .attr('y1', top).attr('y2', bot)
                .attr('stroke', ann.color)
                .attr('stroke-width', ann.sw || 1)
                .attr('stroke-dasharray', '4 4');
            annotG.append('text')
                .attr('x', ax + 3).attr('y', top + 14)
                .attr('font-size', '9px').attr('font-weight', '600')
                .attr('fill', ann.color)
                .text(ann.label);
        });
        // Endpoint label
        var lastMonthly = parsedMonthly.length ? parsedMonthly[parsedMonthly.length - 1] : null;
        if (lastMonthly) {
            var epx = xScale(lastMonthly._date);
            var epy = yScaleIncome(+lastMonthly.operating_income);
            annotG.append('circle').attr('cx', epx).attr('cy', epy).attr('r', 4).attr('fill', '#1e3a5f');
            annotG.append('text')
                .attr('x', epx + 8).attr('y', epy).attr('dy', '0.35em')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', '#1e3a5f')
                .text('FY26: A$30.2B ▲6%');
        }

        // =====================================================================
        // CHAPTER 1: Divisional TREEMAP
        // =====================================================================
        var totalBySeg = {};
        segments.forEach(function(seg) { totalBySeg[seg] = 0; });
        parsedMonthly.forEach(function(d) {
            segments.forEach(function(seg) { totalBySeg[seg] += (+d[seg] || 0); });
        });
        var totalAll = segments.reduce(function(s, seg) { return s + totalBySeg[seg]; }, 0) || 1;

        var treemapG = g.append('g')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
            .attr('opacity', 0);
        var treemapBuilt = false;

        function buildTreemap() {
            var iW = W - margin.left - margin.right;
            var iH = viewH - margin.top - margin.bottom;
            treemapG.selectAll('*').remove();

            var rootData = {
                name: 'Group',
                children: segments.map(function(seg) {
                    return { name: seg, value: totalBySeg[seg], npat: REAL_DIV_NPAT[seg] || 0, short: SEG_SHORT[seg] || seg };
                })
            };
            var hierarchy = d3.hierarchy(rootData)
                .sum(function(d) { return d.value || 0; })
                .sort(function(a, b) { return b.value - a.value; });

            var treemapLayout = d3.treemap().size([iW, iH]).padding(3).round(true);
            treemapLayout(hierarchy);
            var leaves = hierarchy.leaves();

            // Rects animate from full-size to final positions
            var rects = treemapG.selectAll('rect.tm-rect').data(leaves).enter()
                .append('rect').attr('class', 'tm-rect')
                .attr('x', 0).attr('y', 0).attr('width', iW).attr('height', iH)
                .attr('fill', function(d) { return SEG_COLORS[d.data.name] || '#888'; })
                .attr('stroke', 'white').attr('stroke-width', 2).attr('rx', 4).attr('opacity', 0);

            rects.interrupt()
                .transition().duration(200).ease(d3.easeQuadIn)
                .delay(function(d, i) { return i * 80; })
                .attr('opacity', 1)
                .transition().duration(600).ease(d3.easeCubicInOut)
                .attr('x', function(d) { return d.x0; })
                .attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return Math.max(0, d.x1 - d.x0); })
                .attr('height', function(d) { return Math.max(0, d.y1 - d.y0); });

            var labelGs = treemapG.selectAll('g.tm-label').data(leaves).enter()
                .append('g').attr('class', 'tm-label').attr('opacity', 0).attr('pointer-events', 'none');

            labelGs.each(function(d) {
                var w = d.x1 - d.x0, h = d.y1 - d.y0;
                if (w < 80) return;
                var cx = d.x0 + w / 2, cy = d.y0 + h / 2;
                var pct = (d.data.value / totalAll * 100).toFixed(1) + '%';
                var incomeVal = d.data.value;
                var incomeStr = incomeVal > 1e9 ? 'A$' + (incomeVal / 1e9).toFixed(1) + 'B' : 'A$' + d3.format('.3s')(incomeVal).replace('G', 'B');
                var npat = d.data.npat ? '$' + (d.data.npat / 1000).toFixed(2) + 'B NPAT' : '';

                d3.select(this).append('text')
                    .attr('x', cx).attr('y', cy - 14).attr('text-anchor', 'middle')
                    .attr('font-size', Math.min(13, w / 5) + 'px').attr('font-weight', '700').attr('fill', 'white')
                    .text(d.data.short);
                d3.select(this).append('text')
                    .attr('x', cx).attr('y', cy + 2).attr('text-anchor', 'middle')
                    .attr('font-size', Math.min(11, w / 6) + 'px').attr('font-weight', '400').attr('fill', 'rgba(255,255,255,0.9)')
                    .text(incomeStr + ' · ' + pct);
                if (h > 60 && npat) {
                    d3.select(this).append('text')
                        .attr('x', cx).attr('y', cy + 16).attr('text-anchor', 'middle')
                        .attr('font-size', Math.min(10, w / 7) + 'px').attr('font-weight', '400').attr('fill', 'rgba(255,255,255,0.75)')
                        .text(npat);
                }
            });
            labelGs.transition().delay(850).duration(400).attr('opacity', 1);
            treemapBuilt = true;
        }

        // =====================================================================
        // CHAPTER 2: STREAM GRAPH — five-year revenue flow
        // =====================================================================
        var STACK_KEYS = segments.map(function(s) { return SEG_KEY[s]; });
        var stackInput = parsedMonthly.map(function(d) {
            var row = { _date: d._date, date: d.date };
            segments.forEach(function(seg) { row[SEG_KEY[seg]] = +d[seg] || 0; });
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
            .range([viewH - margin.bottom, margin.top]);

        var streamAreaGen = d3.area()
            .x(function(d) { return xScale(d.data._date); })
            .y0(function(d) { return yScaleStream(d[0]); })
            .y1(function(d) { return yScaleStream(d[1]); })
            .curve(d3.curveMonotoneX);

        var streamPaths = {}, streamLabelBgs = {}, streamLabelEls = {};
        segments.forEach(function(seg, si) {
            var col = SEG_COLORS[seg] || '#888';
            var p = g.append('path')
                .datum(streamSeries[si])
                .attr('fill', col).attr('fill-opacity', 0.82).attr('stroke', 'none')
                .attr('d', streamAreaGen).attr('opacity', 0)
                .attr('class', 'stream-path').attr('data-seg', seg);
            streamPaths[seg] = p;

            var bg  = g.append('rect').attr('rx', 3).attr('fill', 'white').attr('fill-opacity', 0.8).attr('opacity', 0);
            var lbl = g.append('text')
                .attr('font-size', '11px').attr('font-weight', '700').attr('fill', col).attr('opacity', 0)
                .text(SEG_SHORT[seg] || seg);
            streamLabelEls[seg] = lbl;
            streamLabelBgs[seg] = bg;
        });

        function updateStreamLabels(opacity) {
            var lastIdx = stackInput.length - 1;
            if (lastIdx < 0) return;
            var lx = xScale(stackInput[lastIdx]._date) + 5;
            segments.forEach(function(seg, si) {
                var band = streamSeries[si][lastIdx];
                var cy = (yScaleStream(band[0]) + yScaleStream(band[1])) / 2;
                var lbl = streamLabelEls[seg], bg = streamLabelBgs[seg];
                lbl.attr('x', lx).attr('y', cy).attr('dy', '0.35em').attr('opacity', opacity);
                try {
                    var bb = lbl.node().getBBox();
                    bg.attr('x', bb.x - 2).attr('y', bb.y - 1).attr('width', bb.width + 4).attr('height', bb.height + 2).attr('opacity', opacity * 0.85);
                } catch(e) { bg.attr('opacity', 0); }
            });
        }

        // =====================================================================
        // CHAPTER 3: DIVISION SELECTION CARDS (DOM overlay)
        // =====================================================================
        SEG_CARDS_DIV = document.createElement('div');
        SEG_CARDS_DIV.style.cssText = 'position:absolute;left:' + margin.left + 'px;top:' + margin.top + 'px;width:' + (W - margin.left - margin.right) + 'px;height:' + (viewH - margin.top - margin.bottom) + 'px;display:none;align-items:center;justify-content:center;z-index:8;';
        parentElement.appendChild(SEG_CARDS_DIV);

        // 2x2 grid wrapper
        var cardsGrid = document.createElement('div');
        cardsGrid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:16px;width:600px;max-width:90%;';
        SEG_CARDS_DIV.appendChild(cardsGrid);

        var divCardEls = {};
        segments.forEach(function(seg, i) {
            var col = SEG_COLORS[seg] || '#888';
            var tint = SEG_TINTS[seg] || '#eee';
            var nim  = REAL_DIV_NIM[seg]  != null ? REAL_DIV_NIM[seg].toFixed(2)  + '%'  : '—';
            var cti  = REAL_DIV_CTI[seg]  != null ? REAL_DIV_CTI[seg].toFixed(1)  + '%'  : '—';
            var npat = REAL_DIV_NPAT[seg] != null ? '$' + (REAL_DIV_NPAT[seg] / 1000).toFixed(2) + 'B' : '—';

            var card = document.createElement('div');
            card.style.cssText = 'background:white;border-radius:12px;padding:20px 24px;border:2px solid #e2e8f0;cursor:pointer;transition:all 0.25s ease;box-shadow:0 2px 8px rgba(0,0,0,0.06);transform:scale(0.85);opacity:0;';
            card.innerHTML = '<div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:6px;">' + (SEG_SHORT[seg] || seg) + '</div>'
                           + '<div style="font-size:22px;font-weight:800;color:' + col + ';margin-bottom:8px;">' + npat + '</div>'
                           + '<div style="font-size:11px;color:#64748b;">NIM <b style="color:#334155">' + nim + '</b> &nbsp;|&nbsp; CTI <b style="color:#334155">' + cti + '</b></div>';

            card.addEventListener('mouseenter', function() {
                if (selectedSeg !== seg) {
                    card.style.borderColor = col + '88';
                    card.style.boxShadow   = '0 4px 16px rgba(0,0,0,0.10)';
                }
            });
            card.addEventListener('mouseleave', function() {
                if (selectedSeg !== seg) {
                    card.style.borderColor = '#e2e8f0';
                    card.style.boxShadow   = '0 2px 8px rgba(0,0,0,0.06)';
                }
            });
            card.addEventListener('click', function(e) {
                e.stopPropagation();
                selectedSeg = seg;
                parentElement._selectedSeg = seg;
                updateDivCardStates();
                // Highlight background stream
                segments.forEach(function(s) {
                    streamPaths[s].interrupt()
                        .transition().duration(300)
                        .attr('opacity', s === seg ? 0.85 : 0.12)
                        .attr('stroke', s === seg ? '#000' : 'none')
                        .attr('stroke-width', s === seg ? 1 : 0);
                });
            });
            cardsGrid.appendChild(card);
            divCardEls[seg] = card;

            // Staggered scale-in animation (triggered when chapter 3 activates)
            card._animDelay = i * 60;
        });

        function updateDivCardStates() {
            segments.forEach(function(seg) {
                var card = divCardEls[seg];
                if (!card) return;
                var col = SEG_COLORS[seg] || '#888';
                if (seg === selectedSeg) {
                    card.style.borderColor  = col;
                    card.style.background   = col + '12';
                    card.style.boxShadow    = '0 4px 20px ' + col + '44';
                } else {
                    card.style.borderColor  = '#e2e8f0';
                    card.style.background   = 'white';
                    card.style.boxShadow    = '0 2px 8px rgba(0,0,0,0.06)';
                }
            });
        }

        function showSegCards() {
            SEG_CARDS_DIV.style.display = 'flex';
            updateDivCardStates();
            segments.forEach(function(seg) {
                var card = divCardEls[seg];
                if (!card) return;
                card.style.transform = 'scale(0.85)';
                card.style.opacity   = '0';
                card.style.transition = 'none';
                setTimeout(function() {
                    card.style.transition = 'transform 0.4s cubic-bezier(0.34,1.2,0.64,1), opacity 0.35s ease, border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease';
                    card.style.transform  = 'scale(1)';
                    card.style.opacity    = '1';
                }, card._animDelay || 0);
            });
        }

        function hideSegCards() {
            SEG_CARDS_DIV.style.display = 'none';
        }

        // =====================================================================
        // CHAPTER 4: SANKEY P&L DIAGRAM
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
            return { totalNii: totalNii, totalOther: totalOther, opexLink: opexLink, lieLink: lieLink, totalRev: totalRev, preProvision: preProvision, npat: npat };
        }

        function formatSankeyValue(v) {
            return 'A$' + d3.format('.3s')(v).replace('G', 'B');
        }

        function drawSankey() {
            if (!window.d3sankey) return;
            var dsk = window.d3sankey;
            var iW  = W - margin.left - margin.right;
            var iH  = viewH - margin.top - margin.bottom;
            var seg    = selectedSeg;
            var segCol = SEG_COLORS[seg] || '#2a78d6';
            var sd = computeSankeyData(seg);
            var divNim  = REAL_DIV_NIM[seg];
            var divCti  = REAL_DIV_CTI[seg];
            var divNpat = REAL_DIV_NPAT[seg];
            var divNimStr = divNim != null ? 'NIM ' + divNim.toFixed(2) + '%' : '';

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

            var nodes = graph.nodes, links = graph.links;

            function nodeColor(i) {
                if (i === 0 || i === 1) return '#0d9488';
                if (i === 2) return segCol;
                if (i === 3 || i === 5) return '#dc2626';
                return '#16a34a';
            }
            function linkColor(link) {
                var ti = link.target.index !== undefined ? link.target.index : link.target;
                if (ti === 3 || ti === 5) return 'rgba(220,38,38,0.32)';
                return d3.color(segCol) ? d3.color(segCol).copy({ opacity: 0.38 }).formatRgb() : segCol + '66';
            }

            var linkPath = dsk.sankeyLinkHorizontal();

            // Links: draw-on with stroke-dasharray trick would be complex; fade in staggered
            var linkEls = sankeyG.append('g').attr('class', 'sankey-links')
                .selectAll('path').data(links).enter().append('path')
                .attr('d', linkPath)
                .attr('stroke', function(d) { return linkColor(d); })
                .attr('stroke-width', function(d) { return Math.max(1, d.width); })
                .attr('fill', 'none').attr('opacity', 0);

            linkEls.interrupt()
                .transition().duration(500)
                .delay(function(d, i) { return i * 100; })
                .ease(d3.easeCubicInOut)
                .attr('opacity', 1);

            // Nodes: left→right staggered
            var nodeEls = sankeyG.append('g').attr('class', 'sankey-nodes')
                .selectAll('rect').data(nodes).enter().append('rect')
                .attr('x', function(d) { return d.x0; })
                .attr('y', function(d) { return d.y0; })
                .attr('width', function(d) { return d.x1 - d.x0; })
                .attr('height', function(d) { return Math.max(1, d.y1 - d.y0); })
                .attr('fill', function(d, i) { return nodeColor(i); })
                .attr('rx', 3).attr('opacity', 0);

            nodeEls.interrupt()
                .transition().duration(400)
                .delay(function(d, i) { return i * 80; })
                .ease(d3.easeBackOut.overshoot(1.2))
                .attr('opacity', 1);

            var nodeLabelG = sankeyG.append('g').attr('class', 'sankey-node-labels');
            nodes.forEach(function(d, i) {
                var isRight = d.x0 > iW / 2;
                var lx = isRight ? d.x1 + 6 : d.x0 - 6;
                var ly = (d.y0 + d.y1) / 2;
                var anchor = isRight ? 'start' : 'end';

                nodeLabelG.append('text')
                    .attr('x', lx).attr('y', ly - 8).attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle').attr('font-size', '10px').attr('font-weight', '700')
                    .attr('fill', '#334155').attr('opacity', 0)
                    .text(d.name)
                    .transition().delay(600).duration(400).attr('opacity', 1);

                nodeLabelG.append('text')
                    .attr('x', lx).attr('y', ly + 5).attr('text-anchor', anchor)
                    .attr('dominant-baseline', 'middle').attr('font-size', '9px').attr('font-weight', '400')
                    .attr('fill', '#64748b').attr('opacity', 0)
                    .text(formatSankeyValue(d.value || 0))
                    .transition().delay(700).duration(400).attr('opacity', 1);

                if (i === 0 && divNimStr) {
                    nodeLabelG.append('text')
                        .attr('x', lx).attr('y', ly + 17).attr('text-anchor', anchor)
                        .attr('font-size', '8px').attr('font-weight', '600').attr('fill', '#0d9488').attr('opacity', 0)
                        .text(divNimStr)
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
                if (i === 6 && divNpat != null) {
                    nodeLabelG.append('text')
                        .attr('x', lx).attr('y', ly + 17).attr('text-anchor', anchor)
                        .attr('font-size', '8px').attr('font-weight', '600').attr('fill', '#16a34a').attr('opacity', 0)
                        .text('FY26 NPAT: $' + (divNpat / 1000).toFixed(3) + 'B')
                        .transition().delay(800).duration(400).attr('opacity', 1);
                }
            });

            // CTI annotation on OpEx node
            if (divCti != null) {
                var opexNode = nodes[3];
                if (opexNode) {
                    var ctiX = (opexNode.x0 + opexNode.x1) / 2;
                    var ctiY = opexNode.y0 - 6;
                    sankeyG.append('text')
                        .attr('x', ctiX).attr('y', ctiY).attr('text-anchor', 'middle')
                        .attr('font-size', '8px').attr('font-weight', '700').attr('fill', '#dc2626').attr('opacity', 0)
                        .text('CTI ' + divCti.toFixed(1) + '%')
                        .transition().delay(900).duration(400).attr('opacity', 1);
                }
            }
        }

        // =====================================================================
        // CHAPTER 5: Stock price area + line + 20-week MA
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
            .attr('fill', 'none').attr('stroke', '#0F4C81').attr('stroke-width', 2)
            .attr('d', stockLineGen).attr('opacity', 0);

        var stockLineLen = 0;
        requestAnimationFrame(function() {
            try { stockLineLen = stockLinePath.node().getTotalLength(); } catch(e) {}
            stockLinePath
                .attr('stroke-dasharray', stockLineLen + ' ' + stockLineLen)
                .attr('stroke-dashoffset', stockLineLen);
        });
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
            ? parsedStock.reduce(function(a, b) { return b.value > a.value ? b : a; })
            : null;
        var peakAnnotG = g.append('g').attr('opacity', 0);
        if (peakRow) {
            var px = xScale(peakRow._date), py = yScaleStock(peakRow.value);
            peakAnnotG.append('line')
                .attr('x1', px).attr('x2', px).attr('y1', py).attr('y2', py + 30)
                .attr('stroke', '#0F4C81').attr('stroke-width', 1).attr('stroke-dasharray', '3,2');
            peakAnnotG.append('text')
                .attr('x', px).attr('y', py - 6).attr('text-anchor', 'middle')
                .attr('font-size', '9px').attr('font-weight', '700').attr('fill', '#0F4C81')
                .text('FY24 peak');
        }

        // =====================================================================
        // DEACTIVATE STEP — interrupt all, clean up overlays
        // =====================================================================
        function deactivateStep(idx) {
            svg.selectAll('*').interrupt();
            if (annotG) annotG.attr('opacity', 0);
            hideSegCards();
            svg.style('opacity', '1');
            if (kpiGrid) kpiGrid.style.display = 'none';
        }

        // =====================================================================
        // ACTIVATE STEP — per-chapter animation sequences
        // =====================================================================

        function activateStep(idx) {
            var t = d3.transition().duration(400).ease(d3.easeCubicInOut);

            // Helper: hide all SVG chart elements quickly
            function hideAllSVG(dur) {
                var d = dur || 300;
                totalAreaPath.interrupt().transition().duration(d).attr('opacity', 0);
                totalLinePath.interrupt().transition().duration(d).attr('opacity', 0);
                if (annotG) annotG.interrupt().transition().duration(d).attr('opacity', 0);
                treemapG.interrupt().transition().duration(d).attr('opacity', 0);
                segments.forEach(function(seg) {
                    streamPaths[seg].interrupt().transition().duration(d).attr('opacity', 0);
                    streamLabelEls[seg].interrupt().transition().duration(d).attr('opacity', 0);
                    streamLabelBgs[seg].interrupt().transition().duration(d).attr('opacity', 0);
                });
                sankeyG.interrupt().transition().duration(d).attr('opacity', 0);
                stockAreaPath.interrupt().transition().duration(d).attr('opacity', 0);
                stockLinePath.interrupt().transition().duration(d).attr('opacity', 0);
                maLine.interrupt().transition().duration(d).attr('opacity', 0);
                if (maLabelEl) maLabelEl.interrupt().transition().duration(d).attr('opacity', 0);
                peakAnnotG.interrupt().transition().duration(d).attr('opacity', 0);
            }

            // --- Chapter 0: Group OI area + line + annotations ---
            if (idx === 0) {
                hideAllSVG(250);
                hideSegCards();
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');
                totalLineAnimated = false;
                stockAnimated = false;

                styleYAxis(yScaleIncome, false);
                drawGridlines(yScaleIncome);
                xAxisG.interrupt().transition(t).attr('opacity', 1);
                yAxisG.interrupt().transition(t).attr('opacity', 1);
                gridG.interrupt().transition(t).attr('opacity', 1);

                totalAreaPath.interrupt().transition().duration(800).ease(d3.easeCubicInOut).attr('opacity', 1);
                if (!totalLineAnimated) {
                    totalLineAnimated = true;
                    totalLinePath.interrupt()
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', totalLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            if (annotG) annotG.interrupt().transition().duration(500).ease(d3.easeQuadOut).attr('opacity', 1);
                        });
                } else {
                    totalLinePath.interrupt().transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            if (annotG) annotG.interrupt().transition().duration(400).ease(d3.easeQuadOut).attr('opacity', 1);
                        });
                }

            // --- Chapter 1: Treemap ---
            } else if (idx === 1) {
                hideAllSVG(250);
                hideSegCards();
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.interrupt().transition(t).attr('opacity', 0);
                yAxisG.interrupt().transition(t).attr('opacity', 0);
                gridG.interrupt().transition(t).attr('opacity', 0);

                treemapG.interrupt().attr('opacity', 1);
                if (!treemapBuilt) { buildTreemap(); }
                else {
                    // Re-animate labels
                    treemapG.selectAll('g.tm-label').interrupt()
                        .attr('opacity', 0)
                        .transition().delay(300).duration(400).attr('opacity', 1);
                }

            // --- Chapter 2: Stream graph ---
            } else if (idx === 2) {
                hideAllSVG(250);
                hideSegCards();
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                xAxisG.interrupt().transition(t).attr('opacity', 1);
                yAxisG.interrupt().transition(t).attr('opacity', 0);
                gridG.interrupt().transition(t).attr('opacity', 0);

                segments.forEach(function(seg, si) {
                    streamPaths[seg].interrupt()
                        .transition().delay(si * 100).duration(700).ease(d3.easeCubicInOut)
                        .attr('opacity', 0.82);
                });
                // Labels fade in AFTER main paths finish (RULE 5)
                setTimeout(function() {
                    if (currentChapter === 2) { updateStreamLabels(1); }
                }, 900);

            // --- Chapter 3: Division selection cards + stream background ---
            } else if (idx === 3) {
                hideAllSVG(200);
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');

                // Show stream graph at low opacity as background context
                xAxisG.interrupt().transition(t).attr('opacity', 0.4);
                yAxisG.interrupt().transition(t).attr('opacity', 0);
                gridG.interrupt().transition(t).attr('opacity', 0);

                segments.forEach(function(seg) {
                    var isSel = seg === selectedSeg;
                    streamPaths[seg].interrupt()
                        .transition().duration(400).ease(d3.easeCubicInOut)
                        .attr('opacity', isSel ? 0.85 : 0.12)
                        .attr('stroke', isSel ? '#000' : 'none')
                        .attr('stroke-width', isSel ? 1 : 0);
                });

                // Show division selection cards with staggered animation
                showSegCards();

                // SVG pointer-events: allow for this step (stream is background only)
                svgEl.style.pointerEvents = 'none';

            // --- Chapter 4: Sankey P&L ---
            } else if (idx === 4) {
                hideAllSVG(250);
                hideSegCards();
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');
                svgEl.style.pointerEvents = 'none';

                xAxisG.interrupt().transition(t).attr('opacity', 0);
                yAxisG.interrupt().transition(t).attr('opacity', 0);
                gridG.interrupt().transition(t).attr('opacity', 0);

                sankeyG.selectAll('*').remove();
                sankeyG.interrupt().attr('opacity', 0);

                function doDrawSankey() {
                    drawSankey();
                    sankeyG.interrupt().transition().duration(300).ease(d3.easeQuadOut).attr('opacity', 1);
                }
                if (window.d3sankey) {
                    doDrawSankey();
                } else {
                    loadD3Sankey().then(doDrawSankey).catch(function() {
                        chapterTitle.textContent = 'Sankey chart failed to load';
                    });
                }

            // --- Chapter 5: Stock price + 20-week MA ---
            } else if (idx === 5) {
                hideAllSVG(250);
                hideSegCards();
                if (kpiGrid) kpiGrid.style.display = 'none';
                svg.style('opacity', '1');
                svgEl.style.pointerEvents = 'none';

                styleYAxis(yScaleStock, true);
                drawGridlines(yScaleStock);
                xAxisG.interrupt().transition(t).attr('opacity', 1);
                yAxisG.interrupt().transition(t).attr('opacity', 1);
                gridG.interrupt().transition(t).attr('opacity', 1);

                stockAreaPath.interrupt().transition(t).attr('opacity', 1);

                if (!stockAnimated) {
                    stockAnimated = true;
                    stockLinePath.interrupt()
                        .attr('opacity', 1)
                        .attr('stroke-dashoffset', stockLineLen)
                        .transition().duration(1100).ease(d3.easeCubicOut)
                        .attr('stroke-dashoffset', 0)
                        .on('end', function() {
                            // Annotations AFTER main line (RULE 5)
                            peakAnnotG.interrupt().transition().duration(400).ease(d3.easeQuadOut).attr('opacity', 1);
                            maLine.interrupt().transition().duration(600).ease(d3.easeCubicInOut).attr('opacity', 0.9);
                            if (maLabelEl) maLabelEl.interrupt().transition().delay(400).duration(400).ease(d3.easeQuadOut).attr('opacity', 1);
                        });
                } else {
                    stockLinePath.interrupt().transition(t).attr('opacity', 1).attr('stroke-dashoffset', 0);
                    peakAnnotG.interrupt().transition(t).attr('opacity', 1);
                    maLine.interrupt().transition(t).attr('opacity', 0.9);
                    if (maLabelEl) maLabelEl.interrupt().transition(t).attr('opacity', 1);
                }

            // --- Chapter 6: KPI Grid ---
            } else if (idx === 6) {
                hideAllSVG(250);
                hideSegCards();
                svgEl.style.pointerEvents = 'none';

                xAxisG.interrupt().transition(t).attr('opacity', 0);
                yAxisG.interrupt().transition(t).attr('opacity', 0);
                gridG.interrupt().transition(t).attr('opacity', 0);

                // Hide SVG, show KPI grid
                svg.interrupt().style('opacity', '0');
                kpiGrid.style.display = 'grid';

                // Staggered tile pop-in with count-up tweens
                kpiTileEls.forEach(function(item, ci) {
                    var tile = item.tile;
                    tile.style.transform  = 'translateY(14px)';
                    tile.style.opacity    = '0';
                    tile.style.transition = 'none';
                    setTimeout(function() {
                        tile.style.transition = 'transform 0.45s cubic-bezier(0.34,1.2,0.64,1), opacity 0.4s ease';
                        tile.style.transform  = 'translateY(0)';
                        tile.style.opacity    = '1';
                    }, ci * 70);
                });
            }
        }

        // =====================================================================
        // RESIZE OBSERVER
        // =====================================================================
        if (window.ResizeObserver) {
            var ro = new ResizeObserver(function() {
                var newW = Math.max(900, parentElement.offsetWidth || 1440);
                xScale.range([margin.left, newW - margin.right]);
                xAxisG.interrupt().call(d3.axisBottom(xScale).ticks(6).tickSizeOuter(0));
                xAxisG.select('.domain').remove();
                xAxisG.selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');
                xAxisG.selectAll('line').attr('stroke', '#e2e8f0');
                if (_lastYScale) drawGridlines(_lastYScale);

                totalAreaPath.attr('d', totalAreaGen);
                totalLinePath.attr('d', totalLineGen);
                segments.forEach(function(seg) {
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
                    var rpx = xScale(peakRow._date), rpy = yScaleStock(peakRow.value);
                    peakAnnotG.select('line').attr('x1', rpx).attr('x2', rpx).attr('y1', rpy).attr('y2', rpy + 30);
                    peakAnnotG.select('text').attr('x', rpx).attr('y', rpy - 6);
                }
                if (currentChapter === 2) { updateStreamLabels(1); }
                if (currentChapter === 1) { treemapBuilt = false; buildTreemap(); }
                if (currentChapter === 4 && window.d3sankey) { drawSankey(); }

                // Reposition seg cards container
                if (SEG_CARDS_DIV) {
                    var nW2 = newW - margin.left - margin.right;
                    SEG_CARDS_DIV.style.left  = margin.left + 'px';
                    SEG_CARDS_DIV.style.width  = nW2 + 'px';
                }
            });
            ro.observe(parentElement);
            parentElement._resizeObserver = ro;
        }

        // =====================================================================
        // INITIAL ACTIVATION
        // =====================================================================
        requestAnimationFrame(function() {
            updateUI();
            activateStep(0);
        });

        var _unloadHandler = function() {
            if (parentElement._keydownHandler) {
                document.removeEventListener('keydown', parentElement._keydownHandler);
            }
        };
        window.addEventListener('unload', _unloadHandler);
        parentElement._unloadHandler = _unloadHandler;

    } // end buildStory
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
            real_kpis — dict with actual CBA FY26 KPIs
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
