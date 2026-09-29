#!/usr/bin/env python3
"""vulnlab-ai CLI.  사용: python run.py <command> [options]

  lab-check         실습 서버 연결 확인
  collect           시나리오대로 요청 수집 → dataset/data/raw.jsonl
  label             수집 데이터 수동 검수(라벨 수정)
  split             train/val/test 분할
  stats             데이터셋 통계
  evaluate          탐지기 평가 (rules 또는 llm)
  export-finetune   fine-tuning 용 chat JSONL 변환
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def p(path: str) -> Path:
    pth = Path(path)
    return pth if pth.is_absolute() else ROOT / pth


def main() -> int:
    ap = argparse.ArgumentParser(description="Local-lab web vulnerability detection research toolkit")
    ap.add_argument("--config", default="config/settings.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lab-check")

    c = sub.add_parser("collect")
    c.add_argument("--scenarios", default="config/scenarios.json")
    c.add_argument("--out", default="dataset/data/raw.jsonl")
    c.add_argument("--append", action="store_true")

    l = sub.add_parser("label")
    l.add_argument("--file", default="dataset/data/raw.jsonl")
    l.add_argument("--only-disagree", action="store_true", help="규칙 탐지 힌트와 다른 샘플만 검수")

    s = sub.add_parser("split")
    s.add_argument("--file", default="dataset/data/raw.jsonl")
    s.add_argument("--out-dir", default="dataset/data")
    s.add_argument("--seed", type=int, default=42)

    st = sub.add_parser("stats")
    st.add_argument("--file", default="dataset/data/raw.jsonl")

    e = sub.add_parser("evaluate")
    e.add_argument("--file", default="dataset/data/test.jsonl")
    e.add_argument("--detector", choices=["rules", "llm"], default=None)
    e.add_argument("--provider", default=None, help="settings.json 의 providers 키 (예: ollama, openai, anthropic, mock)")
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--out", default=None)

    f = sub.add_parser("export-finetune")
    f.add_argument("--file", default="dataset/data/train.jsonl")
    f.add_argument("--out", default="dataset/data/finetune_train.jsonl")

    args = ap.parse_args()
    settings = json.loads(p(args.config).read_text(encoding="utf-8"))

    if args.cmd == "lab-check":
        from agent.collector import Collector
        lab = settings["lab"]
        ex = Collector(lab["base_url"], lab.get("extra_allowed_hosts", [])).fetch("GET", "/")
        print(f"OK {ex.url} -> {ex.status_code}")

    elif args.cmd == "collect":
        from dataset.builder import collect
        n = collect(settings, p(args.scenarios), p(args.out), append=args.append)
        print(f"{n}개 샘플 저장 → {args.out}")

    elif args.cmd == "label":
        from dataset.labeling import review
        review(p(args.file), only_disagree=args.only_disagree)

    elif args.cmd == "split":
        from dataset.builder import split
        print(split(p(args.file), p(args.out_dir), seed=args.seed))

    elif args.cmd == "stats":
        from dataset.builder import stats
        print(json.dumps(stats(p(args.file)), ensure_ascii=False, indent=2))

    elif args.cmd == "evaluate":
        from analyzer.factory import build_detector
        from dataset.builder import load_jsonl
        from evaluator.evaluate import evaluate, print_report, save_report
        detector = build_detector(settings, args.detector, args.provider)
        samples = load_jsonl(p(args.file))
        if args.limit:
            samples = samples[: args.limit]
        report = evaluate(detector, samples)
        print_report(report)
        out = args.out or f"results/eval_{detector.name.replace(':', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        save_report(report, p(out))
        print(f"리포트 저장 → {out}")

    elif args.cmd == "export-finetune":
        from dataset.builder import export_finetune
        n = export_finetune(p(args.file), p(args.out), settings["detector"].get("max_body_chars", 3000))
        print(f"{n}개 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
