/**
 * Browser Performance Collector
 * 
 * Add this script to your browser console to collect detailed performance metrics.
 * 
 * Usage:
 *   1. Open browser DevTools (F12)
 *   2. Go to Console tab
 *   3. Copy and paste this entire script
 *   4. Press Enter
 *   5. Reload the page or trigger the loading
 *   6. Run: collectPerformanceMetrics()
 * 
 * This will collect:
 * - API call timings
 * - Rendering timings
 * - Network waterfall
 * - Resource loading times
 */

(function() {
    'use strict';
    
    const metrics = {
        startTime: null,
        apiCalls: [],
        renderEvents: [],
        networkTimings: [],
        errors: []
    };
    
    // Intercept fetch calls
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        const startTime = performance.now();
        
        console.log(`[PERF] Fetch started: ${url}`);
        
        return originalFetch.apply(this, args)
            .then(response => {
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                const callInfo = {
                    url: url,
                    method: 'GET',
                    startTime: startTime,
                    endTime: endTime,
                    duration: duration,
                    status: response.status,
                    ok: response.ok
                };
                
                metrics.apiCalls.push(callInfo);
                console.log(`[PERF] Fetch completed: ${url} - ${duration.toFixed(2)}ms (status: ${response.status})`);
                
                // Clone response to read body without consuming it
                const clonedResponse = response.clone();
                clonedResponse.json().then(data => {
                    callInfo.dataSize = JSON.stringify(data).length;
                    callInfo.itemCount = (data.news || []).length + (data.trades || []).length;
                    console.log(`[PERF] Response size: ${callInfo.dataSize} bytes, items: ${callInfo.itemCount}`);
                }).catch(() => {});
                
                return response;
            })
            .catch(error => {
                const endTime = performance.now();
                metrics.errors.push({
                    url: url,
                    error: error.message,
                    time: endTime
                });
                console.error(`[PERF] Fetch error: ${url} - ${error.message}`);
                throw error;
            });
    };
    
    // Monitor DOM mutations (rendering)
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                metrics.renderEvents.push({
                    time: performance.now(),
                    type: 'DOM_INSERT',
                    nodeCount: mutation.addedNodes.length
                });
            }
        });
    });
    
    // Monitor performance marks
    const originalMark = performance.mark;
    performance.mark = function(name) {
        metrics.renderEvents.push({
            time: performance.now(),
            type: 'MARK',
            name: name
        });
        return originalMark.apply(this, arguments);
    };
    
    // Collect network timing from Performance API
    function collectNetworkTimings() {
        const entries = performance.getEntriesByType('resource');
        entries.forEach(entry => {
            if (entry.name.includes('/merged-items') || entry.name.includes('/api/')) {
                metrics.networkTimings.push({
                    url: entry.name,
                    duration: entry.duration,
                    dns: entry.domainLookupEnd - entry.domainLookupStart,
                    connect: entry.connectEnd - entry.connectStart,
                    request: entry.responseStart - entry.requestStart,
                    response: entry.responseEnd - entry.responseStart,
                    transfer: entry.transferSize || 0,
                    decoded: entry.decodedBodySize || 0
                });
            }
        });
    }
    
    // Main collection function - ensure it's globally accessible
    function collectPerformanceMetrics() {
        collectNetworkTimings();
        
        const summary = {
            timestamp: new Date().toISOString(),
            url: window.location.href,
            totalTime: performance.now() - (metrics.startTime || 0),
            apiCalls: metrics.apiCalls,
            networkTimings: metrics.networkTimings,
            renderEvents: metrics.renderEvents,
            errors: metrics.errors,
            analysis: {
                totalApiCalls: metrics.apiCalls.length,
                totalApiTime: metrics.apiCalls.reduce((sum, call) => sum + call.duration, 0),
                averageApiTime: metrics.apiCalls.length > 0 
                    ? metrics.apiCalls.reduce((sum, call) => sum + call.duration, 0) / metrics.apiCalls.length 
                    : 0,
                longestApiCall: metrics.apiCalls.length > 0
                    ? metrics.apiCalls.reduce((max, call) => call.duration > max ? call.duration : max, 0)
                    : 0,
                totalRenderEvents: metrics.renderEvents.length,
                totalErrors: metrics.errors.length
            }
        };
        
        console.log('\n' + '='.repeat(70));
        console.log('PERFORMANCE METRICS SUMMARY');
        console.log('='.repeat(70));
        console.log(`Total API Calls: ${summary.analysis.totalApiCalls}`);
        console.log(`Total API Time: ${summary.analysis.totalApiTime.toFixed(2)}ms`);
        console.log(`Average API Time: ${summary.analysis.averageApiTime.toFixed(2)}ms`);
        console.log(`Longest API Call: ${summary.analysis.longestApiTime.toFixed(2)}ms`);
        console.log(`Total Render Events: ${summary.analysis.totalRenderEvents}`);
        console.log(`Errors: ${summary.analysis.totalErrors}`);
        
        console.log('\nAPI Calls Details:');
        summary.apiCalls.forEach((call, i) => {
            console.log(`  ${i+1}. ${call.url}`);
            console.log(`     Duration: ${call.duration.toFixed(2)}ms, Status: ${call.status}`);
            if (call.dataSize) {
                console.log(`     Size: ${call.dataSize} bytes, Items: ${call.itemCount}`);
            }
        });
        
        console.log('\nNetwork Timings:');
        summary.networkTimings.forEach((timing, i) => {
            console.log(`  ${i+1}. ${timing.url}`);
            console.log(`     Total: ${timing.duration.toFixed(2)}ms`);
            console.log(`     DNS: ${timing.dns.toFixed(2)}ms, Connect: ${timing.connect.toFixed(2)}ms`);
            console.log(`     Request: ${timing.request.toFixed(2)}ms, Response: ${timing.response.toFixed(2)}ms`);
        });
        
        console.log('='.repeat(70));
        
        // Copy to clipboard (if possible)
        try {
            const jsonStr = JSON.stringify(summary, null, 2);
            navigator.clipboard.writeText(jsonStr).then(() => {
                console.log('\n[SUCCESS] Metrics copied to clipboard!');
            }).catch(() => {
                console.log('\n[METRICS JSON]');
                console.log(jsonStr);
            });
        } catch (e) {
            console.log('\n[METRICS JSON]');
            console.log(JSON.stringify(summary, null, 2));
        }
        
        return summary;
    }
    
    // Expose function globally
    window.collectPerformanceMetrics = collectPerformanceMetrics;
    
    // Start monitoring
    metrics.startTime = performance.now();
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('[PERF] Performance monitoring started. Reload page and run collectPerformanceMetrics() when done.');
    console.log('[PERF] Function available: typeof collectPerformanceMetrics =', typeof collectPerformanceMetrics);
    
})();

