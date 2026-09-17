"""TradingView Lightweight Charts as a Streamlit V2 custom component.

Uses st.components.v2.component() (no iframe) — same pattern as streamlit-jsme.
Loads lightweight-charts@4.2.0 from the unpkg CDN on first render.
"""
from __future__ import annotations

import streamlit as st

_HTML = '<div id="tv_root" style="width:100%;"></div>'

_JS = r"""
export default function(component) {
    const { parentElement, data } = component;

    const height     = (data && data.height)      || 400;
    const chartType  = (data && data.chart_type)  || 'candlestick';
    const seriesData = (data && data.series_data) || [];
    const volumeData = (data && data.volume_data) || [];
    const overlays   = (data && data.overlays)    || [];
    const colors     = (data && data.colors)      || {};

    const container = parentElement.querySelector('#tv_root');
    if (!container) return;

    // Reserve vertical space immediately so Streamlit layout is stable.
    container.style.height = height + 'px';
    container.style.overflow = 'hidden';

    const CDN = 'https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js';

    function loadScript(src) {
        return new Promise(function(resolve, reject) {
            if (window.LightweightCharts) { resolve(); return; }
            var existing = document.querySelector('script[data-tv-lc]');
            if (existing) {
                existing.addEventListener('load', resolve);
                existing.addEventListener('error', reject);
                return;
            }
            var s = document.createElement('script');
            s.setAttribute('data-tv-lc', '1');
            s.src = src;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    function getTheme() {
        var style   = getComputedStyle(document.documentElement);
        var bg      = style.getPropertyValue('--background-color').trim() || '#ffffff';
        var text    = style.getPropertyValue('--text-color').trim()        || '#1a1d21';
        var isDark  = bg && (bg.match(/^#[0-2]/) || bg.match(/^rgb\(\s*[012]\d/));
        return {
            text:   text,
            grid:   isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)',
            border: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)',
        };
    }

    function buildChart() {
        if (parentElement._tvChart) {
            try { parentElement._tvChart.remove(); } catch(e) {}
            parentElement._tvChart = null;
        }
        if (parentElement._tvRO) { parentElement._tvRO.disconnect(); }

        var theme = getTheme();
        var w = container.offsetWidth || 800;

        var chart = LightweightCharts.createChart(container, {
            width:  w,
            height: height,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor:  theme.text,
                fontSize:   12,
            },
            grid: {
                vertLines: { color: theme.grid },
                horzLines: { color: theme.grid },
            },
            rightPriceScale: { borderColor: theme.border },
            timeScale:        { borderColor: theme.border, timeVisible: false },
            crosshair:        { mode: LightweightCharts.CrosshairMode.Normal },
        });
        parentElement._tvChart = chart;

        var upColor   = colors.up   || '#0F8A5F';
        var downColor = colors.down || '#C0392B';
        var lineColor = colors.line || '#0F4C81';

        if (chartType === 'candlestick' && seriesData.length) {
            var cs = chart.addCandlestickSeries({
                upColor:        upColor,   downColor:        downColor,
                borderUpColor:  upColor,   borderDownColor:  downColor,
                wickUpColor:    upColor,   wickDownColor:    downColor,
            });
            cs.setData(seriesData);

            if (volumeData.length) {
                var vs = chart.addHistogramSeries({
                    priceFormat:  { type: 'volume' },
                    priceScaleId: 'vol',
                });
                chart.priceScale('vol').applyOptions({
                    scaleMargins: { top: 0.82, bottom: 0 },
                });
                var volColored = volumeData.map(function(v, i) {
                    var isDown = seriesData[i] && seriesData[i].close < seriesData[i].open;
                    return Object.assign({}, v, {
                        color: isDown ? 'rgba(192,57,43,0.4)' : 'rgba(15,76,129,0.4)',
                    });
                });
                vs.setData(volColored);
            }
        } else if (chartType === 'area' && seriesData.length) {
            var as = chart.addAreaSeries({
                topColor:    'rgba(15,76,129,0.30)',
                bottomColor: 'rgba(15,76,129,0.00)',
                lineColor:   lineColor,
                lineWidth:   2,
            });
            as.setData(seriesData);
        } else if (chartType === 'line' && seriesData.length) {
            var ls = chart.addLineSeries({ color: lineColor, lineWidth: 2 });
            ls.setData(seriesData);
        }

        // Overlay (peer-comparison) lines
        var palette = ['#C9A227', '#C0392B', '#6FA8C9', '#0F8A5F'];
        overlays.forEach(function(ov, idx) {
            if (!ov.data || !ov.data.length) return;
            var ol = chart.addLineSeries({
                color:                  ov.color || palette[idx % palette.length],
                lineWidth:              1.5,
                lineStyle:              2,   // dashed
                title:                  ov.name || '',
                crosshairMarkerVisible: false,
            });
            ol.setData(ov.data);
        });

        chart.timeScale().fitContent();

        // Responsive width
        parentElement._tvRO = new ResizeObserver(function(entries) {
            var newW = Math.round(entries[0].contentRect.width);
            if (newW > 0 && parentElement._tvChart) {
                parentElement._tvChart.applyOptions({ width: newW });
            }
        });
        parentElement._tvRO.observe(container);
    }

    loadScript(CDN).then(buildChart).catch(function(err) {
        container.innerHTML =
            '<p style="color:red;padding:8px;">Chart library failed to load. Check internet access.</p>';
    });

    return function() {
        if (parentElement._tvRO)    parentElement._tvRO.disconnect();
        if (parentElement._tvChart) try { parentElement._tvChart.remove(); } catch(e) {}
    };
}
"""

_tv_component = st.components.v2.component(
    "tv_chart",
    html=_HTML,
    js=_JS,
    isolate_styles=False,
)


def st_tv_chart(
    series_data: list[dict],
    volume_data: list[dict] | None = None,
    overlays: list[dict] | None = None,
    *,
    chart_type: str = "candlestick",
    height: int = 400,
    colors: dict | None = None,
    key: str | None = None,
) -> None:
    """Render a TradingView Lightweight Chart (v4.2) as a Streamlit V2 component.

    Parameters
    ----------
    series_data:
        Candlestick: list of {time, open, high, low, close}.
        Line/area:   list of {time, value}.
        ``time`` must be an ISO date string e.g. ``"2024-03-15"``.
    volume_data:
        Optional list of {time, value} for the volume histogram (candlestick only).
    overlays:
        Optional list of {name, data, color?} for extra line series (peer comparison).
        Each ``data`` entry is {time, value}.
    chart_type:
        ``"candlestick"``, ``"area"``, or ``"line"``.
    height:
        Chart height in pixels.
    colors:
        Override chart colors: {up, down, line}.
    key:
        Unique Streamlit component key.
    """
    _tv_component(
        data={
            "series_data": series_data,
            "volume_data": volume_data or [],
            "overlays":    overlays or [],
            "chart_type":  chart_type,
            "height":      height,
            "colors":      colors or {},
        },
        default=None,
        key=key or f"tv_{chart_type}",
    )
