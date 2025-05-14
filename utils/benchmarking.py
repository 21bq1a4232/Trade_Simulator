"""
Benchmarking utilities for performance measurement.
"""
import time
import threading
from contextlib import contextmanager
from collections import defaultdict, deque

class Benchmarker:
    """
    Utility for measuring and tracking performance metrics.
    Provides timing functions for various operations.
    """
    
    def __init__(self, max_history=1000):
        """
        Initialize the benchmarker.
        
        Args:
            max_history (int): Maximum number of timing samples to keep
        """
        self.max_history = max_history
        self.timings = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "history": deque(maxlen=max_history),
            "last_time": 0.0
        })
        
        self.start_time = None
        self.is_running = False
        self.lock = threading.Lock()
    
    def start(self):
        """Start the benchmarker."""
        self.start_time = time.time()
        self.is_running = True
    
    def stop(self):
        """Stop the benchmarker."""
        self.is_running = False
    
    @contextmanager
    def measure(self, label):
        """
        Context manager for measuring the execution time of a block of code.
        
        Args:
            label (str): Label for the timing measurement
        
        Example:
            ```
            with benchmarker.measure("my_operation"):
                # Code to measure
                result = do_something()
            ```
        """
        if not self.is_running:
            yield
            return
        
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self._record_timing(label, elapsed_time)
    
    def _record_timing(self, label, elapsed_time):
        """
        Record a timing measurement.
        
        Args:
            label (str): Label for the measurement
            elapsed_time (float): Elapsed time in seconds
        """
        with self.lock:
            timing = self.timings[label]
            
            # Update timing statistics
            timing["count"] += 1
            timing["total_time"] += elapsed_time
            timing["min_time"] = min(timing["min_time"], elapsed_time)
            timing["max_time"] = max(timing["max_time"], elapsed_time)
            timing["last_time"] = elapsed_time
            
            # Add to history
            timing["history"].append(elapsed_time)
    
    def get_results(self):
        """
        Get all benchmark results.
        
        Returns:
            dict: Benchmark results by label
        """
        with self.lock:
            results = {}
            
            for label, timing in self.timings.items():
                # Calculate statistics
                count = timing["count"]
                
                if count > 0:
                    avg_time = timing["total_time"] / count
                    
                    # Calculate percentiles if we have enough samples
                    history = list(timing["history"])
                    if history:
                        sorted_history = sorted(history)
                        p50 = sorted_history[len(sorted_history) // 2]
                        p90 = sorted_history[int(len(sorted_history) * 0.9)]
                        p99 = sorted_history[int(len(sorted_history) * 0.99)]
                    else:
                        p50 = p90 = p99 = 0.0
                    
                    results[label] = {
                        "count": count,
                        "avg_ms": avg_time * 1000,
                        "min_ms": timing["min_time"] * 1000,
                        "max_ms": timing["max_time"] * 1000,
                        "last_ms": timing["last_time"] * 1000,
                        "p50_ms": p50 * 1000,
                        "p90_ms": p90 * 1000,
                        "p99_ms": p99 * 1000
                    }
            
            # Add total runtime
            if self.start_time:
                total_runtime = time.time() - self.start_time
                results["total_runtime"] = {
                    "seconds": total_runtime,
                    "minutes": total_runtime / 60
                }
            
            return results
    
    def reset(self):
        """Reset all benchmark measurements."""
        with self.lock:
            self.timings.clear()
            self.start_time = time.time()