from __future__ import annotations
import os, re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

# opționale – doar dacă există
_EnhancedScraper = None
_universal = None
_IndustryScraper = None

try:
    from scrapers.enhanced_scraper import EnhancedScraper as _EnhancedScraper  # type: ignore
except Exception:
    pass

try:
    import tools.universal_site_pipeline as _universal  # type: ignore
except Exception:
    pass

try:
    from web_scraping.real_industry_scraper import IndustryScraper as _IndustryScraper  # type: ignore
except Exception:
    pass


def _domain(u: str) -> str:
    try:
        return urlparse(u).netloc.lower()
    except Exception:
        return ""

def _bs_outlinks(html: str, base: str) -> List[str]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return []
    out = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            out.append(urljoin(base, href))
    except Exception:
        pass
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

def _trafilatura_text(html: str) -> Tuple[str, str]:
    title, text = "", ""
    try:
        import trafilatura
        downloaded = trafilatura.extract(html, include_comments=False, include_tables=False, favor_recall=True)
        if downloaded:
            text = downloaded
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            t = soup.find("title")
            if t and t.text:
                title = t.text.strip()
        except Exception:
            pass
    except Exception:
        pass
    return text, title

def _requests_fetch(url: str, user_agent: str) -> Tuple[str, str, Dict[str, Any]]:
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        r = s.get(url, timeout=25, allow_redirects=True)
        if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type",""):
            return "", "", {}
        return r.text, r.url, dict(r.headers)
    except Exception:
        return "", "", {}

def _playwright_fetch(url: str, user_agent: str) -> Tuple[str, str, str, List[str], str]:
    """Returnează (html, final_url, title, outlinks, plain_text) folosind Chromium headless."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return "", "", "", [], ""
    wait_ms = int(os.getenv("PLAYWRIGHT_WAIT_MS", "2500"))
    timeout_ms = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "20000"))
    html, final_url, title, links, plain_text = "", "", "", [], ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=user_agent, ignore_https_errors=True)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(wait_ms)
            final_url = page.url
            title = page.title() or ""
            # text simplu (fallback dacă trafilatura nu scoate)
            try:
                plain_text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
            except Exception:
                plain_text = ""
            # outlinks din DOM
            try:
                links = page.eval_on_selector_all("a[href]", "els => els.map(a => a.href)")
            except Exception:
                links = []
            html = page.content()
        except Exception:
            pass
        finally:
            ctx.close(); browser.close()
    return html, final_url, title, links or [], plain_text

def smart_fetch(url: str, user_agent: Optional[str]=None) -> Dict[str, Any]:
    """
    Întoarce:
      { ok, url, domain, title, text, outlinks, raw_html, headers }  sau  { ok, site_pages: [...] }
    Ordine: EnhancedScraper → universal_site_pipeline → IndustryScraper → requests+trafilatura → Playwright (fallback).
    """
    ua = user_agent or os.getenv("CRAWL_UA", "Mozilla/5.0 (compatible; Orchestrator/1.0)")
    # 1) EnhancedScraper
    if _EnhancedScraper is not None:
        try:
            es = _EnhancedScraper(user_agent=ua) if "user_agent" in _EnhancedScraper.__init__.__code__.co_varnames else _EnhancedScraper()
            for method in ("scrape", "fetch", "crawl_url", "crawl"):
                if hasattr(es, method):
                    res = getattr(es, method)(url)
                    if isinstance(res, dict):
                        if "site_pages" in res and isinstance(res["site_pages"], list) and res["site_pages"]:
                            return {"ok": True, "site_pages": res["site_pages"]}
                        html = res.get("html") or res.get("raw_html") or ""
                        text = res.get("text") or res.get("content") or ""
                        title = res.get("title") or ""
                        final_url = res.get("final_url") or res.get("url") or url
                        outlinks = res.get("outlinks") or (_bs_outlinks(html, final_url) if html else [])
                        ok = bool(text or (html and outlinks))
                        return {
                            "ok": ok, "url": final_url, "domain": _domain(final_url),
                            "title": title, "text": text if text else _trafilatura_text(html)[0],
                            "outlinks": outlinks, "raw_html": html or None, "headers": res.get("headers")
                        }
        except Exception:
            pass

    # 2) Universal site pipeline
    if _universal is not None:
        try:
            for fname in ("scrape_url", "scrape", "fetch_url", "process_url"):
                if hasattr(_universal, fname):
                    res = getattr(_universal, fname)(url)
                    if isinstance(res, dict):
                        if "site_pages" in res and isinstance(res["site_pages"], list) and res["site_pages"]:
                            return {"ok": True, "site_pages": res["site_pages"]}
                        html = res.get("html") or ""
                        text = res.get("text") or res.get("content") or ""
                        title = res.get("title") or ""
                        final_url = res.get("final_url") or res.get("url") or url
                        outlinks = res.get("outlinks") or (_bs_outlinks(html, final_url) if html else [])
                        ok = bool(text or (html and outlinks))
                        return {
                            "ok": ok, "url": final_url, "domain": _domain(final_url),
                            "title": title, "text": text if text else _trafilatura_text(html)[0],
                            "outlinks": outlinks, "raw_html": html or None
                        }
        except Exception:
            pass

    # 3) IndustryScraper
    if _IndustryScraper is not None:
        try:
            ins = _IndustryScraper()
            for method in ("scrape_url", "scrape", "crawl_url", "crawl"):
                if hasattr(ins, method):
                    res = getattr(ins, method)(url)
                    if isinstance(res, dict):
                        if "site_pages" in res and isinstance(res["site_pages"], list) and res["site_pages"]:
                            return {"ok": True, "site_pages": res["site_pages"]}
                        html = res.get("html") or ""
                        text = res.get("text") or res.get("content") or ""
                        title = res.get("title") or ""
                        final_url = res.get("final_url") or res.get("url") or url
                        outlinks = res.get("outlinks") or (_bs_outlinks(html, final_url) if html else [])
                        ok = bool(text or (html and outlinks))
                        return {
                            "ok": ok, "url": final_url, "domain": _domain(final_url),
                            "title": title, "text": text if text else _trafilatura_text(html)[0],
                            "outlinks": outlinks, "raw_html": html or None
                        }
        except Exception:
            pass

    # 4) Fallback: requests + trafilatura
    html, final_url, headers = _requests_fetch(url, ua)
    if html:
        text, title = _trafilatura_text(html)
        outlinks = _bs_outlinks(html, final_url or url)
        ok = bool(text or outlinks)
        if ok:
            return {
                "ok": True, "url": final_url or url, "domain": _domain(final_url or url),
                "title": title, "text": text, "outlinks": outlinks,
                "raw_html": html, "headers": headers
            }

    # 5) Fallback: Playwright (opțional, controlat de ENABLE_PLAYWRIGHT)
    if os.getenv("ENABLE_PLAYWRIGHT", "0").lower() in ("1","true","yes"):
        html, final_url, title, links, plain_text = _playwright_fetch(url, ua)
        if html or links or plain_text:
            # trage trafilatura peste HTML pentru text mai bun; dacă iese gol, folosește plain_text
            text, ttitle = _trafilatura_text(html) if html else ("", "")
            if not text and plain_text:
                text = plain_text
            if not title and ttitle:
                title = ttitle
            return {
                "ok": bool(text or links), "url": final_url or url, "domain": _domain(final_url or url),
                "title": title or "", "text": text or "", "outlinks": list(dict.fromkeys(links or [])),
                "raw_html": html or None
            }

    return {"ok": False}
