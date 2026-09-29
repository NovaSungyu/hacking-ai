"""수동 라벨 검수 도구. 자동 라벨(lab_design)을 사람이 확인/수정하고 label_source=manual 로 기록."""
from analyzer.rules import RuleDetector
from analyzer.schema import LABELS
from .builder import load_jsonl, save_jsonl


def review(path, only_disagree: bool = False) -> None:
    samples = load_jsonl(path)
    rules = RuleDetector()
    changed = 0
    for i, s in enumerate(samples):
        hint = rules.predict(s.exchange)
        if only_disagree and hint.label == s.label:
            continue
        ex = s.exchange
        print("=" * 70)
        print(f"[{i + 1}/{len(samples)}] id={s.id} scenario={s.scenario} source={s.label_source}")
        print(f"{ex.method} {ex.url} -> {ex.status_code}")
        print(f"inputs: {ex.inputs}")
        print("body:", ex.response_body[:400].replace("\n", " "))
        print(f"현재 라벨: {s.label} | 규칙 탐지 힌트: {hint.label} {hint.evidence}")
        ans = input(f"Enter=유지, 라벨입력 {LABELS}, q=저장 후 종료 > ").strip()
        if ans == "q":
            break
        if ans in LABELS and ans != s.label:
            s.label, s.label_source = ans, "manual"
            changed += 1
    save_jsonl(samples, path)
    print(f"저장 완료. 수정된 샘플: {changed}")
