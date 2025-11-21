from __future__ import annotations
# tools/agent_expander.py
import re
import socket
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse

import requests
import urllib.robotparser as robotparser

DEFAULT_API_BASE = "http://127.0.0.1:8083"
HTTP_TIMEOUT = 8  # sec

@dataclass
class ExpandResult:
    created: List[Dict]
    skipped: List[Dict]

def _norm_domain(domain_or_url: str) -> str:
    if not domain_or_url:
        return ""
    if "://" in domain_or_url:
        parsed = urlparse(domain_or_url)
        host = parsed.netloc
    else:
        host = domain_or_url
    host = host.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host

def _robots_allows(url: str, user_agent: str = "*") -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, "/")
    except Exception:
        # Dacă nu putem citi robots.txt, fim conservatori și permitem 1 pagină
        return True

def _is_alive(url: str) -> bool:
    try:
        # HEAD întâi, fallback GET mic
        r = requests.head(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            return True
    except Exception:
        pass
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def _resolve_dns(domain: str) -> bool:
    try:
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def propose_sites(base_domain: str, objective: str, limit: int = 5) -> List[str]:
    """
    Heuristică simplă: subdomenii comune + variante TLD + pagini tipice.
    Poți înlocui ulterior cu o propunere bazată pe LLM sau graf de link-uri.
    """
    d = _norm_domain(base_domain)
    if not d:
        return []

    candidates = []
    # Subdomenii uzuale
    subs = ["www", "blog", "docs", "help", "support"]
    for s in subs:
        candidates.append(f"{s}.{d}")

    # Variante TLD (dacă domeniul e .ro sau .com, încearcă cealaltă)
    if d.endswith(".ro"):
        core = d[:-3].rstrip(".")
        candidates.append(f"{core}.com")
    if d.endswith(".com"):
        core = d[:-4].rstrip(".")
        candidates.append(f"{core}.ro")

    # Elimină duplicate și pe sine
    seen = set()
    out = []
    for c in candidates:
        c_norm = _norm_domain(c)
        if c_norm and c_norm != d and c_norm not in seen:
            seen.add(c_norm)
            out.append(c_norm)

    return out[: max(1, limit)]

def _to_url(domain: str) -> str:
    return f"https://{_norm_domain(domain)}/"

def _create_agent(api_base: str, name: str, domain: str, objective: str, max_pages: int) -> Tuple[bool, Dict]:
    payload = {
        "name": name,
        "domain": _norm_domain(domain),
        "objective": objective,
        "max_pages": max_pages
    }
    try:
        resp = requests.post(f"{api_base}/create-agent", json=payload, timeout=60)
        if resp.status_code == 200:
            return True, resp.json() if resp.headers.get("content-type","").startswith("application/") else {"status":"ok"}
        return False, {"status": resp.status_code, "body": resp.text}
    except Exception as e:
        return False, {"error": str(e)}

def expand_agent(
    api_base: str,
    agent_id: str,
    agent_name: str,
    base_domain: str,
    objective: str,
    max_agents: int = 3,
    max_pages_per_site: int = 20
) -> ExpandResult:
    created: List[Dict] = []
    skipped: List[Dict] = []

    base_domain = _norm_domain(base_domain)
    if not base_domain:
        return ExpandResult(created=created, skipped=[{"domain": "", "reason": "base_domain_invalid"}])

    proposals = propose_sites(base_domain, objective, limit=max_agents * 2)
    # Filtrări: DNS, reachability, robots
    filtered: List[str] = []
    for dom in proposals:
        dom_norm = _norm_domain(dom)
        if not dom_norm:
            skipped.append({"domain": dom, "reason": "invalid"})
            continue
        if not _resolve_dns(dom_norm):
            skipped.append({"domain": dom_norm, "reason": "dns_fail"})
            continue
        url = _to_url(dom_norm)
        if not _is_alive(url):
            skipped.append({"domain": dom_norm, "reason": "unreachable"})
            continue
        if not _robots_allows(url):
            skipped.append({"domain": dom_norm, "reason": "robots_disallow"})
            continue
        filtered.append(dom_norm)

    # Creează agenți pentru primele N
    for dom in filtered[: max_agents]:
        ok, info = _create_agent(api_base, f"{agent_name}:{dom}", dom, objective, max_pages_per_site)
        if ok:
            created.append({"agent_id": info.get("agent_id") if isinstance(info, dict) else None, "domain": dom, "info": info})
        else:
            skipped.append({"domain": dom, "reason": "create_failed", "detail": info})

    return ExpandResult(created=created, skipped=skipped)
