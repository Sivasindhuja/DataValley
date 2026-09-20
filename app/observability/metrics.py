from collections import Counter
_metrics = Counter()
def inc(key: str, n=1):
    _metrics[key]+=n
def get_metrics():
    return dict(_metrics)
