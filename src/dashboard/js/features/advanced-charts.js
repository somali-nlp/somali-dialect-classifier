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
    create(containerId, metrics, flowData = null) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return null;
        }

        // Prefer pre-aggregated flow data, fall back to derived metrics
        const aggregated = flowData
            ? this.normalizeExternalFlow(flowData)
            : this.aggregateFlowData(metrics);

        if (!aggregated) {
            container.innerHTML = '<p style="text-align:center;padding:2rem;color:#6b7280;">Sankey data is not yet available.</p>';
            return null;
        }

        // Create canvas-based Sankey using manual rendering
        // This avoids needing D3-sankey library (keeping bundle size small)
        return this.renderManualSankey(container, aggregated);
    },

    normalizeExternalFlow(flowData) {
        if (!flowData) {
            return null;
        }

        const stageCounts = flowData.stage_counts || {};
        const filterBreakdown = flowData.filter_breakdown || {};

        const aggregated = {
            discovered: stageCounts.discovered || 0,
            fetched: stageCounts.fetched || stageCounts.discovery || 0,
            extracted: stageCounts.extracted || 0,
            quality_received: stageCounts.quality_received || stageCounts.extracted || 0,
            passed_quality: stageCounts.quality_passed || stageCounts.written || 0,
            written: stageCounts.written || stageCounts['Silver Dataset'] || stageCounts.quality_passed || 0,
            filtered_duplicate: 0,
            filtered_quality: 0,
            filtered_other: 0
        };

        Object.entries(filterBreakdown).forEach(([reason, count]) => {
            const normalizedReason = reason.toLowerCase();
            if (normalizedReason.includes('duplicate') || normalizedReason.includes('hash')) {
                aggregated.filtered_duplicate += count;
            } else if (normalizedReason.includes('length') || normalizedReason.includes('quality')) {
                aggregated.filtered_quality += count;
            } else {
                aggregated.filtered_other += count;
            }
        });

        const hasAnyValue = Object.values(aggregated).some(value => typeof value === 'number' && value > 0);
        return hasAnyValue ? aggregated : null;
    },

    aggregateFlowData(metrics) {
        const flow = {
            discovered: 0,
            fetched: 0,
            extracted: 0,
            quality_received: 0,
            passed_quality: 0,
            filtered_duplicate: 0,
            filtered_quality: 0,
            filtered_other: 0,
            written: 0
        };

        if (!Array.isArray(metrics)) {
            return null;
        }

        metrics.forEach(metric => {
            if (!metric) return;

            const filteredTotal = Object.values(metric.filter_breakdown || {}).reduce((sum, value) => sum + value, 0);

            flow.discovered += metric.urls_discovered || 0;
            flow.fetched += metric.urls_fetched || metric.urls_discovered || 0;
            flow.extracted += metric.records_extracted || metric.records_written || 0;
            flow.quality_received += (metric.records_written || 0) + filteredTotal;
            flow.passed_quality += metric.records_written || 0;
            flow.written += metric.records_written || 0;

            Object.entries(metric.filter_breakdown || {}).forEach(([reason, count]) => {
                const normalizedReason = reason.toLowerCase();
                if (normalizedReason.includes('duplicate') || normalizedReason.includes('hash')) {
                    flow.filtered_duplicate += count;
                } else if (normalizedReason.includes('length') || normalizedReason.includes('quality')) {
                    flow.filtered_quality += count;
                } else {
                    flow.filtered_other += count;
                }
            });
        });

        const hasAnyValue = Object.values(flow).some(value => typeof value === 'number' && value > 0);
        return hasAnyValue ? flow : null;
    },

    renderManualSankey(container, flow) {
        container.innerHTML = '';

        const width = container.offsetWidth || 800;
        const height = 500;
        const desiredHeight = Math.max(height, 520);
        container.style.minHeight = `${desiredHeight}px`;
        container.style.height = `${desiredHeight}px`;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', desiredHeight);
        svg.setAttribute('viewBox', `0 0 ${width} ${desiredHeight}`);
        svg.style.width = '100%';
        svg.style.height = 'auto';

        // Define stages
        const stages = [
            { id: 'discovered', label: 'Discovered', value: flow.discovered, color: '#94a3b8', x: 0 },
            { id: 'fetched', label: 'Fetched', value: flow.fetched, color: '#60a5fa', x: 1 },
            { id: 'extracted', label: 'Extracted', value: flow.extracted, color: '#3b82f6', x: 2 },
            { id: 'quality_checked', label: 'Quality Check', value: flow.quality_received, color: '#2563eb', x: 3 },
            { id: 'written', label: 'Silver Dataset', value: flow.written, color: '#10b981', x: 4 }
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
        drawFlow(stages[2], stages[3], flow.quality_received, 'flow-2');
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
        const totalFiltered = (flow.filtered_duplicate || 0) + (flow.filtered_quality || 0) + (flow.filtered_other || 0);
        if (totalFiltered > 0) {
            const filterY = stages[3].yPos + stages[3].height + 60;
            const qualityDrop = Math.max(flow.quality_received - flow.written, 0);

            const breakdownRows = [
                { color: '#ef4444', label: 'Duplicates', value: flow.filtered_duplicate },
                { color: '#f59e0b', label: 'Quality Filters', value: flow.filtered_quality },
                { color: '#94a3b8', label: 'Other Filters', value: flow.filtered_other }
            ].filter(item => item.value > 0);

            const addText = (textContent, offsetY, color = '#6b7280') => {
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', stages[3].xPos + stageWidth / 2);
                text.setAttribute('y', offsetY);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('fill', color);
                text.setAttribute('font-size', '11');
                text.textContent = textContent;
                svg.appendChild(text);
            };

            addText(`Filtered: ${this.formatNumber(totalFiltered)} records`, filterY, '#ef4444');
            if (qualityDrop > 0) {
                addText(`Retained after QC: ${this.formatNumber(flow.written)}`, filterY + 15, '#2563eb');
            }

            breakdownRows.forEach((item, index) => {
                addText(`${item.label}: ${this.formatNumber(item.value)}`, filterY + 32 + index * 15, item.color);
            });
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
     * Supports both pre-aggregated distribution data and raw metric fallbacks
     */
    create(containerId, metrics, distributions = null) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} not found`);
            return null;
        }

        const distributionData = distributions
            ? this.normalizeDistributionData(distributions)
            : this.extractTextLengthData(metrics);

        if (!distributionData) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No text distribution data available</p>';
            return null;
        }

        return this.renderRidgePlot(container, distributionData);
    },

    extractTextLengthData(metrics) {
        if (!Array.isArray(metrics) || metrics.length === 0) {
            return null;
        }

        const lengthsBySource = new Map();

        metrics.forEach(metric => {
            if (!metric) return;

            const source = this.getSourceName(metric.source);
            const textLengths = metric.legacy_metrics?.snapshot?.text_lengths || [];

            if (textLengths.length > 0) {
                const filtered = textLengths.filter(value => value > 0);
                if (filtered.length === 0) return;

                const existing = lengthsBySource.get(source) || [];
                lengthsBySource.set(source, existing.concat(filtered));
            }
        });

        if (lengthsBySource.size === 0) {
            return null;
        }

        const edges = [10, 100, 1000, 10000, 100000, 1000000];
        const labels = ['10-100', '100-1K', '1K-10K', '10K-100K', '100K+'];
        const distributions = {};

        lengthsBySource.forEach((lengths, source) => {
            const histogram = this.computeHistogram(lengths, edges);
            distributions[source] = {
                bins: labels,
                bin_edges: edges,
                counts: histogram.counts,
                densities: histogram.densities,
                stats: histogram.stats
            };
        });

        return {
            sources: Array.from(lengthsBySource.keys()),
            binInfo: { edges, labels },
            distributions
        };
    },

    getSourceName(fullSource) {
        if (!fullSource) return 'Unknown';
        return fullSource
            .replace(/-Somali|_Somali_c4-so|-somali/gi, '')
            .replace('Sprakbanken', 'Språkbanken')
            .trim();
    },

    normalizeDistributionData(distributionData) {
        if (!distributionData || !distributionData.distributions) {
            return null;
        }

        return {
            sources: distributionData.sources || Object.keys(distributionData.distributions),
            binInfo: distributionData.bin_info || { edges: [], labels: [] },
            distributions: distributionData.distributions
        };
    },

    renderRidgePlot(container, sourceData) {
        container.innerHTML = '';

        const { sources, distributions, binInfo } = sourceData;
        if (!sources || sources.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No text distribution data available</p>';
            return null;
        }

        const width = container.offsetWidth || 800;
        const ridgeHeight = 70;
        const spacing = 24;
        const height = sources.length * (ridgeHeight + spacing) + 120;
        const desiredHeight = Math.max(height, 520);
        container.style.minHeight = `${desiredHeight}px`;
        container.style.height = `${desiredHeight}px`;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', desiredHeight);
        svg.setAttribute('viewBox', `0 0 ${width} ${desiredHeight}`);
        svg.style.width = '100%';
        svg.style.height = 'auto';

        const padding = { left: 170, right: 40, top: 40, bottom: 70 };
        const chartWidth = width - padding.left - padding.right;

        const edges = (binInfo.edges && binInfo.edges.length > 1)
            ? binInfo.edges
            : this.deriveEdges(distributions);

        if (!edges || edges.length < 2) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">Insufficient distribution data</p>';
            return null;
        }

        const globalMin = Math.max(edges[0], 1);
        const globalMax = edges[edges.length - 1];
        const logMin = Math.log10(globalMin);
        const logMax = Math.log10(globalMax);

        const colors = {
            'Wikipedia': '#3b82f6',
            'BBC': '#ef4444',
            'HuggingFace': '#10b981',
            'Språkbanken': '#f59e0b'
        };

        const maxDensity = sources.reduce((max, source) => {
            const densities = distributions[source]?.densities || [];
            const localMax = Math.max(...densities, 0);
            return Math.max(max, localMax);
        }, 0) || 1;

        sources.forEach((source, idx) => {
            const distribution = distributions[source];
            if (!distribution) return;

            const densities = distribution.densities || [];
            const counts = distribution.counts || [];
            const totalCount = counts.reduce((sum, value) => sum + value, 0);
            const labelText = `${this.getSourceName(source)} (${totalCount.toLocaleString()} samples)`;

            const yBase = padding.top + idx * (ridgeHeight + spacing);

            const points = densities.map((density, index) => {
                const edgeStart = edges[index];
                const edgeEnd = edges[index + 1] || edgeStart;
                const center = (edgeStart + edgeEnd) / 2;
                const logValue = Math.log10(Math.max(center, 1));
                const x = padding.left + ((logValue - logMin) / (logMax - logMin)) * chartWidth;
                const y = yBase + ridgeHeight - (density / maxDensity) * ridgeHeight;
                return { x, y };
            });

            if (points.length === 0) return;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            let d = `M ${padding.left} ${yBase + ridgeHeight} `;
            points.forEach(point => {
                d += `L ${point.x} ${point.y} `;
            });
            d += `L ${padding.left + chartWidth} ${yBase + ridgeHeight} Z`;

            const color = colors[this.getSourceName(source)] || '#3b82f6';
            path.setAttribute('d', d);
            path.setAttribute('fill', `${color}4d`);
            path.setAttribute('stroke', color);
            path.setAttribute('stroke-width', '1.5');
            path.classList.add('ridge-plot-layer');

            const stats = distribution.stats || {};
            const statsSummary = stats.count
                ? `Mean: ${Math.round(stats.mean).toLocaleString()} • Median: ${Math.round(stats.median).toLocaleString()}`
                : '';
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            title.textContent = statsSummary ? `${labelText} • ${statsSummary}` : labelText;
            path.appendChild(title);

            svg.appendChild(path);

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', padding.left - 20);
            label.setAttribute('y', yBase + ridgeHeight / 2);
            label.setAttribute('text-anchor', 'end');
            label.setAttribute('dominant-baseline', 'middle');
            label.setAttribute('fill', '#374151');
            label.setAttribute('font-size', '13');
            label.setAttribute('font-weight', '600');
            label.textContent = labelText;
            svg.appendChild(label);

            if (stats.median) {
                const medianLog = Math.log10(Math.max(stats.median, 1));
                const medianX = padding.left + ((medianLog - logMin) / (logMax - logMin)) * chartWidth;

                const medianLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                medianLine.setAttribute('x1', medianX);
                medianLine.setAttribute('y1', yBase);
                medianLine.setAttribute('x2', medianX);
                medianLine.setAttribute('y2', yBase + ridgeHeight);
                medianLine.setAttribute('stroke', color);
                medianLine.setAttribute('stroke-width', '2');
                medianLine.setAttribute('stroke-dasharray', '4 2');
                svg.appendChild(medianLine);

                const medianLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                medianLabel.setAttribute('x', medianX);
                medianLabel.setAttribute('y', yBase - 6);
                medianLabel.setAttribute('text-anchor', 'middle');
                medianLabel.setAttribute('fill', color);
                medianLabel.setAttribute('font-size', '10');
                medianLabel.textContent = Math.round(stats.median).toLocaleString();
                svg.appendChild(medianLabel);
            }
        });

        const axisGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        axisGroup.setAttribute('transform', `translate(0, ${desiredHeight - padding.bottom})`);

        const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        axisLine.setAttribute('x1', padding.left);
        axisLine.setAttribute('x2', padding.left + chartWidth);
        axisLine.setAttribute('y1', 0);
        axisLine.setAttribute('y2', 0);
        axisLine.setAttribute('stroke', '#d1d5db');
        axisLine.setAttribute('stroke-width', '1');
        axisGroup.appendChild(axisLine);

        const tickValues = edges.slice(0, -1).map((edge, index) => {
            const nextEdge = edges[index + 1] || edge;
            return Math.round(Math.sqrt(edge * nextEdge));
        });

        tickValues.forEach(value => {
            const logValue = Math.log10(Math.max(value, 1));
            const x = padding.left + ((logValue - logMin) / (logMax - logMin)) * chartWidth;

            const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            tick.setAttribute('x1', x);
            tick.setAttribute('x2', x);
            tick.setAttribute('y1', 0);
            tick.setAttribute('y2', 6);
            tick.setAttribute('stroke', '#9ca3af');
            tick.setAttribute('stroke-width', '1');
            axisGroup.appendChild(tick);

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', x);
            label.setAttribute('y', 20);
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('fill', '#6b7280');
            label.setAttribute('font-size', '11');
            label.textContent = this.formatTick(value);
            axisGroup.appendChild(label);
        });

        svg.appendChild(axisGroup);

        const axisLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        axisLabel.setAttribute('x', padding.left + chartWidth / 2);
        axisLabel.setAttribute('y', desiredHeight - 20);
        axisLabel.setAttribute('text-anchor', 'middle');
        axisLabel.setAttribute('fill', '#6b7280');
        axisLabel.setAttribute('font-size', '12');
        axisLabel.textContent = 'Text length (characters, log scale)';
        svg.appendChild(axisLabel);

        container.appendChild(svg);
        return svg;
    },

    deriveEdges(distributions) {
        const first = Object.values(distributions || {})[0];
        return first ? first.bin_edges : [];
    },

    formatTick(value) {
        if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
        if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
        return value.toLocaleString();
    },

    computeHistogram(values, edges) {
        const counts = new Array(edges.length - 1).fill(0);

        values.forEach(value => {
            if (value < edges[0]) return;

            let index = edges.findIndex((edge, idx) => value >= edge && value < edges[idx + 1]);
            if (index === -1) {
                index = counts.length - 1;
            }
            index = Math.min(index, counts.length - 1);
            counts[index] += 1;
        });

        const total = values.length || 1;
        const densities = counts.map(count => count / total);
        const stats = this.calculateStats(values);

        return { counts, densities, stats };
    },

    calculateStats(values) {
        if (!values || values.length === 0) {
            return {
                mean: 0,
                median: 0,
                q1: 0,
                q3: 0,
                min: 0,
                max: 0,
                count: 0
            };
        }

        const sorted = [...values].sort((a, b) => a - b);
        const sum = sorted.reduce((acc, val) => acc + val, 0);

        return {
            mean: sum / sorted.length,
            median: this.calculateMedian(sorted),
            q1: this.calculateQuantile(sorted, 0.25),
            q3: this.calculateQuantile(sorted, 0.75),
            min: sorted[0],
            max: sorted[sorted.length - 1],
            count: sorted.length
        };
    },

    calculateMedian(sortedValues) {
        if (!sortedValues || sortedValues.length === 0) {
            return 0;
        }

        const mid = Math.floor(sortedValues.length / 2);
        return sortedValues.length % 2 === 0
            ? (sortedValues[mid - 1] + sortedValues[mid]) / 2
            : sortedValues[mid];
    },

    calculateQuantile(sortedValues, quantile) {
        if (!sortedValues || sortedValues.length === 0) {
            return 0;
        }

        const pos = (sortedValues.length - 1) * quantile;
        const base = Math.floor(pos);
        const rest = pos - base;

        if (sortedValues[base + 1] !== undefined) {
            return sortedValues[base] + rest * (sortedValues[base + 1] - sortedValues[base]);
        }

        return sortedValues[base];
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
