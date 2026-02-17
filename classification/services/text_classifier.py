# classification/services/text_classifier.py
import os
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from django.conf import settings


class TextClassifier:
    """
    🧠 텍스트 분류기 (4카테고리)

    ✅ 기본: HF 우선 로드 (배포 안정)
      - Hugging Face Hub에서 subfolder(text_model_v1)로 로드
    ✅ 로컬 강제: TEXT_MODEL_SOURCE=local 일 때만 로컬 우선
      - classification/models/text_model_v1 폴더가 존재할 경우 로컬에서 로드

    - label_map.json 우선, 없으면 DEFAULT_4 사용
    """

    DEFAULT_4 = ["finance", "study_note", "info", "others"]

    CATEGORY_KR_4 = {
        "finance": "결제/예약",
        "study_note": "학습/노트",
        "info": "정보",
        "others": "기타",
    }

    DEFAULT_HF_REPO = "junghae/recapture-model"
    DEFAULT_HF_SUBFOLDER = "text_model_v1"

    def __init__(self):
        print("🔧 텍스트 분류 모델 로딩 중...")
        print("✅ TextClassifier: HF 우선 로드 버전(2026-02-18)")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        local_dir = Path(settings.BASE_DIR) / "classification" / "models" / "text_model_v1"

        hf_repo = os.getenv("TEXT_MODEL_HF_REPO", self.DEFAULT_HF_REPO)
        hf_subfolder = os.getenv("TEXT_MODEL_HF_SUBFOLDER", self.DEFAULT_HF_SUBFOLDER)

        # ✅ HF 우선 정책
        # - 기본: HF 로드
        # - TEXT_MODEL_SOURCE=local 인 경우에만 로컬 우선
        source_pref = os.getenv("TEXT_MODEL_SOURCE", "hf").strip().lower()
        use_local = (source_pref == "local")

        if use_local and local_dir.exists():
            source = str(local_dir)
            is_hf = False
            print(f"   📂 로컬에서 로드(강제 local): {source}")
        else:
            source = hf_repo
            is_hf = True
            print(f"   📦 HF에서 로드(기본): {hf_repo}/{hf_subfolder}")

        # ✅ 라벨맵 로드
        self.id_to_label = self._load_label_map(local_dir, hf_repo, hf_subfolder, is_hf)

        # ✅ 모델/토크나이저 로드
        if is_hf:
            # HF는 subfolder 필수
            self.tokenizer = AutoTokenizer.from_pretrained(source, subfolder=hf_subfolder)
            self.model = AutoModelForSequenceClassification.from_pretrained(source, subfolder=hf_subfolder)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(source)
            self.model = AutoModelForSequenceClassification.from_pretrained(source)

        self.model.to(self.device)
        self.model.eval()

        print(f"✅ 모델 로드 성공 (Device: {self.device})")

    def _load_label_map(self, local_dir: Path, hf_repo: str, hf_subfolder: str, is_hf: bool):
        # 로컬
        if not is_hf:
            p = local_dir / "label_map.json"
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    label_map = json.load(f)
                id_to_label = {int(v): k for k, v in label_map.items()}
                print(f"✅ 라벨 맵핑 로드 완료(LOCAL): {len(id_to_label)}개 카테고리")
                return id_to_label

            print("⚠️ label_map.json이 없습니다 → DEFAULT_4로 임시 설정합니다.")
            return {i: cat for i, cat in enumerate(self.DEFAULT_4)}

        # HF
        try:
            from huggingface_hub import hf_hub_download

            path = hf_hub_download(
                repo_id=hf_repo,
                filename=f"{hf_subfolder}/label_map.json",
            )
            with open(path, "r", encoding="utf-8") as f:
                label_map = json.load(f)

            id_to_label = {int(v): k for k, v in label_map.items()}
            print(f"✅ 라벨 맵핑 로드 완료(HF): {len(id_to_label)}개 카테고리")
            return id_to_label

        except Exception as e:
            print(f"⚠️ label_map.json(HF) 로드 실패 → DEFAULT_4 사용 ({e})")
            return {i: cat for i, cat in enumerate(self.DEFAULT_4)}

    def predict(self, text: str):
        if not text or len(text.strip()) < 2:
            return "others", 0.0

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=256,
            truncation=True,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=1)
            confidence, pred_idx = torch.max(probs, dim=1)

        pred_idx = int(pred_idx.item())
        confidence = float(confidence.item())

        category = self.id_to_label.get(pred_idx, "others")
        return category, confidence

    def predict_with_korean(self, text: str):
        cat, conf = self.predict(text)
        return cat, self.CATEGORY_KR_4.get(cat, cat), conf