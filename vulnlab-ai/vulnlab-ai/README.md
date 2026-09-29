# vulnlab-ai — 로컬 실습 환경 전용 웹 취약점 탐지 AI 연구 툴킷

**범위 제한**: 모든 요청은 `agent/safety.py` 허용 목록(localhost/루프백 + 직접 지정한 실습 호스트)만 통과합니다.
외부 사이트 공격, 권한 우회, 페이로드 자동 생성 기능은 포함하지 않습니다.

## 빠른 시작
```bash
pip install -r requirements.txt
# 1) 실습 서버 (Docker, 127.0.0.1 에만 노출)
cd lab && docker compose up -d --build && cd ..
#    (Docker 없이) python lab/app.py

python run.py lab-check
python run.py collect                 # → dataset/data/raw.jsonl
python run.py stats
python run.py split                   # → train/val/test.jsonl
python run.py evaluate --detector rules            # 규칙 기준선
python run.py evaluate --detector llm --provider ollama
python run.py evaluate --detector llm --provider anthropic   # ANTHROPIC_API_KEY 필요
python run.py export-finetune         # → dataset/data/finetune_train.jsonl
python -m unittest discover -s tests -t .
```

## 새 provider 추가
`models/base.py` 의 `LLMProvider.complete(system, user) -> str` 만 구현하고 `models/registry.py` 에 등록,
`config/settings.json` 의 `providers` 에 설정을 추가하면 됩니다. 분석/평가 코드는 수정할 필요가 없습니다.

## 라벨링 원칙
라벨은 **엔드포인트가 취약한지가 아니라, 이 요청/응답 안에 증거가 보이는지**를 기준으로 붙입니다.
(취약한 엔드포인트에 정상 입력을 보낸 경우 → `none`, hard negative)
