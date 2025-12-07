"""
Diagnostic tool to identify performance bottlenecks in deployed version.

This script helps identify why the deployed version shows "loading news and trades"
for a long time despite API optimizations.

Usage:
    python diagnose_performance.py --url https://finx.ai-builders.space/
"""

import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime
import argparse


class PerformanceDiagnostic:
    """Diagnoses performance issues in deployed version."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[Dict] = []
    
    async def measure_endpoint_detailed(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Measure endpoint with detailed timing breakdown."""
        timings = {}
        
        # DNS lookup time (approximate)
        dns_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # First request - includes DNS lookup
                first_start = time.time()
                async with session.get(f"{self.base_url}{endpoint}", params=params) as response:
                    first_connect = time.time()
                    data = await response.json()
                    first_complete = time.time()
                    
                    # Second request - DNS cached
                    second_start = time.time()
                    async with session.get(f"{self.base_url}{endpoint}", params=params) as response2:
                        second_connect = time.time()
                        data2 = await response2.json()
                        second_complete = time.time()
                    
                    return {
                        "endpoint": endpoint,
                        "params": params,
                        "status": response.status,
                        "first_request": {
                            "total_ms": (first_complete - first_start) * 1000,
                            "connect_ms": (first_connect - first_start) * 1000,
                            "transfer_ms": (first_complete - first_connect) * 1000,
                        },
                        "second_request": {
                            "total_ms": (second_complete - second_start) * 1000,
                            "connect_ms": (second_connect - second_start) * 1000,
                            "transfer_ms": (second_complete - second_connect) * 1000,
                        },
                        "dns_overhead_ms": ((first_connect - first_start) - (second_connect - second_start)) * 1000,
                        "data_size_bytes": len(json.dumps(data).encode('utf-8')),
                        "item_count": len(data.get("news", [])) + len(data.get("trades", []))
                    }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "params": params,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def test_full_loading_flow(self) -> Dict:
        """Test the full loading flow that user experiences."""
        print("[DIAGNOSTIC] Testing full loading flow...")
        
        results = {}
        
        # 1. Test optimized endpoint (what frontend should use)
        print("  [1/3] Testing optimized /merged-items endpoint...")
        optimized = await self.measure_endpoint_detailed(
            "/merged-items",
            {
                "limit": 10,
                "offset": 0,
                "item_type": "all",
                "include_liked_status": "true",
                "include_thoughts": "true"
            }
        )
        results["optimized_endpoint"] = optimized
        
        # 2. Test database query performance (if we can access it)
        print("  [2/3] Testing database query performance...")
        # We can't directly test DB, but we can infer from response time
        
        # 3. Test network latency
        print("  [3/3] Testing network latency...")
        latency_results = []
        for i in range(5):
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/favicon.ico") as response:
                    await response.read()
            latency = (time.time() - start) * 1000
            latency_results.append(latency)
        
        results["network_latency"] = {
            "average_ms": sum(latency_results) / len(latency_results),
            "min_ms": min(latency_results),
            "max_ms": max(latency_results),
            "measurements": latency_results
        }
        
        # Analyze results
        if "error" not in optimized:
            total_time = optimized["first_request"]["total_ms"]
            connect_time = optimized["first_request"]["connect_ms"]
            transfer_time = optimized["first_request"]["transfer_ms"]
            
            results["analysis"] = {
                "total_time_ms": total_time,
                "connect_time_ms": connect_time,
                "transfer_time_ms": transfer_time,
                "server_processing_ms": total_time - connect_time - transfer_time,
                "bottleneck": self._identify_bottleneck(total_time, connect_time, transfer_time, optimized.get("data_size_bytes", 0))
            }
        
        return results
    
    def _identify_bottleneck(self, total: float, connect: float, transfer: float, data_size: int) -> str:
        """Identify the main bottleneck."""
        if connect > total * 0.5:
            return "Network latency / DNS lookup"
        elif transfer > total * 0.5:
            return "Data transfer (large response size)"
        elif (total - connect - transfer) > total * 0.5:
            return "Server processing (database query)"
        else:
            return "Multiple factors"
    
    def print_diagnosis(self, results: Dict):
        """Print formatted diagnosis."""
        print("\n" + "="*70)
        print("PERFORMANCE DIAGNOSIS")
        print("="*70)
        
        if "error" in results.get("optimized_endpoint", {}):
            print(f"\n❌ ERROR: {results['optimized_endpoint']['error']}")
            return
        
        opt = results["optimized_endpoint"]
        latency = results["network_latency"]
        analysis = results.get("analysis", {})
        
        print(f"\n📊 Endpoint Performance:")
        print(f"   First Request: {opt['first_request']['total_ms']:.2f}ms")
        print(f"     - Connect: {opt['first_request']['connect_ms']:.2f}ms")
        print(f"     - Transfer: {opt['first_request']['transfer_ms']:.2f}ms")
        print(f"   Second Request: {opt['second_request']['total_ms']:.2f}ms (cached DNS)")
        print(f"   Data Size: {opt['data_size_bytes']:,} bytes ({opt['data_size_bytes']/1024:.2f} KB)")
        print(f"   Items Returned: {opt['item_count']}")
        
        print(f"\n🌐 Network Latency:")
        print(f"   Average: {latency['average_ms']:.2f}ms")
        print(f"   Range: {latency['min_ms']:.2f}ms - {latency['max_ms']:.2f}ms")
        
        if analysis:
            print(f"\n🔍 Analysis:")
            print(f"   Total Time: {analysis['total_time_ms']:.2f}ms")
            print(f"   Server Processing: {analysis['server_processing_ms']:.2f}ms")
            print(f"   Main Bottleneck: {analysis['bottleneck']}")
            
            # Recommendations
            print(f"\n💡 Recommendations:")
            if analysis['bottleneck'] == "Network latency / DNS lookup":
                print("   - Consider using CDN or edge caching")
                print("   - Check DNS resolution time")
            elif analysis['bottleneck'] == "Data transfer (large response size)":
                print("   - Enable response compression (gzip)")
                print("   - Consider pagination or lazy loading")
            elif analysis['bottleneck'] == "Server processing (database query)":
                print("   - Check database indexes")
                print("   - Consider adding Redis cache")
                print("   - Optimize database queries")
            else:
                print("   - Multiple optimizations needed")
                print("   - Check server logs for detailed timing")
        
        print("="*70)
    
    async def check_frontend_behavior(self) -> Dict:
        """Check what the frontend actually does."""
        print("\n[DIAGNOSTIC] Checking frontend behavior...")
        
        # Fetch the HTML to see what API calls it makes
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/") as response:
                html = await response.text()
        
        # Check if HTML contains the optimized API call
        has_optimized_call = 'include_liked_status=true' in html or 'include_liked_status=true' in html
        
        return {
            "html_size_bytes": len(html.encode('utf-8')),
            "has_optimized_api_call": has_optimized_call,
            "check_manually": "Open browser DevTools Network tab to see actual API calls"
        }


async def main():
    parser = argparse.ArgumentParser(description="Diagnose performance issues")
    parser.add_argument("--url", default="https://finx.ai-builders.space/", help="Base URL")
    parser.add_argument("--save", help="Save results to file")
    
    args = parser.parse_args()
    
    diagnostic = PerformanceDiagnostic(base_url=args.url.rstrip('/'))
    
    # Run diagnostics
    flow_results = await diagnostic.test_full_loading_flow()
    frontend_check = await diagnostic.check_frontend_behavior()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "url": args.url,
        "loading_flow": flow_results,
        "frontend_check": frontend_check
    }
    
    diagnostic.print_diagnosis(flow_results)
    
    print(f"\n📱 Frontend Check:")
    print(f"   HTML Size: {frontend_check['html_size_bytes']:,} bytes")
    print(f"   Has Optimized Call: {frontend_check['has_optimized_api_call']}")
    print(f"   {frontend_check['check_manually']}")
    
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVED] Results saved to {args.save}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Diagnostic cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

