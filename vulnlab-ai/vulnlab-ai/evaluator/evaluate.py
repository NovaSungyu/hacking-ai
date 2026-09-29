import json
import time
from pathlib import Path
from typing import Any, Dict, List

from analyzer.schema import LABELS, Sample
from .metrics import compute_metrics


def evaluate(detector, samples: List[Sample], verbose: bool = True) -> Dict[str, Any]:
    y_true, y_pred, preds, latencies = [], [], [], []
    for i, s in enumerate(samples, 1):
        t0 = time.perf_counter()
        p = detector.predict(s.exchange)
        latencies.append((time.perf_counter() - t0) * 1000)
        y_true.append(s.label)
        y_pred.append(p.label)
        preds.append({"id": s.id, "scenario": s.scenario, "true": s.label, "pred": p.label,
                      "confidence": p.confidence, "evidence": p.evidence,
                      "reasoning": p.reasoning, "error": p.error})
        if verbose:
            print(f"\r평가 중 {i}/{len(samples)}", end="", flush=True)
    if verbose:
        print()
    return {
        "detector": getattr(detector, "name", type(detector).__name__),
        "num_samples": len(samples),
        "metrics": compute_metrics(y_true, y_pred, LABELS),
        "call_failures": sum(1 for p in preds if p["error"]),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "mismatches": [p for p in preds if p["true"] != p["pred"]],
        "predictions": preds,
    }


def print_report(r: Dict[str, Any]) -> None:
    b, m = r["metrics"]["binary"], r["metrics"]["multiclass"]
    print(f"\n=== 평가 결과: {r['detector']} (n={r['num_samples']}) ===")
    print(f"[이진: 취약 vs 정상]  TP={b['tp']} FP={b['fp']} FN={b['fn']} TN={b['tn']}")
    print(f"  accuracy={b['accuracy']:.3f} precision={b['precision']:.3f} "
          f"recall={b['recall']:.3f} f1={b['f1']:.3f} FPR={b['false_positive_rate']:.3f}")
    print(f"[다중 분류]  accuracy={m['accuracy']:.3f} macro_f1={m['macro_f1']:.3f}")
    for c, v in m["per_class"].items():
        if v["support"]:
            print(f"  {c:18s} P={v['precision']:.2f} R={v['recall']:.2f} F1={v['f1']:.2f} (n={v['support']})")
    print(f"호출/파싱 실패: {r['call_failures']} | 평균 지연: {r['avg_latency_ms']} ms | 오답: {len(r['mismatches'])}")
    for x in r["mismatches"][:10]:
        print(f"  ✗ {x['scenario']}: true={x['true']} pred={x['pred']} {x['error'] or ''}")


def save_report(r: Dict[str, Any], path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
