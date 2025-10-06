from __future__ import annotations
import time, heapq, hashlib
from dataclasses import dataclass, field
from urllib.parse import urlparse

def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower()

def now() -> float:
    return time.time()

@dataclass(order=True)
class PQItem:
    priority: float
    url: str = field(compare=False)
    meta: dict = field(compare=False, default_factory=dict)

class FrontierManager:
    """
    Coada prioritară cu:
    - scor: 0.5*sim_sem + 0.3*autoritate + 0.2*diversitate
    - rate-limit per domeniu (crawl_delay sec)
    - dedup URL prin sha1
    """
    def __init__(self, crawl_delay: float = 1.0):
        self._pq: list[PQItem] = []
        self._seen: set[str] = set()
        self._last_hit: dict[str, float] = {}
        self.crawl_delay = crawl_delay

    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def add(self, url: str, priority: float, meta: dict | None = None):
        k = self._key(url)
        if k in self._seen:
            return
        self._seen.add(k)
        heapq.heappush(self._pq, PQItem(-priority, url, meta or {}))

    def add_many(self, items: list[dict]):
        for it in items:
            self.add(it["url"], it.get("priority", 0.0), it.get("meta", {}))

    def can_fetch(self, url: str) -> bool:
        d = domain_of(url)
        last = self._last_hit.get(d, 0.0)
        return (now() - last) >= self.crawl_delay

    def mark_fetched(self, url: str):
        self._last_hit[domain_of(url)] = now()

    def mark_seen_url(self, url: str):
        self._seen.add(self._key(url))

    def empty(self) -> bool:
        return not self._pq

    def pop(self) -> PQItem | None:
        if not self._pq:
            return None
        return heapq.heappop(self._pq)

    @staticmethod
    def score(sim_semantic: float, authority: float, diversity: float) -> float:
        return 0.5*sim_semantic + 0.3*authority + 0.2*diversity
