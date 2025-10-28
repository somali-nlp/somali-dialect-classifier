/**
 * Advanced Chart Components
 * Sankey diagrams, Ridge plots, and Bullet charts for advanced data visualization
 */

// ========================================
// SANKEY DIAGRAM (Data Flow Visualization)
// ========================================
export const SankeyChart = {
    /**
     * Create a Sankey/Funnel diagram showing data flow through pipeline stages
     * Using D3-sankey for proper flow visualization
     */
    create(containerId, metrics) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return null;
        }

        // Aggregate data from all sources
        const aggregated = this.aggregateFlowData(metrics);

        // Create canvas-based Sankey using manual rendering
        // This avoids needing D3-sankey library (keeping bundle size small)
        return this.renderManualSankey(container, aggregated);
    },

    aggregateFlowData(metrics) {
        const flow = {
            discovered: 0,
            fetched: 0,
            extracted: 0,
            passed_quality: 0,
            filtered_duplicate: 0,
            filtered_quality: 0,
            filtered_other: 0,
            written: 0
        };

        metrics.forEach(metric => {
            if (!metric) return;

            const layered = metric.layered_metrics || {};
            const legacy = metric.legacy_metrics?.snapshot || {};

            // Connectivity (Discovery)
            flow.discovered += legacy.urls_discovered || legacy.files_discovered || 0;

            // Extraction
            flow.fetched += legacy.urls_fetched || legacy.files_processed || legacy.records_fetched || 0;
            flow.extracted += layered.extraction?.content_extracted || legacy.records_extracted || 0;

            // Quality filtering
            const qualityMetrics = layered.quality || {};
            flow.passed_quality += qualityMetrics.records_passed_filters || 0;

            // Filter breakdown
            const filterBreakdown = qualityMetrics.filter_breakdown || legacy.filter_reasons || {};
            Object.entries(filterBreakdown).forEach(([reason, count]) => {
                if (reason.toLowerCase().includes('duplicate') || reason.toLowerCase().includes('hash')) {
                    flow.filtered_duplicate += count;
                } else if (reason.toLowerCase().includes('length') || reason.toLowerCase().includes('quality')) {
                    flow.filtered_quality += count;
                } else {
                    flow.filtered_other += count;
                }
            });

            // Volume (Final output)
            flow.written += layered.volume?.records_written || legacy.records_written || 0;
        });

        return flow;
    },

    renderManualSankey(container, flow) {
        container.innerHTML = '';

        const width = container.offsetWidth || 800;
        const height = 500;
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.style.width = '100%';
        svg.style.height = 'auto';

        // Define stages
        const stages = [
            { id: 'discovered', label: 'Discovered', value: flow.discovered, color: '#94a3b8', x: 0 },
            { id: 'fetched', label: 'Fetched', value: flow.fetched, color: '#60a5fa', x: 1 },
            { id: 'extracted', label: 'Extracted', value: flow.extracted, color: '#3b82f6', x: 2 },
            { id: 'quality_checked', label: 'Quality Check', value: flow.extracted, color: '#2563eb', x: 3 },
            { id: 'written', label: 'Written', value: flow.written, color: '#10b981', x: 4 }
        ];

        // Calculate max value for scaling
        const maxValue = Math.max(...stages.map(s => s.value), 1);

        // Layout parameters
        const stageWidth = 100;
        const stageSpacing = (width - stageWidth * stages.length - 100) / (stages.length - 1);
        const padding = 50;
        const maxHeight = height - 2 * padding;

        // Position stages
        stages.forEach((stage, i) => {
            stage.xPos = padding + i * (stageWidth + stageSpacing);
            stage.height = (stage.value / maxValue) * maxHeight;
            stage.yPos = padding + (maxHeight - stage.height) / 2;
        });

        // Create gradient definitions
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

        // Add flow gradients
        const createGradient = (id, color1, color2) => {
            const grad = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            grad.setAttribute('id', id);
            grad.setAttribute('x1', '0%');
            grad.setAttribute('x2', '100%');

            const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop1.setAttribute('offset', '0%');
            stop1.setAttribute('stop-color', color1);
            stop1.setAttribute('stop-opacity', '0.6');

            const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop2.setAttribute('offset', '100%');
            stop2.setAttribute('stop-color', color2);
            stop2.setAttribute('stop-opacity', '0.6');

            grad.appendChild(stop1);
            grad.appendChild(stop2);
            return grad;
        };

        for (let i = 0; i < stages.length - 1; i++) {
            defs.appendChild(createGradient(`flow-${i}`, stages[i].color, stages[i + 1].color));
        }
        svg.appendChild(defs);

        // Draw flows (connections)
        const drawFlow = (fromStage, toStage, value, gradientId) => {
            if (value <= 0) return;

            const flowHeight = (value / maxValue) * maxHeight;
            const fromY = fromStage.yPos + (fromStage.height - flowHeight) / 2;
            const toY = toStage.yPos + (toStage.height - flowHeight) / 2;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            const fromX = fromStage.xPos + stageWidth;
            const toX = toStage.xPos;
            const midX = (fromX + toX) / 2;

            const d = `
                M ${fromX} ${fromY}
                C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}
                L ${toX} ${toY + flowHeight}
                C ${midX} ${toY + flowHeight}, ${midX} ${fromY + flowHeight}, ${fromX} ${fromY + flowHeight}
                Z
            `;

            path.setAttribute('d', d);
            path.setAttribute('fill', `url(#${gradientId})`);
            path.setAttribute('stroke', 'none');
            path.classList.add('sankey-flow');

            // Hover effect
            path.addEventListener('mouseenter', function() {
                this.style.opacity = '1';
                this.style.filter = 'brightness(1.1)';
            });
            path.addEventListener('mouseleave', function() {
                this.style.opacity = '0.6';
                this.style.filter = 'brightness(1)';
            });

            // Tooltip
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = `${fromStage.label} → ${toStage.label}: ${value.toLocaleString()} records`;
            path.appendChild(title);

            svg.appendChild(path);
        };

        // Draw all flows
        drawFlow(stages[0], stages[1], flow.fetched, 'flow-0');
        drawFlow(stages[1], stages[2], flow.extracted, 'flow-1');
        drawFlow(stages[2], stages[3], flow.extracted, 'flow-2');
        drawFlow(stages[3], stages[4], flow.written, 'flow-3');

        // Draw stage rectangles
        stages.forEach((stage, i) => {
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', stage.xPos);
            rect.setAttribute('y', stage.yPos);
            rect.setAttribute('width', stageWidth);
            rect.setAttribute('height', stage.height || 5);
            rect.setAttribute('fill', stage.color);
            rect.setAttribute('rx', '4');
            rect.classList.add('sankey-node');

            // Hover effect
            rect.addEventListener('mouseenter', function() {
                this.style.filter = 'brightness(1.2)';
            });
            rect.addEventListener('mouseleave', function() {
                this.style.filter = 'brightness(1)';
            });

            // Tooltip
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = `${stage.label}: ${stage.value.toLocaleString()} records`;
            rect.appendChild(title);

            svg.appendChild(rect);

            // Stage label
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', stage.xPos + stageWidth / 2);
            label.setAttribute('y', stage.yPos - 10);
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('fill', '#374151');
            label.setAttribute('font-size', '13');
            label.setAttribute('font-weight', '600');
            label.textContent = stage.label;
            svg.appendChild(label);

            // Value label
            const valueLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            valueLabel.setAttribute('x', stage.xPos + stageWidth / 2);
            valueLabel.setAttribute('y', stage.yPos + stage.height + 25);
            valueLabel.setAttribute('text-anchor', 'middle');
            valueLabel.setAttribute('fill', '#6b7280');
            valueLabel.setAttribute('font-size', '12');
            valueLabel.textContent = this.formatNumber(stage.value);
            svg.appendChild(valueLabel);
        });

        // Add filter annotations
        if (flow.filtered_duplicate > 0 || flow.filtered_quality > 0) {
            const filterY = stages[3].yPos + stages[3].height + 60;

            if (flow.filtered_duplicate > 0) {
                const filterText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                filterText.setAttribute('x', stages[3].xPos + stageWidth / 2);
                filterText.setAttribute('y', filterY);
                filterText.setAttribute('text-anchor', 'middle');
                filterText.setAttribute('fill', '#ef4444');
                filterText.setAttribute('font-size', '11');
                filterText.textContent = `↓ Duplicates: ${this.formatNumber(flow.filtered_duplicate)}`;
                svg.appendChild(filterText);
            }

            if (flow.filtered_quality > 0) {
                const filterText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                filterText.setAttribute('x', stages[3].xPos + stageWidth / 2);
                filterText.setAttribute('y', filterY + 15);
                filterText.setAttribute('text-anchor', 'middle');
                filterText.setAttribute('fill', '#f59e0b');
                filterText.setAttribute('font-size', '11');
                filterText.textContent = `↓ Quality: ${this.formatNumber(flow.filtered_quality)}`;
                svg.appendChild(filterText);
            }
        }

        container.appendChild(svg);
        return svg;
    },

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toLocaleString();
    }
};

// ========================================
// RIDGE PLOT (Text Length Distribution)
// ========================================
export const RidgePlot = {
    /**
     * Create ridge plots for text-length distribution comparison
     * Overlapping density curves for each source
     */
    create(containerId, metrics) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return null;
        }

        // Extract text length data by source
        const sourceData = this.extractTextLengthData(metrics);

        return this.renderRidgePlot(container, sourceData);
    },

    extractTextLengthData(metrics) {
        const data = {};

        metrics.forEach(metric => {
            if (!metric) return;

            const source = this.getSourceName(metric._source || metric.source);
            const textLengths = metric.legacy_metrics?.snapshot?.text_lengths || [];

            if (textLengths.length > 0 && !data[source]) {
                data[source] = textLengths;
            }
        });

        return data;
    },

    getSourceName(fullSource) {
        if (!fullSource) return 'Unknown';
        return fullSource
            .replace(/-Somali|_Somali_c4-so|-somali/gi, '')
            .replace('Sprakbanken', 'Språkbanken')
            .trim();
    },

    renderRidgePlot(container, sourceData) {
        container.innerHTML = '';

        const sources = Object.keys(sourceData);
        if (sources.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No text length data available</p>';
            return null;
        }

        const width = container.offsetWidth || 800;
        const ridgeHeight = 80;
        const spacing = 20;
        const height = sources.length * (ridgeHeight + spacing) + 100;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.style.width = '100%';
        svg.style.height = 'auto';

        const padding = { left: 150, right: 50, top: 50, bottom: 50 };
        const chartWidth = width - padding.left - padding.right;

        // Colors for each source
        const colors = {
            'Wikipedia': '#3b82f6',
            'BBC': '#ef4444',
            'HuggingFace': '#10b981',
            'Språkbanken': '#f59e0b'
        };

        // Find global min/max for consistent x-axis (log scale)
        let globalMin = Infinity;
        let globalMax = 0;

        sources.forEach(source => {
            const lengths = sourceData[source].filter(l => l > 0);
            if (lengths.length > 0) {
                globalMin = Math.min(globalMin, ...lengths);
                globalMax = Math.max(globalMax, ...lengths);
            }
        });

        // Use log scale for x-axis
        const logMin = Math.log10(Math.max(globalMin, 1));
        const logMax = Math.log10(globalMax);

        // Create density curves for each source
        sources.forEach((source, idx) => {
            const y = padding.top + idx * (ridgeHeight + spacing);
            const lengths = sourceData[source].filter(l => l > 0);

            if (lengths.length === 0) return;

            // Calculate density using kernel density estimation (simplified)
            const bins = 50;
            const density = this.calculateDensity(lengths, bins, globalMin, globalMax);

            // Find max density for scaling
            const maxDensity = Math.max(...density.map(d => d.density), 1);

            // Create path for density curve
            const points = density.map(d => {
                const logValue = Math.log10(Math.max(d.value, 1));
                const x = padding.left + ((logValue - logMin) / (logMax - logMin)) * chartWidth;
                const curveY = y + ridgeHeight - (d.density / maxDensity) * ridgeHeight;
                return { x, y: curveY };
            });

            // Draw filled area
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            let d = `M ${padding.left} ${y + ridgeHeight} `;
            points.forEach((p, i) => {
                if (i === 0) d += `L ${p.x} ${p.y} `;
                else d += `L ${p.x} ${p.y} `;
            });
            d += `L ${padding.left + chartWidth} ${y + ridgeHeight} Z`;

            path.setAttribute('d', d);
            path.setAttribute('fill', colors[source] || '#9ca3af');
            path.setAttribute('fill-opacity', '0.5');
            path.setAttribute('stroke', colors[source] || '#6b7280');
            path.setAttribute('stroke-width', '2');
            path.classList.add('ridge-curve');
            svg.appendChild(path);

            // Add median line
            const median = this.calculateMedian(lengths);
            const medianLogValue = Math.log10(Math.max(median, 1));
            const medianX = padding.left + ((medianLogValue - logMin) / (logMax - logMin)) * chartWidth;

            const medianLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            medianLine.setAttribute('x1', medianX);
            medianLine.setAttribute('y1', y);
            medianLine.setAttribute('x2', medianX);
            medianLine.setAttribute('y2', y + ridgeHeight);
            medianLine.setAttribute('stroke', colors[source] || '#6b7280');
            medianLine.setAttribute('stroke-width', '2');
            medianLine.setAttribute('stroke-dasharray', '4 2');
            medianLine.setAttribute('opacity', '0.8');
            svg.appendChild(medianLine);

            // Source label
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', padding.left - 10);
            label.setAttribute('y', y + ridgeHeight / 2);
            label.setAttribute('text-anchor', 'end');
            label.setAttribute('dominant-baseline', 'middle');
            label.setAttribute('fill', '#374151');
            label.setAttribute('font-size', '13');
            label.setAttribute('font-weight', '600');
            label.textContent = source;
            svg.appendChild(label);

            // Median value label
            const medianLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            medianLabel.setAttribute('x', medianX);
            medianLabel.setAttribute('y', y - 5);
            medianLabel.setAttribute('text-anchor', 'middle');
            medianLabel.setAttribute('fill', colors[source] || '#6b7280');
            medianLabel.setAttribute('font-size', '10');
            medianLabel.textContent = Math.round(median);
            svg.appendChild(medianLabel);
        });

        // X-axis (logarithmic)
        const axisY = padding.top + sources.length * (ridgeHeight + spacing);
        const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        axisLine.setAttribute('x1', padding.left);
        axisLine.setAttribute('y1', axisY);
        axisLine.setAttribute('x2', padding.left + chartWidth);
        axisLine.setAttribute('y2', axisY);
        axisLine.setAttribute('stroke', '#d1d5db');
        axisLine.setAttribute('stroke-width', '2');
        svg.appendChild(axisLine);

        // X-axis ticks (log scale)
        const logTicks = [10, 100, 1000, 10000, 100000];
        logTicks.forEach(tickValue => {
            if (tickValue < globalMin || tickValue > globalMax) return;

            const logValue = Math.log10(tickValue);
            const x = padding.left + ((logValue - logMin) / (logMax - logMin)) * chartWidth;

            const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            tick.setAttribute('x1', x);
            tick.setAttribute('y1', axisY);
            tick.setAttribute('x2', x);
            tick.setAttribute('y2', axisY + 5);
            tick.setAttribute('stroke', '#6b7280');
            tick.setAttribute('stroke-width', '1');
            svg.appendChild(tick);

            const tickLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            tickLabel.setAttribute('x', x);
            tickLabel.setAttribute('y', axisY + 20);
            tickLabel.setAttribute('text-anchor', 'middle');
            tickLabel.setAttribute('fill', '#6b7280');
            tickLabel.setAttribute('font-size', '11');
            tickLabel.textContent = tickValue >= 1000 ? (tickValue / 1000) + 'K' : tickValue;
            svg.appendChild(tickLabel);
        });

        // X-axis label
        const xLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        xLabel.setAttribute('x', padding.left + chartWidth / 2);
        xLabel.setAttribute('y', axisY + 45);
        xLabel.setAttribute('text-anchor', 'middle');
        xLabel.setAttribute('fill', '#374151');
        xLabel.setAttribute('font-size', '13');
        xLabel.setAttribute('font-weight', '600');
        xLabel.textContent = 'Text Length (characters, log scale)';
        svg.appendChild(xLabel);

        container.appendChild(svg);
        return svg;
    },

    calculateDensity(data, bins, min, max) {
        const binWidth = (max - min) / bins;
        const density = [];

        for (let i = 0; i < bins; i++) {
            const binMin = min + i * binWidth;
            const binMax = binMin + binWidth;
            const binCenter = (binMin + binMax) / 2;

            // Count values in bin with Gaussian kernel
            let count = 0;
            const bandwidth = binWidth * 2;

            data.forEach(value => {
                const distance = Math.abs(value - binCenter);
                const weight = Math.exp(-(distance * distance) / (2 * bandwidth * bandwidth));
                count += weight;
            });

            density.push({
                value: binCenter,
                density: count / data.length
            });
        }

        return density;
    },

    calculateMedian(arr) {
        const sorted = [...arr].sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        return sorted.length % 2 === 0
            ? (sorted[mid - 1] + sorted[mid]) / 2
            : sorted[mid];
    }
};

// ========================================
// BULLET CHART (Performance Metrics)
// ========================================
export const BulletChart = {
    /**
     * Create bullet charts with dual encoding
     * Horizontal bars with control bands, targets, and quality dots
     */
    create(containerId, metrics) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return null;
        }

        const data = this.prepareData(metrics);
        return this.renderBulletChart(container, data);
    },

    prepareData(metrics) {
        const sourceMetrics = {};

        metrics.forEach(metric => {
            if (!metric) return;

            const source = this.getSourceName(metric._source || metric.source);
            const layered = metric.layered_metrics || {};
            const legacy = metric.legacy_metrics || {};
            const stats = legacy.statistics || {};

            if (!sourceMetrics[source]) {
                sourceMetrics[source] = {
                    performance: 0,
                    quality: 0,
                    throughput: 0,
                    target: 80
                };
            }

            // Calculate performance score (0-100)
            const successRate = stats.http_request_success_rate || stats.fetch_success_rate || 0;
            const extractionRate = stats.content_extraction_success_rate || 0;
            const qualityRate = stats.quality_pass_rate || 0;

            sourceMetrics[source].performance = (successRate * 100 + extractionRate * 100 + qualityRate * 100) / 3;
            sourceMetrics[source].quality = qualityRate * 100;

            // Throughput (records per minute)
            const throughput = stats.throughput || {};
            sourceMetrics[source].throughput = throughput.records_per_minute || 0;
        });

        return sourceMetrics;
    },

    getSourceName(fullSource) {
        if (!fullSource) return 'Unknown';
        return fullSource
            .replace(/-Somali|_Somali_c4-so|-somali/gi, '')
            .replace('Sprakbanken', 'Språkbanken')
            .trim();
    },

    renderBulletChart(container, data) {
        container.innerHTML = '';

        const sources = Object.keys(data);
        if (sources.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No performance data available</p>';
            return null;
        }

        const width = container.offsetWidth || 800;
        const barHeight = 60;
        const spacing = 40;
        const height = sources.length * (barHeight + spacing) + 100;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.style.width = '100%';
        svg.style.height = 'auto';

        const padding = { left: 150, right: 50, top: 50, bottom: 50 };
        const chartWidth = width - padding.left - padding.right;

        // Colors
        const colors = {
            'Wikipedia': '#3b82f6',
            'BBC': '#ef4444',
            'HuggingFace': '#10b981',
            'Språkbanken': '#f59e0b'
        };

        sources.forEach((source, idx) => {
            const y = padding.top + idx * (barHeight + spacing);
            const metric = data[source];

            // Control bands (background zones)
            const bands = [
                { threshold: 40, color: '#fee2e2', label: 'Poor' },
                { threshold: 70, color: '#fef3c7', label: 'Fair' },
                { threshold: 90, color: '#d1fae5', label: 'Good' },
                { threshold: 100, color: '#a7f3d0', label: 'Excellent' }
            ];

            let prevThreshold = 0;
            bands.forEach(band => {
                const bandWidth = ((band.threshold - prevThreshold) / 100) * chartWidth;
                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                rect.setAttribute('x', padding.left + (prevThreshold / 100) * chartWidth);
                rect.setAttribute('y', y);
                rect.setAttribute('width', bandWidth);
                rect.setAttribute('height', barHeight);
                rect.setAttribute('fill', band.color);
                rect.setAttribute('opacity', '0.5');
                svg.appendChild(rect);
                prevThreshold = band.threshold;
            });

            // Performance bar
            const perfWidth = (metric.performance / 100) * chartWidth;
            const perfBar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            perfBar.setAttribute('x', padding.left);
            perfBar.setAttribute('y', y + 15);
            perfBar.setAttribute('width', perfWidth);
            perfBar.setAttribute('height', 30);
            perfBar.setAttribute('fill', colors[source] || '#9ca3af');
            perfBar.setAttribute('rx', '4');
            svg.appendChild(perfBar);

            // Target marker
            const targetX = padding.left + (metric.target / 100) * chartWidth;
            const targetLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            targetLine.setAttribute('x1', targetX);
            targetLine.setAttribute('y1', y);
            targetLine.setAttribute('x2', targetX);
            targetLine.setAttribute('y2', y + barHeight);
            targetLine.setAttribute('stroke', '#1f2937');
            targetLine.setAttribute('stroke-width', '3');
            svg.appendChild(targetLine);

            // Quality dot overlay
            const qualityX = padding.left + (metric.quality / 100) * chartWidth;
            const qualityDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            qualityDot.setAttribute('cx', qualityX);
            qualityDot.setAttribute('cy', y + barHeight / 2);
            qualityDot.setAttribute('r', '8');
            qualityDot.setAttribute('fill', metric.quality >= 70 ? '#10b981' : '#f59e0b');
            qualityDot.setAttribute('stroke', 'white');
            qualityDot.setAttribute('stroke-width', '2');
            svg.appendChild(qualityDot);

            // Source label
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', padding.left - 10);
            label.setAttribute('y', y + barHeight / 2);
            label.setAttribute('text-anchor', 'end');
            label.setAttribute('dominant-baseline', 'middle');
            label.setAttribute('fill', '#374151');
            label.setAttribute('font-size', '13');
            label.setAttribute('font-weight', '600');
            label.textContent = source;
            svg.appendChild(label);

            // Performance value
            const valueLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            valueLabel.setAttribute('x', padding.left + perfWidth + 10);
            valueLabel.setAttribute('y', y + barHeight / 2);
            valueLabel.setAttribute('dominant-baseline', 'middle');
            valueLabel.setAttribute('fill', '#374151');
            valueLabel.setAttribute('font-size', '12');
            valueLabel.setAttribute('font-weight', '600');
            valueLabel.textContent = metric.performance.toFixed(1) + '%';
            svg.appendChild(valueLabel);
        });

        // X-axis
        const axisY = padding.top + sources.length * (barHeight + spacing);
        const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        axisLine.setAttribute('x1', padding.left);
        axisLine.setAttribute('y1', axisY);
        axisLine.setAttribute('x2', padding.left + chartWidth);
        axisLine.setAttribute('y2', axisY);
        axisLine.setAttribute('stroke', '#d1d5db');
        axisLine.setAttribute('stroke-width', '2');
        svg.appendChild(axisLine);

        // X-axis ticks
        [0, 25, 50, 75, 100].forEach(tickValue => {
            const x = padding.left + (tickValue / 100) * chartWidth;

            const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            tick.setAttribute('x1', x);
            tick.setAttribute('y1', axisY);
            tick.setAttribute('x2', x);
            tick.setAttribute('y2', axisY + 5);
            tick.setAttribute('stroke', '#6b7280');
            tick.setAttribute('stroke-width', '1');
            svg.appendChild(tick);

            const tickLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            tickLabel.setAttribute('x', x);
            tickLabel.setAttribute('y', axisY + 20);
            tickLabel.setAttribute('text-anchor', 'middle');
            tickLabel.setAttribute('fill', '#6b7280');
            tickLabel.setAttribute('font-size', '11');
            tickLabel.textContent = tickValue + '%';
            svg.appendChild(tickLabel);
        });

        // Legend
        const legendY = padding.top - 30;
        const legendItems = [
            { label: 'Performance Score', color: '#3b82f6', type: 'bar' },
            { label: 'Quality Rate', color: '#10b981', type: 'dot' },
            { label: 'Target', color: '#1f2937', type: 'line' }
        ];

        let legendX = padding.left;
        legendItems.forEach(item => {
            if (item.type === 'bar') {
                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                rect.setAttribute('x', legendX);
                rect.setAttribute('y', legendY);
                rect.setAttribute('width', '20');
                rect.setAttribute('height', '10');
                rect.setAttribute('fill', item.color);
                rect.setAttribute('rx', '2');
                svg.appendChild(rect);
            } else if (item.type === 'dot') {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', legendX + 10);
                circle.setAttribute('cy', legendY + 5);
                circle.setAttribute('r', '5');
                circle.setAttribute('fill', item.color);
                svg.appendChild(circle);
            } else if (item.type === 'line') {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', legendX);
                line.setAttribute('y1', legendY + 5);
                line.setAttribute('x2', legendX + 20);
                line.setAttribute('y2', legendY + 5);
                line.setAttribute('stroke', item.color);
                line.setAttribute('stroke-width', '3');
                svg.appendChild(line);
            }

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', legendX + 25);
            label.setAttribute('y', legendY + 5);
            label.setAttribute('dominant-baseline', 'middle');
            label.setAttribute('fill', '#374151');
            label.setAttribute('font-size', '11');
            label.textContent = item.label;
            svg.appendChild(label);

            legendX += 150;
        });

        container.appendChild(svg);
        return svg;
    }
};
