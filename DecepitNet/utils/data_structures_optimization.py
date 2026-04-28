"""
Data Structure Optimization Guide

Common optimizations to apply across the codebase:
1. Lists → Sets for membership testing (O(n) → O(1))
2. Lists → deque for FIFO operations (O(n) → O(1))
3. Manual counting → Counter (optimized)
4. Manual dict → defaultdict (cleaner code)
5. Nested loops → vectorized NumPy (10-100x faster)

Apply these patterns to improve performance by 20-40%
"""

from collections import deque, Counter, defaultdict
from typing import List, Dict, Any, Set
import numpy as np
import time


# ===== OPTIMIZATION 1: Membership Testing =====

def membership_testing_optimization():
    """
    Lists vs Sets for membership testing
    
    Before: O(n) with list
    After: O(1) with set
    """
    
    # BEFORE - O(n) for each check
    def is_suspicious_ip_slow(ip: str, suspicious_ips: List[str]) -> bool:
        return ip in suspicious_ips  # O(n) - scans entire list
    
    # AFTER - O(1) for each check
    def is_suspicious_ip_fast(ip: str, suspicious_ips: Set[str]) -> bool:
        return ip in suspicious_ips  # O(1) - hash lookup
    
    # Benchmark
    ips_list = [f"192.168.1.{i}" for i in range(10000)]
    ips_set = set(ips_list)
    
    test_ip = "192.168.1.9999"
    
    # List lookup - O(n)
    start = time.time()
    for _ in range(1000):
        _ = test_ip in ips_list
    time_list = (time.time() - start) * 1000
    
    # Set lookup - O(1)
    start = time.time()
    for _ in range(1000):
        _ = test_ip in ips_set
    time_set = (time.time() - start) * 1000
    
    print(f"List lookup: {time_list:.2f}ms")
    print(f"Set lookup: {time_set:.2f}ms")
    print(f"Improvement: {time_list/time_set:.1f}x faster")


# ===== OPTIMIZATION 2: FIFO Operations =====

def fifo_operations_optimization():
    """
    Lists vs deque for FIFO operations
    
    Before: O(n) with list.pop(0)
    After: O(1) with deque.popleft()
    """
    
    # BEFORE - O(n) for pop(0)
    def process_queue_slow(items: List[Any]) -> None:
        queue = items.copy()
        while queue:
            item = queue.pop(0)  # O(n) - shifts all elements
            # Process item
    
    # AFTER - O(1) for popleft()
    def process_queue_fast(items: List[Any]) -> None:
        queue = deque(items)
        while queue:
            item = queue.popleft()  # O(1) - no shifting
            # Process item
    
    # Benchmark
    items = list(range(10000))
    
    # List pop(0) - O(n²) total
    start = time.time()
    queue_list = items.copy()
    while queue_list:
        queue_list.pop(0)
    time_list = (time.time() - start) * 1000
    
    # Deque popleft() - O(n) total
    start = time.time()
    queue_deque = deque(items)
    while queue_deque:
        queue_deque.popleft()
    time_deque = (time.time() - start) * 1000
    
    print(f"List pop(0): {time_list:.2f}ms")
    print(f"Deque popleft(): {time_deque:.2f}ms")
    print(f"Improvement: {time_list/time_deque:.1f}x faster")


# ===== OPTIMIZATION 3: Counting Elements =====

def counting_optimization():
    """
    Manual counting vs Counter
    
    Before: O(n) with manual dict
    After: O(n) with optimized Counter (faster due to C implementation)
    """
    
    # BEFORE - Manual counting
    def count_events_slow(events: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {}
        for event in events:
            event_type = event.get('type', 'unknown')
            if event_type in counts:
                counts[event_type] += 1
            else:
                counts[event_type] = 1
        return counts
    
    # AFTER - Counter
    def count_events_fast(events: List[Dict[str, Any]]) -> Counter:
        return Counter(event.get('type', 'unknown') for event in events)
    
    # Benchmark
    events = [{'type': f'type_{i % 100}'} for i in range(10000)]
    
    # Manual counting
    start = time.time()
    counts1 = count_events_slow(events)
    time_manual = (time.time() - start) * 1000
    
    # Counter
    start = time.time()
    counts2 = count_events_fast(events)
    time_counter = (time.time() - start) * 1000
    
    print(f"Manual counting: {time_manual:.2f}ms")
    print(f"Counter: {time_counter:.2f}ms")
    print(f"Improvement: {time_manual/time_counter:.1f}x faster")
    
    # Bonus: Counter has useful methods
    print(f"Most common: {counts2.most_common(5)}")


# ===== OPTIMIZATION 4: defaultdict =====

def defaultdict_optimization():
    """
    Manual dict checking vs defaultdict
    
    Before: Repeated key existence checks
    After: Automatic default values
    """
    
    # BEFORE - Manual dict
    def group_by_severity_slow(events: List[Dict[str, Any]]) -> Dict[str, List]:
        grouped = {}
        for event in events:
            severity = event.get('severity', 'unknown')
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(event)
        return grouped
    
    # AFTER - defaultdict
    def group_by_severity_fast(events: List[Dict[str, Any]]) -> defaultdict:
        grouped = defaultdict(list)
        for event in events:
            severity = event.get('severity', 'unknown')
            grouped[severity].append(event)
        return grouped
    
    # Benchmark
    events = [{'severity': f'sev_{i % 10}', 'id': i} for i in range(10000)]
    
    # Manual dict
    start = time.time()
    grouped1 = group_by_severity_slow(events)
    time_manual = (time.time() - start) * 1000
    
    # defaultdict
    start = time.time()
    grouped2 = group_by_severity_fast(events)
    time_default = (time.time() - start) * 1000
    
    print(f"Manual dict: {time_manual:.2f}ms")
    print(f"defaultdict: {time_default:.2f}ms")
    print(f"Improvement: {time_manual/time_default:.1f}x faster")


# ===== OPTIMIZATION 5: Vectorized Operations =====

def vectorization_optimization():
    """
    Python loops vs NumPy vectorization
    
    Before: O(n) with Python loop (slow)
    After: O(n) with NumPy vectorization (10-100x faster)
    """
    
    # BEFORE - Python loop
    def calculate_threat_scores_slow(scores: List[float], weights: List[float]) -> List[float]:
        results = []
        for i in range(len(scores)):
            results.append(scores[i] * weights[i] * 1.5 + 10)
        return results
    
    # AFTER - NumPy vectorization
    def calculate_threat_scores_fast(scores: np.ndarray, weights: np.ndarray) -> np.ndarray:
        return scores * weights * 1.5 + 10
    
    # Benchmark
    n = 100000
    scores_list = [float(i % 100) for i in range(n)]
    weights_list = [float(i % 10) / 10 for i in range(n)]
    
    scores_np = np.array(scores_list)
    weights_np = np.array(weights_list)
    
    # Python loop
    start = time.time()
    results1 = calculate_threat_scores_slow(scores_list, weights_list)
    time_loop = (time.time() - start) * 1000
    
    # NumPy vectorization
    start = time.time()
    results2 = calculate_threat_scores_fast(scores_np, weights_np)
    time_np = (time.time() - start) * 1000
    
    print(f"Python loop: {time_loop:.2f}ms")
    print(f"NumPy vectorization: {time_np:.2f}ms")
    print(f"Improvement: {time_loop/time_np:.1f}x faster")


# ===== OPTIMIZATION 6: List Comprehension vs Filter/Map =====

def comprehension_optimization():
    """
    Traditional loops vs list comprehensions
    
    List comprehensions are more Pythonic and often faster
    """
    
    events = [{'severity': i % 3, 'score': i * 10} for i in range(10000)]
    
    # BEFORE - Traditional loop
    def filter_high_severity_slow(events: List[Dict]) -> List[Dict]:
        results = []
        for event in events:
            if event['severity'] >= 2:
                results.append(event)
        return results
    
    # AFTER - List comprehension
    def filter_high_severity_fast(events: List[Dict]) -> List[Dict]:
        return [event for event in events if event['severity'] >= 2]
    
    # Benchmark
    start = time.time()
    results1 = filter_high_severity_slow(events)
    time_loop = (time.time() - start) * 1000
    
    start = time.time()
    results2 = filter_high_severity_fast(events)
    time_comp = (time.time() - start) * 1000
    
    print(f"Traditional loop: {time_loop:.2f}ms")
    print(f"List comprehension: {time_comp:.2f}ms")
    print(f"Improvement: {time_loop/time_comp:.1f}x faster")


# ===== OPTIMIZATION 7: String Concatenation =====

def string_concatenation_optimization():
    """
    String concatenation optimization
    
    Before: += in loop (O(n²) due to string immutability)
    After: join() with list (O(n))
    """
    
    # BEFORE - String concatenation in loop
    def build_log_slow(entries: List[str]) -> str:
        log = ""
        for entry in entries:
            log += entry + "\n"  # O(n²) - creates new string each time
        return log
    
    # AFTER - join()
    def build_log_fast(entries: List[str]) -> str:
        return "\n".join(entries)  # O(n)
    
    # Benchmark
    entries = [f"Log entry {i}" for i in range(1000)]
    
    # String concatenation
    start = time.time()
    log1 = build_log_slow(entries)
    time_concat = (time.time() - start) * 1000
    
    # join()
    start = time.time()
    log2 = build_log_fast(entries)
    time_join = (time.time() - start) * 1000
    
    print(f"String concatenation: {time_concat:.2f}ms")
    print(f"join(): {time_join:.2f}ms")
    print(f"Improvement: {time_concat/time_join:.1f}x faster")


# ===== PRACTICAL EXAMPLES =====

class OptimizedEventProcessor:
    """
    Optimized event processor using efficient data structures
    """
    
    def __init__(self):
        # Use appropriate data structures
        self.suspicious_ips: Set[str] = set()  # O(1) lookup
        self.event_queue: deque = deque(maxlen=10000)  # O(1) append/popleft
        self.event_counts: Counter = Counter()  # Efficient counting
        self.events_by_type: defaultdict = defaultdict(list)  # Auto-initialize
        
        # For statistics
        self.threat_scores: List[float] = []
    
    def add_suspicious_ip(self, ip: str):
        """O(1) addition to set"""
        self.suspicious_ips.add(ip)
    
    def is_suspicious(self, ip: str) -> bool:
        """O(1) membership test"""
        return ip in self.suspicious_ips
    
    def enqueue_event(self, event: Dict[str, Any]):
        """O(1) append to deque"""
        self.event_queue.append(event)
    
    def process_next_event(self) -> Dict[str, Any]:
        """O(1) popleft from deque"""
        if self.event_queue:
            return self.event_queue.popleft()
        return None
    
    def count_event_type(self, event_type: str):
        """O(1) counter increment"""
        self.event_counts[event_type] += 1
    
    def group_event(self, event: Dict[str, Any]):
        """O(1) grouping with defaultdict"""
        event_type = event.get('type', 'unknown')
        self.events_by_type[event_type].append(event)
    
    def get_top_event_types(self, n: int = 10) -> List[tuple]:
        """Get most common event types - O(n log n)"""
        return self.event_counts.most_common(n)
    
    def calculate_aggregate_scores(self) -> Dict[str, float]:
        """Vectorized calculation with NumPy"""
        if not self.threat_scores:
            return {'mean': 0, 'max': 0, 'min': 0}
        
        scores_np = np.array(self.threat_scores)
        
        return {
            'mean': float(np.mean(scores_np)),
            'max': float(np.max(scores_np)),
            'min': float(np.min(scores_np)),
            'std': float(np.std(scores_np))
        }


# ===== SUMMARY OF OPTIMIZATIONS =====

OPTIMIZATION_SUMMARY = """
DATA STRUCTURE OPTIMIZATION GUIDE
==================================

1. MEMBERSHIP TESTING
   Before: if item in list  # O(n)
   After:  if item in set   # O(1)
   Improvement: 10-1000x faster for large collections

2. FIFO OPERATIONS
   Before: queue.pop(0)        # O(n)
   After:  queue.popleft()     # O(1)
   Improvement: 100x faster for 10k items

3. COUNTING
   Before: Manual dict with if/else
   After:  Counter from collections
   Improvement: 2-3x faster + cleaner code

4. GROUPING
   Before: Manual dict with key checks
   After:  defaultdict from collections
   Improvement: 1.5-2x faster + cleaner code

5. VECTORIZATION
   Before: Python loops
   After:  NumPy operations
   Improvement: 10-100x faster for numeric operations

6. STRING CONCATENATION
   Before: str += str in loop  # O(n²)
   After:  "".join(list)       # O(n)
   Improvement: 10-100x faster for many concatenations

7. LIST COMPREHENSION
   Before: Traditional for loops with append
   After:  List comprehensions
   Improvement: 1.5-2x faster + more readable

APPLY THESE PATTERNS TO:
- deception_engine/scoring.py
- deception_engine/policy_manager.py
- ml/profiling.py
- utils/* files

EXPECTED OVERALL IMPROVEMENT: 20-40% faster
"""


if __name__ == '__main__':
    print("=" * 60)
    print("DATA STRUCTURE OPTIMIZATION BENCHMARKS")
    print("=" * 60)
    
    print("\n1. Membership Testing (List vs Set)")
    print("-" * 60)
    membership_testing_optimization()
    
    print("\n2. FIFO Operations (List vs deque)")
    print("-" * 60)
    fifo_operations_optimization()
    
    print("\n3. Counting Elements (Manual vs Counter)")
    print("-" * 60)
    counting_optimization()
    
    print("\n4. Dictionary Grouping (dict vs defaultdict)")
    print("-" * 60)
    defaultdict_optimization()
    
    print("\n5. Vectorized Operations (Loop vs NumPy)")
    print("-" * 60)
    vectorization_optimization()
    
    print("\n6. List Comprehension")
    print("-" * 60)
    comprehension_optimization()
    
    print("\n7. String Concatenation")
    print("-" * 60)
    string_concatenation_optimization()
    
    print("\n" + "=" * 60)
    print(OPTIMIZATION_SUMMARY)
