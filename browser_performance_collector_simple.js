/**
 * Simplified Browser Performance Collector
 * 
 * Step-by-step usage:
 * 1. Open DevTools (F12) -> Console tab
 * 2. Copy ALL code below (from // START to // END)
 * 3. Paste into console and press Enter
 * 4. You should see: "[PERF] Performance monitoring started..."
 * 5. Refresh the page
 * 6. After page loads, type: collectPerformanceMetrics()
 * 7. Press Enter
 */

// START - Copy everything from here
(function() {
    'use strict';
    
    const metrics = {
        startTime: performance.now(),
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
    
    // Monitor DOM mutations
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
    
    // Collect network timing
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
    
    // Main function - MUST be exposed to window
    function collectPerformanceMetrics() {
        collectNetworkTimings();
        
        const summary = {
            timestamp: new Date().toISOString(),
            url: window.location.href,
            totalTime: performance.now() - metrics.startTime,
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
        
        if (summary.apiCalls.length > 0) {
            console.log('\nAPI Calls Details:');
            summary.apiCalls.forEach((call, i) => {
                console.log(`  ${i+1}. ${call.url}`);
                console.log(`     Duration: ${call.duration.toFixed(2)}ms, Status: ${call.status}`);
                if (call.dataSize) {
                    console.log(`     Size: ${call.dataSize} bytes, Items: ${call.itemCount}`);
                }
            });
        }
        
        if (summary.networkTimings.length > 0) {
            console.log('\nNetwork Timings:');
            summary.networkTimings.forEach((timing, i) => {
                console.log(`  ${i+1}. ${timing.url}`);
                console.log(`     Total: ${timing.duration.toFixed(2)}ms`);
                console.log(`     DNS: ${timing.dns.toFixed(2)}ms, Connect: ${timing.connect.toFixed(2)}ms`);
                console.log(`     Request: ${timing.request.toFixed(2)}ms, Response: ${timing.response.toFixed(2)}ms`);
            });
        }
        
        console.log('='.repeat(70));
        
        // Try to copy to clipboard
        try {
            const jsonStr = JSON.stringify(summary, null, 2);
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(jsonStr).then(() => {
                    console.log('\n[SUCCESS] Metrics copied to clipboard!');
                }).catch(() => {
                    console.log('\n[METRICS JSON]');
                    console.log(jsonStr);
                });
            } else {
                console.log('\n[METRICS JSON]');
                console.log(jsonStr);
            }
        } catch (e) {
            console.log('\n[METRICS JSON]');
            console.log(JSON.stringify(summary, null, 2));
        }
        
        return summary;
    }
    
    // CRITICAL: Expose to window object
    window.collectPerformanceMetrics = collectPerformanceMetrics;
    
    // Start monitoring
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('[PERF] ✅ Performance monitoring started!');
    console.log('[PERF] ✅ Function available: collectPerformanceMetrics()');
    console.log('[PERF] 📝 Next: Refresh page, then run: collectPerformanceMetrics()');
    
})();
// END - Copy everything to here

