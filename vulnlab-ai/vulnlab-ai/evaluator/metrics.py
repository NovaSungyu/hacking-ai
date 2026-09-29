"""지표 계산. 두 관점을 모두 제공한다.

1) binary  : '취약(none 이외) vs 정상(none)' 탐지 여부 → TP/FP/FN/TN, accuracy, precision, recall, F1
2) multiclass : 취약 유형까지 맞혀야 정답 → 정확도, 클래스별 P/R/F1, macro-F1, 혼동행렬
"""
from typing import Dict, List, Optional

from analyzer.schema import LABELS


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p, r = _div(tp, tp + fp), _div(tp, tp + fn)
    return {"precision": p, "recall": r, "f1": _div(2 * p * r, p + r)}


def compute_metrics(y_true: List[str], y_pred: List[str], labels: Optional[List[str]] = None,
                    negative: str = "none") -> Dict:
    labels = labels or LABELS
    assert len(y_true) == len(y_pred), "length mismatch"
    n = len(y_true)

    tp = fp = fn = tn = 0
    for t, p in zip(y_true, y_pred):
        tv, pv = t != negative, p != negative
        tp += tv and pv
        fp += (not tv) and pv
        fn += tv and (not pv)
        tn += (not tv) and (not pv)
    binary = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
              "accuracy": _div(tp + tn, n), **_prf(tp, fp, fn),
              "false_positive_rate": _div(fp, fp + tn)}

    cm = {t: {p: 0 for p in labels} for t in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    per_class, f1s = {}, []
    for c in labels:
        c_tp = cm[c][c]
        c_fp = sum(cm[t][c] for t in labels if t != c)
        c_fn = sum(cm[c][p] for p in labels if p != c)
        support = sum(cm[c].values())
        per_class[c] = {**_prf(c_tp, c_fp, c_fn), "support": support}
        if support:
            f1s.append(per_class[c]["f1"])
    multiclass = {"accuracy": _div(sum(cm[c][c] for c in labels), n),
                  "macro_f1": _div(sum(f1s), len(f1s)),
                  "per_class": per_class, "confusion_matrix": cm}
    return {"n": n, "binary": binary, "multiclass": multiclass}
