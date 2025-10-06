import os, re, urllib.parse, time
import cloudscraper
from pymongo import MongoClient
import openai
system_prompt = "Răspunde exclusiv în limba română. Folosește DOAR informația din conținutul extras al site-ului (HTML/text) și evită presupunerile. Nu inventa competitori și nu include 'Amazon Romania'. Dacă nu găsești date suficiente, scrie: 'Nu există date suficiente în conținutul extras'. Structură: Industrie (descriere), Competitori (cu puncte tari/slabe), Oportunități, Riscuri, Plan de 30 de zile."

def fetch_text(url: str) -> str:
    scraper = cloudscraper.create_scraper(browser={'custom': 'Chrome'})
    html = scraper.get(url, timeout=60).text
    html = re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', ' ', html, flags=re.I|re.S)
    txt = re.sub(r'<[^>]+>', ' ', html)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

def upsert_content(db, url: str, text: str):
    p = urllib.parse.urlparse(url)
    domain = p.netloc.lower()
    doc = {
        "url": url,
        "site_url": url,
        "title": domain,
        "content": text,
        "content_text": text,
        "raw_text": text,
        "language": "romanian",
        "domain": domain,
        "canonical_url": url,
        "lower_url": url.lower(),
        "source": "direct-analysis",
    }
    for coll in ["industry_sites_content","site_contents","web_content","real_industry_web_content","industry_web_content","site_content","pages"]:
        db[coll].update_one({"site_url": url}, {"$set": doc}, upsert=True)

def run_llm(url: str, text: str, base_url: str) -> str:
    client = openai.OpenAI(base_url=base_url, api_key=os.getenv("OPENAI_API_KEY","local-vllm"))

    def attempt(limit_head: int, limit_tail: int, max_tokens: int) -> str:
        head = text[:limit_head]
        tail = text[-limit_tail:] if len(text) > (limit_head + limit_tail) else ""
        truncated = head + "\n...\n" + tail if tail else head
        msgs = [
            {"role": "system", "content": "Strategic industry analyst. Return concise, structured, actionable insights."},
            {"role": "user", "content": f"Analyze site: {url}\nText (trimmed):\n{truncated}\n\nProvide: industry, competitors, opportunities, risks, and 30/60/90 day plan."}
        ]
        resp = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role":"system","content": system_prompt}] + [{"role":"system","content": system_prompt}] + [{"role":"system","content": system_prompt}] + msgs,
            temperature=0.1,
            max_tokens=900
        )
        return resp.choices[0].message.content

    try:
        return attempt(2000, 1000, 700)
    except Exception as e:
        err = str(e)
        if ("maximum context length" in err) or ("4096 tokens" in err):
            return attempt(1200, 400, 600)
        raise

def main():
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.librariadelfin.ro/"
    text = fetch_text(url)
    if not text:
        print("❌ Failed to fetch content")
        return
    mc = MongoClient("mongodb://localhost:27017")
    db = mc.get_database("ai_agents")
    upsert_content(db, url, text)
    analysis = run_llm(url, text, base_url="http://localhost:9302/v1")
    db["industry_analysis_results"].update_one(
        {"url": url},
        {"$set": {"url": url, "analysis": analysis, "length": len(analysis), "ts": time.time()}},
        upsert=True
    )
    print("✅ Analysis length:", len(analysis))
    print("=== ANALYSIS ===")
    print(analysis)

if __name__ == "__main__":
    main()

ANALYSIS_URLS = os.getenv('ANALYSIS_URLS')
if ANALYSIS_URLS:
    target_urls = [u.strip() for u in ANALYSIS_URLS.split(',') if u.strip()]
