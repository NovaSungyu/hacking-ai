"""데이터셋 생성: 수집(collect) → JSONL 저장 → 분할(split) → 파인튜닝 형식 변환."""
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

import requests

from agent.collector import Collector
from agent.safety import TargetNotAllowed
from analyzer.llm_detector import SYSTEM_PROMPT, build_user_prompt
from analyzer.schema import Sample
import uuid


def load_jsonl(path) -> List[Sample]:
    with open(path, encoding="utf-8") as f:
        return [Sample.from_dict(json.loads(line)) for line in f if line.strip()]


def save_jsonl(samples: List[Sample], path, append: bool = False) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")


def collect(settings: Dict[str, Any], scenarios_path, out_path, append: bool = False) -> int:
    lab, cc = settings["lab"], settings["collector"]
    collector = Collector(lab["base_url"], lab.get("extra_allowed_hosts", []),
                          cc.get("timeout_sec", 5), cc.get("max_body_chars", 20000))
    scenarios = json.loads(Path(scenarios_path).read_text(encoding="utf-8"))
    samples: List[Sample] = []
    for sc in scenarios:
        method = sc.get("method", "GET").upper()
        variants = sc.get("variants") or [sc.get("params", {})]
        for params in variants:
            try:
                ex = collector.fetch(method, sc["path"],
                                     params=params if method == "GET" else None,
                                     data=params if method != "GET" else None)
            except TargetNotAllowed:
                raise  # 안전장치 위반은 절대 건너뛰지 않고 중단
            except requests.RequestException as e:
                print(f"[warn] {sc['name']} {params}: {e}")
                continue
            samples.append(Sample(id=uuid.uuid4().hex[:12], scenario=sc["name"], label=sc["label"],
                                  label_source="lab_design", exchange=ex, notes=sc.get("notes", "")))
            time.sleep(cc.get("delay_sec", 0.1))
    save_jsonl(samples, out_path, append=append)
    return len(samples)


def split(in_path, out_dir, train=0.7, val=0.15, seed=42) -> Dict[str, int]:
    """라벨별 층화(stratified) 분할. 주의: 같은 엔드포인트의 변형들이 train/test 에 섞이면
    성능이 부풀려진다. 실제 연구에서는 엔드포인트/앱 단위로 나누는 것을 권장."""
    samples = load_jsonl(in_path)
    by_label = defaultdict(list)
    for s in samples:
        by_label[s.label].append(s)
    rng = random.Random(seed)
    parts = {"train": [], "val": [], "test": []}
    for items in by_label.values():
        rng.shuffle(items)
        n = len(items)
        n_val = max(1, round(n * val)) if n >= 3 else 0
        n_test = max(1, round(n * (1 - train - val))) if n >= 3 else 0
        n_train = n - n_val - n_test
        parts["train"] += items[:n_train]
        parts["val"] += items[n_train:n_train + n_val]
        parts["test"] += items[n_train + n_val:]
    out_dir = Path(out_dir)
    for name, items in parts.items():
        save_jsonl(items, out_dir / f"{name}.jsonl")
    return {k: len(v) for k, v in parts.items()}


def export_finetune(in_path, out_path, max_body_chars: int = 3000) -> int:
    """chat 형식(JSONL)으로 변환: {"messages":[system,user,assistant]}.
    정답(assistant)은 라벨과 증거 기반의 JSON. 대부분의 fine-tuning 도구가 이 형식을 받는다."""
    samples = load_jsonl(in_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in samples:
            answer = {"label": s.label, "confidence": 1.0, "evidence": [],
                      "reasoning": s.notes or ""}
            rec = {"messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(s.exchange, max_body_chars)},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
            ]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(samples)


def stats(path) -> Dict[str, Any]:
    samples = load_jsonl(path)
    return {"total": len(samples),
            "by_label": dict(Counter(s.label for s in samples)),
            "by_label_source": dict(Counter(s.label_source for s in samples)),
            "scenarios": len({s.scenario for s in samples})}
