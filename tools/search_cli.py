import json, argparse
from retrieval.semantic_search import SemanticSearcher

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--alpha", type=float, default=0.7)
    ap.add_argument("--lang", type=str, default=None)
    ap.add_argument("--domain", type=str, default=None)
    ap.add_argument("--hybrid", action="store_true")
    args = ap.parse_args()

    s = SemanticSearcher()
    if args.hybrid:
        res = s.search_hybrid(args.query, top_k=args.k, alpha=args.alpha, lang=args.lang, domain=args.domain)
    else:
        res = s.search_vectors(args.query, top_k=args.k, lang=args.lang, domain=args.domain)
    print(json.dumps(res, ensure_ascii=False, indent=2))
