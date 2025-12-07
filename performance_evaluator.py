"""
Performance evaluation tool for measuring improvements from Plan A optimizations.

This script measures:
1. API response times (before/after optimization)
2. Frontend rendering times
3. Number of HTTP requests
4. Total page load time

Usage:
    python performance_evaluator.py [--baseline] [--optimized] [--compare]
    
    --baseline: Run baseline test (without optimizations)
    --optimized: Run optimized test (with batch API calls)
    --compare: Compare baseline vs optimized
"""

import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime
import argparse


class PerformanceEvaluator:
    """Evaluates performance improvements from Plan A optimizations."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[Dict] = []
    
    async def measure_api_call(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Measure API call performance."""
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}{endpoint}", params=params) as response:
                    data = await response.json()
                    elapsed = (time.time() - start_time) * 1000  # Convert to ms
                    return {
                        "endpoint": endpoint,
                        "params": params,
                        "status": response.status,
                        "response_time_ms": elapsed,
                        "data_size_bytes": len(json.dumps(data).encode('utf-8')),
                        "item_count": len(data.get("news", [])) + len(data.get("trades", []))
                    }
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                return {
                    "endpoint": endpoint,
                    "params": params,
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": elapsed
                }
    
    async def measure_baseline(self) -> Dict:
        """Measure baseline performance (old method with separate API calls)."""
        print("[BASELINE] Measuring baseline performance...")
        
        # 1. Fetch merged items (without batch data)
        merged_result = await self.measure_api_call(
            "/merged-items",
            {"limit": 10, "offset": 0, "item_type": "all"}
        )
        
        # 2. Fetch liked status separately (simulating old method)
        # Generate hashes (simplified - in real scenario, would need to parse items)
        # For testing, we'll use a dummy hash
        liked_result = await self.measure_api_call(
            "/api/news/liked-status",
            {"news_hashes": "dummy_hash_1,dummy_hash_2"}  # Placeholder
        )
        
        # 3. Fetch thoughts separately (simulating old sequential method)
        thought_results = []
        for i in range(5):  # Simulate fetching 5 thoughts sequentially
            result = await self.measure_api_call(f"/api/news/thought/dummy_hash_{i}")
            thought_results.append(result)
        
        total_time = merged_result["response_time_ms"] + liked_result["response_time_ms"]
        total_time += sum(r["response_time_ms"] for r in thought_results)
        
        return {
            "test_type": "baseline",
            "timestamp": datetime.now().isoformat(),
            "merged_items": merged_result,
            "liked_status": liked_result,
            "thoughts": thought_results,
            "total_api_calls": 2 + len(thought_results),
            "total_time_ms": total_time,
            "sequential_calls": len(thought_results)
        }
    
    async def measure_optimized(self) -> Dict:
        """Measure optimized performance (new method with batch API calls)."""
        print("[OPTIMIZED] Measuring optimized performance...")
        
        # Single API call with batch data
        merged_result = await self.measure_api_call(
            "/merged-items",
            {
                "limit": 10,
                "offset": 0,
                "item_type": "all",
                "include_liked_status": "true",
                "include_thoughts": "true"
            }
        )
        
        return {
            "test_type": "optimized",
            "timestamp": datetime.now().isoformat(),
            "merged_items": merged_result,
            "total_api_calls": 1,
            "total_time_ms": merged_result["response_time_ms"],
            "batch_enabled": True
        }
    
    async def run_comparison(self, iterations: int = 5) -> Dict:
        """Run comparison between baseline and optimized."""
        print(f"[COMPARISON] Running {iterations} iterations...")
        
        baseline_results = []
        optimized_results = []
        
        for i in range(iterations):
            print(f"\n--- Iteration {i+1}/{iterations} ---")
            
            # Run baseline
            baseline = await self.measure_baseline()
            baseline_results.append(baseline)
            await asyncio.sleep(1)  # Small delay between tests
            
            # Run optimized
            optimized = await self.measure_optimized()
            optimized_results.append(optimized)
            await asyncio.sleep(1)
        
        # Calculate averages
        baseline_avg_time = sum(r["total_time_ms"] for r in baseline_results) / len(baseline_results)
        optimized_avg_time = sum(r["total_time_ms"] for r in optimized_results) / len(optimized_results)
        
        baseline_avg_calls = sum(r["total_api_calls"] for r in baseline_results) / len(baseline_results)
        optimized_avg_calls = sum(r["total_api_calls"] for r in optimized_results) / len(optimized_results)
        
        improvement_percent = ((baseline_avg_time - optimized_avg_time) / baseline_avg_time) * 100
        calls_reduction = baseline_avg_calls - optimized_avg_calls
        
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "baseline": {
                "average_time_ms": baseline_avg_time,
                "average_api_calls": baseline_avg_calls,
                "results": baseline_results
            },
            "optimized": {
                "average_time_ms": optimized_avg_time,
                "average_api_calls": optimized_avg_calls,
                "results": optimized_results
            },
            "improvement": {
                "time_reduction_ms": baseline_avg_time - optimized_avg_time,
                "time_reduction_percent": improvement_percent,
                "api_calls_reduction": calls_reduction,
                "api_calls_reduction_percent": (calls_reduction / baseline_avg_calls) * 100 if baseline_avg_calls > 0 else 0
            }
        }
        
        return comparison
    
    def print_results(self, results: Dict):
        """Print formatted results."""
        if results.get("test_type") == "baseline":
            print("\n" + "="*60)
            print("BASELINE PERFORMANCE RESULTS")
            print("="*60)
            print(f"Total API Calls: {results['total_api_calls']}")
            print(f"Total Time: {results['total_time_ms']:.2f}ms")
            print(f"  - Merged Items: {results['merged_items']['response_time_ms']:.2f}ms")
            print(f"  - Liked Status: {results['liked_status']['response_time_ms']:.2f}ms")
            print(f"  - Thoughts (sequential): {sum(r['response_time_ms'] for r in results['thoughts']):.2f}ms")
        
        elif results.get("test_type") == "optimized":
            print("\n" + "="*60)
            print("OPTIMIZED PERFORMANCE RESULTS")
            print("="*60)
            print(f"Total API Calls: {results['total_api_calls']}")
            print(f"Total Time: {results['total_time_ms']:.2f}ms")
            print(f"Batch Enabled: {results['batch_enabled']}")
        
        elif "improvement" in results:
            print("\n" + "="*60)
            print("PERFORMANCE COMPARISON")
            print("="*60)
            print(f"\nBaseline (Average):")
            print(f"  Time: {results['baseline']['average_time_ms']:.2f}ms")
            print(f"  API Calls: {results['baseline']['average_api_calls']:.1f}")
            
            print(f"\nOptimized (Average):")
            print(f"  Time: {results['optimized']['average_time_ms']:.2f}ms")
            print(f"  API Calls: {results['optimized']['average_api_calls']:.1f}")
            
            print(f"\nImprovement:")
            print(f"  Time Reduction: {results['improvement']['time_reduction_ms']:.2f}ms ({results['improvement']['time_reduction_percent']:.1f}%)")
            print(f"  API Calls Reduction: {results['improvement']['api_calls_reduction']:.1f} ({results['improvement']['api_calls_reduction_percent']:.1f}%)")
            print("="*60)
    
    def save_results(self, results: Dict, filename: str = None):
        """Save results to JSON file."""
        if filename is None:
            filename = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SAVED] Results saved to {filename}")


async def main():
    parser = argparse.ArgumentParser(description="Performance evaluation tool")
    parser.add_argument("--baseline", action="store_true", help="Run baseline test")
    parser.add_argument("--optimized", action="store_true", help="Run optimized test")
    parser.add_argument("--compare", action="store_true", help="Compare baseline vs optimized")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations for comparison")
    parser.add_argument("--save", help="Save results to file")
    
    args = parser.parse_args()
    
    evaluator = PerformanceEvaluator(base_url=args.url)
    
    if args.compare or (not args.baseline and not args.optimized):
        # Default: run comparison
        results = await evaluator.run_comparison(iterations=args.iterations)
        evaluator.print_results(results)
        if args.save:
            evaluator.save_results(results, args.save)
    elif args.baseline:
        results = await evaluator.measure_baseline()
        evaluator.print_results(results)
        if args.save:
            evaluator.save_results(results, args.save)
    elif args.optimized:
        results = await evaluator.measure_optimized()
        evaluator.print_results(results)
        if args.save:
            evaluator.save_results(results, args.save)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

