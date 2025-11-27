/**
 * Export Manager - Chart and Dashboard Export Functionality
 * Supports PNG, PDF, and multi-page PDF exports using html2canvas and jsPDF
 */

export const ExportManager = {
    /**
     * Export a single chart as PNG
     */
    async exportChartAsPNG(chartElement, filename = 'chart') {
        try {
            // Show loading indicator
            this.showExportLoader('Exporting chart as PNG...');

            // If it's a Chart.js canvas
            if (chartElement.tagName === 'CANVAS') {
                const chart = Chart.getChart(chartElement);
                if (chart) {
                    // Use Chart.js built-in toBase64Image
                    const url = chart.toBase64Image('image/png', 1.0);
                    this.downloadImage(url, `${filename}.png`);
                    this.hideExportLoader();
                    this.showExportSuccess('Chart exported successfully!');
                    return;
                }

                // Fallback: direct canvas export
                const url = chartElement.toDataURL('image/png', 1.0);
                this.downloadImage(url, `${filename}.png`);
                this.hideExportLoader();
                this.showExportSuccess('Chart exported successfully!');
                return;
            }

            // If it's an SVG or container, use html2canvas
            await this.exportElementAsPNG(chartElement, filename);
            this.hideExportLoader();
            this.showExportSuccess('Chart exported successfully!');

        } catch (error) {
            console.error('Export error:', error);
            this.hideExportLoader();
            this.showExportError('Failed to export chart. Please try again.');
        }
    },

    /**
     * Export DOM element as PNG using html2canvas
     */
    async exportElementAsPNG(element, filename = 'export') {
        // Lazy load html2canvas
        if (!window.html2canvas) {
            await this.loadHtml2Canvas();
        }

        const canvas = await html2canvas(element, {
            backgroundColor: getComputedStyle(element).backgroundColor || '#ffffff',
            scale: 2, // Higher quality
            logging: false,
            useCORS: true
        });

        const url = canvas.toDataURL('image/png', 1.0);
        this.downloadImage(url, `${filename}.png`);
    },

    /**
     * Export chart as PDF
     */
    async exportChartAsPDF(chartElement, filename = 'chart') {
        try {
            this.showExportLoader('Exporting chart as PDF...');

            // Lazy load jsPDF
            if (!window.jspdf) {
                await this.loadJsPDF();
            }

            const { jsPDF } = window.jspdf;

            // Get image data
            let imgData;

            if (chartElement.tagName === 'CANVAS') {
                const chart = Chart.getChart(chartElement);
                if (chart) {
                    imgData = chart.toBase64Image('image/png', 1.0);
                } else {
                    imgData = chartElement.toDataURL('image/png', 1.0);
                }
            } else {
                // Use html2canvas for SVG/DOM elements
                if (!window.html2canvas) {
                    await this.loadHtml2Canvas();
                }

                const canvas = await html2canvas(chartElement, {
                    backgroundColor: '#ffffff',
                    scale: 2,
                    logging: false,
                    useCORS: true
                });

                imgData = canvas.toDataURL('image/png', 1.0);
            }

            // Create PDF
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });

            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();

            // Add image to PDF (maintain aspect ratio)
            const margin = 10;
            const maxWidth = pageWidth - 2 * margin;
            const maxHeight = pageHeight - 2 * margin;

            // Calculate dimensions
            const img = new Image();
            img.src = imgData;

            await new Promise(resolve => {
                img.onload = resolve;
            });

            const imgRatio = img.width / img.height;
            let width = maxWidth;
            let height = width / imgRatio;

            if (height > maxHeight) {
                height = maxHeight;
                width = height * imgRatio;
            }

            const x = (pageWidth - width) / 2;
            const y = (pageHeight - height) / 2;

            pdf.addImage(imgData, 'PNG', x, y, width, height);

            // Add title
            pdf.setFontSize(16);
            pdf.setTextColor(3, 45, 96); // Tableau navy
            pdf.text(filename, pageWidth / 2, 8, { align: 'center' });

            // Add timestamp
            pdf.setFontSize(10);
            pdf.setTextColor(107, 114, 128); // Gray
            const timestamp = new Date().toLocaleString();
            pdf.text(`Generated: ${timestamp}`, pageWidth / 2, pageHeight - 5, { align: 'center' });

            pdf.save(`${filename}.pdf`);
            this.hideExportLoader();
            this.showExportSuccess('PDF exported successfully!');

        } catch (error) {
            console.error('Export error:', error);
            this.hideExportLoader();
            this.showExportError('Failed to export PDF. Please try again.');
        }
    },

    /**
     * Export all charts in current tab as multi-page PDF
     */
    async exportAllCharts() {
        try {
            this.showExportLoader('Exporting all charts as PDF...');

            // Lazy load dependencies
            if (!window.jspdf) {
                await this.loadJsPDF();
            }
            if (!window.html2canvas) {
                await this.loadHtml2Canvas();
            }

            const { jsPDF } = window.jspdf;

            // Find active tab
            const activeTab = document.querySelector('.tab-content.active');
            if (!activeTab) {
                throw new Error('No active tab found');
            }

            // Find all charts in active tab
            const chartCards = activeTab.querySelectorAll('.chart-card');
            const charts = [];

            // Collect charts
            for (const card of chartCards) {
                const canvas = card.querySelector('canvas');
                const svg = card.querySelector('svg');
                const chartElement = canvas || svg;

                if (chartElement) {
                    const title = card.querySelector('.chart-title')?.textContent || 'Chart';
                    charts.push({ element: chartElement, title });
                }
            }

            if (charts.length === 0) {
                throw new Error('No charts found in current tab');
            }

            // Create PDF
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });

            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 15;

            // Process each chart
            for (let i = 0; i < charts.length; i++) {
                if (i > 0) {
                    pdf.addPage();
                }

                const { element, title } = charts[i];

                // Get image data
                let imgData;

                if (element.tagName === 'CANVAS') {
                    const chart = Chart.getChart(element);
                    if (chart) {
                        imgData = chart.toBase64Image('image/png', 1.0);
                    } else {
                        imgData = element.toDataURL('image/png', 1.0);
                    }
                } else {
                    const canvas = await html2canvas(element, {
                        backgroundColor: '#ffffff',
                        scale: 2,
                        logging: false,
                        useCORS: true
                    });
                    imgData = canvas.toDataURL('image/png', 1.0);
                }

                // Add title
                pdf.setFontSize(18);
                pdf.setTextColor(3, 45, 96);
                pdf.text(title, pageWidth / 2, margin, { align: 'center' });

                // Add image
                const maxWidth = pageWidth - 2 * margin;
                const maxHeight = pageHeight - 3 * margin - 10;

                const img = new Image();
                img.src = imgData;

                await new Promise(resolve => {
                    img.onload = resolve;
                });

                const imgRatio = img.width / img.height;
                let width = maxWidth;
                let height = width / imgRatio;

                if (height > maxHeight) {
                    height = maxHeight;
                    width = height * imgRatio;
                }

                const x = (pageWidth - width) / 2;
                const y = margin + 10;

                pdf.addImage(imgData, 'PNG', x, y, width, height);

                // Add page number
                pdf.setFontSize(10);
                pdf.setTextColor(107, 114, 128);
                pdf.text(`Page ${i + 1} of ${charts.length}`, pageWidth / 2, pageHeight - 5, { align: 'center' });
            }

            // Add cover page at the beginning
            pdf.insertPage(1);
            pdf.setPage(1);

            // Cover page design
            pdf.setFontSize(28);
            pdf.setTextColor(3, 45, 96);
            pdf.text('Somali Dialect Classifier', pageWidth / 2, 50, { align: 'center' });

            pdf.setFontSize(20);
            pdf.text('Data Ingestion Dashboard', pageWidth / 2, 65, { align: 'center' });

            pdf.setFontSize(14);
            pdf.setTextColor(107, 114, 128);
            const tabTitle = activeTab.querySelector('.section-title')?.textContent || 'Charts';
            pdf.text(tabTitle, pageWidth / 2, 80, { align: 'center' });

            pdf.setFontSize(12);
            const timestamp = new Date().toLocaleString();
            pdf.text(`Generated: ${timestamp}`, pageWidth / 2, pageHeight / 2, { align: 'center' });

            pdf.text(`Total Charts: ${charts.length}`, pageWidth / 2, pageHeight / 2 + 10, { align: 'center' });

            // Save PDF
            const tabName = tabTitle.toLowerCase().replace(/\s+/g, '-');
            pdf.save(`somali-dialect-dashboard-${tabName}-${Date.now()}.pdf`);

            this.hideExportLoader();
            this.showExportSuccess(`Successfully exported ${charts.length} charts as PDF!`);

        } catch (error) {
            console.error('Export all error:', error);
            this.hideExportLoader();
            this.showExportError('Failed to export all charts. Please try again.');
        }
    },

    /**
     * Show export modal
     */
    showExportModal(chartElement, chartTitle = 'Chart') {
        // Create modal if it doesn't exist
        let modal = document.getElementById('export-modal');

        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'export-modal';
            modal.className = 'export-modal';
            modal.innerHTML = `
                <div class="export-modal-overlay"></div>
                <div class="export-modal-content">
                    <div class="export-modal-header">
                        <h3>Export Chart</h3>
                        <button class="export-modal-close" aria-label="Close">&times;</button>
                    </div>
                    <div class="export-modal-body">
                        <p>Choose export format:</p>
                        <div class="export-options">
                            <button class="export-option-btn" data-format="png">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                    <polyline points="21 15 16 10 5 21"></polyline>
                                </svg>
                                <span>PNG Image</span>
                                <small>High quality raster image</small>
                            </button>
                            <button class="export-option-btn" data-format="pdf">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                    <line x1="16" y1="13" x2="8" y2="13"></line>
                                    <line x1="16" y1="17" x2="8" y2="17"></line>
                                    <polyline points="10 9 9 9 8 9"></polyline>
                                </svg>
                                <span>PDF Document</span>
                                <small>Printable document format</small>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Close handlers
            const closeBtn = modal.querySelector('.export-modal-close');
            const overlay = modal.querySelector('.export-modal-overlay');

            closeBtn.addEventListener('click', () => this.hideExportModal());
            overlay.addEventListener('click', () => this.hideExportModal());

            // Format buttons
            const formatBtns = modal.querySelectorAll('.export-option-btn');
            formatBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const format = btn.dataset.format;
                    const element = modal.dataset.chartElement ? document.querySelector(modal.dataset.chartSelector) : null;
                    const title = modal.dataset.chartTitle || 'chart';

                    this.hideExportModal();

                    if (element) {
                        if (format === 'png') {
                            this.exportChartAsPNG(element, title);
                        } else if (format === 'pdf') {
                            this.exportChartAsPDF(element, title);
                        }
                    }
                });
            });
        }

        // Store chart reference
        modal.dataset.chartTitle = chartTitle;
        modal.dataset.chartElement = chartElement.id || 'chart';
        modal.dataset.chartSelector = chartElement.id ? `#${chartElement.id}` : '.chart-canvas canvas';

        // Show modal
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    },

    /**
     * Hide export modal
     */
    hideExportModal() {
        const modal = document.getElementById('export-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    /**
     * Show export loader
     */
    showExportLoader(message = 'Exporting...') {
        let loader = document.getElementById('export-loader');

        if (!loader) {
            loader = document.createElement('div');
            loader.id = 'export-loader';
            loader.className = 'export-loader';
            loader.innerHTML = `
                <div class="export-loader-content">
                    <div class="export-loader-spinner"></div>
                    <p class="export-loader-message">${message}</p>
                </div>
            `;
            document.body.appendChild(loader);
        } else {
            loader.querySelector('.export-loader-message').textContent = message;
        }

        loader.classList.add('active');
    },

    /**
     * Hide export loader
     */
    hideExportLoader() {
        const loader = document.getElementById('export-loader');
        if (loader) {
            loader.classList.remove('active');
        }
    },

    /**
     * Show export success message
     */
    showExportSuccess(message) {
        this.showToast(message, 'success');
    },

    /**
     * Show export error message
     */
    showExportError(message) {
        this.showToast(message, 'error');
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `export-toast export-toast-${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        // Show toast
        setTimeout(() => {
            toast.classList.add('active');
        }, 10);

        // Hide and remove toast
        setTimeout(() => {
            toast.classList.remove('active');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    },

    /**
     * Download image from data URL
     */
    downloadImage(dataUrl, filename) {
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = filename;
        link.click();
    },

    /**
     * Lazy load html2canvas library
     */
    async loadHtml2Canvas() {
        if (window.html2canvas) return;

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    },

    /**
     * Lazy load jsPDF library
     */
    async loadJsPDF() {
        if (window.jspdf) return;

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
};
