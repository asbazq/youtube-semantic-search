"""Evaluate unfiltered transcript retrieval against a frozen, manually judged pool.

The labels cover the 2026-09-29 top-10 pool. Refuse to score new passages that
have not been judged, rather than silently treating them as irrelevant.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


def passage_key(item):
    return item["video_id"], round(float(item["start_time"]), 3)


def summarize(ranks, k):
    """Hit@K and reciprocal rank, with rank 1 as the best search result."""
    hits = [next((rank for rank in relevant if rank <= k), None) for relevant in ranks]
    return {"hit_rate": sum(rank is not None for rank in hits) / len(hits),
            "mrr": sum(1 / rank for rank in hits if rank is not None) / len(hits)}


def main():
    parser = argparse.ArgumentParser(description="Measure transcript retrieval Hit@K and MRR@K")
    parser.add_argument("--base-url", default="http://localhost:18765")
    parser.add_argument("--labels", type=Path, default=Path(__file__).resolve().parent.parent /
                        "benchmarks/retrieval_labels_2026-09-29.json")
    parser.add_argument("--output", type=Path, default=Path("retrieval_benchmark_results.json"))
    args = parser.parse_args()
    dataset = json.loads(args.labels.read_text())
    base = args.base_url.rstrip("/")
    details = []
    unjudged = []

    for case in dataset["cases"]:
        labels = {passage_key(item): item["relevant"] for item in case["judgments"]}
        request = Request(base + "/api/search",
                          data=json.dumps({"query": case["question"], "top_k": 10}).encode(),
                          headers={"Content-Type": "application/json"})
        started = time.monotonic()
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
        ranked = result["results"]
        unknown = [passage_key(item) for item in ranked if passage_key(item) not in labels]
        unjudged.extend((case["id"], key) for key in unknown)
        relevant_ranks = [rank for rank, item in enumerate(ranked, 1)
                          if labels.get(passage_key(item)) is True]
        details.append({"id": case["id"], "question": case["question"],
                        "returned": len(ranked), "relevant_ranks": relevant_ranks,
                        "seconds": round(time.monotonic() - started, 3),
                        "unjudged": unknown})

    report = {"labels": str(args.labels), "base_url": base, "cases": details,
              "unjudged_count": len(unjudged)}
    if not unjudged:
        ranks = [item["relevant_ranks"] for item in details]
        report["metrics"] = {f"at_{k}": summarize(ranks, k) for k in (1, 3, 5, 10)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    for item in details:
        print(f"{item['id']}: relevant ranks {item['relevant_ranks'] or 'none'}, "
              f"returned {item['returned']}, unjudged {len(item['unjudged'])}")
    if unjudged:
        print(f"Unjudged passages: {len(unjudged)}. Review labels before reporting metrics.")
        raise SystemExit(2)
    for k, values in report["metrics"].items():
        print(f"{k}: Hit={values['hit_rate']:.4f}, MRR={values['mrr']:.4f}")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
