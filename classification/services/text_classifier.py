import os
import json
from collections import defaultdict

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from services.google_ocr_service import GoogleOCRService
from services.ocr_cache import OCRCache


class TextClassifier:
    """
    🧠 텍스트 분류기
    학습된 모델(models/text_model_v1)을 불러와 OCR 텍스트를 4개 카테고리로 예측
    (finance, study_note, info, others)
    """

    def __init__(self):
        print("🔧 텍스트 분류 모델 로딩 중...")

        self.model_path = "models/text_model_v1"
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"❌ 모델 폴더가 없습니다: {self.model_path}\n"
                f"먼저 training/train_text.py를 실행해서 모델을 학습시켜주세요!"
            )

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 라벨맵 로드
        label_map_path = os.path.join(self.model_path, "label_map.json")
        if os.path.exists(label_map_path):
            with open(label_map_path, "r", encoding="utf-8") as f:
                label_map = json.load(f)
            self.id_to_label = {v: k for k, v in label_map.items()}
            print(f"✅ 라벨 맵핑 로드 완료: {len(self.id_to_label)}개 카테고리")
        else:
            print("⚠️ 경고: label_map.json이 없습니다! (알파벳 순서로 임의 설정합니다)")
            categories = sorted(["finance", "info", "others", "study_note"])
            self.id_to_label = {i: cat for i, cat in enumerate(categories)}

        # 모델/토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"✅ 모델 로드 성공 (Device: {self.device})")

        self.category_kr = {
            "finance": "결제/금융",
            "study_note": "학습/노트",
            "info": "정보",
            "others": "기타(비정보)",
        }

    def predict(self, text: str):
        """텍스트 -> (category, confidence)"""
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
        category = self.id_to_label[pred_idx]
        return category, confidence

    def predict_with_korean(self, text: str):
        cat, conf = self.predict(text)
        return cat, self.category_kr.get(cat, cat), conf


def _extract_full_text_from_ocr(response):
    """
    make_dataset.py에서 했던 방식과 최대한 동일하게:
    - response가 dict면 full_text 우선
    - 아니면 str(response)
    """
    if isinstance(response, dict):
        return response.get("full_text", "") or ""
    return str(response)


def _run_ocr(ocr_obj, image_path: str):
    # GoogleOCRService 메서드명 유연 대응
    for name in ["extract_text", "detect_text", "run_ocr", "ocr", "predict", "read_text"]:
        if hasattr(ocr_obj, name):
            return getattr(ocr_obj, name)(image_path)
    raise AttributeError(
        "❌ GoogleOCRService에서 텍스트 추출 메서드를 못 찾았어요.\n"
        "services/google_ocr_service.py에서 실제 메서드명을 확인하고 candidates에 추가하세요."
    )


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 텍스트모델 평가: test_data 이미지 → (OCRCache) → OCR → TextClassifier")
    print("=" * 60)

    TEST_DIR = "test_data"
    CATS = ["finance", "info", "others", "study_note"]
    EXTS = (".jpg", ".jpeg", ".png", ".webp")

    # 폴더당 몇 장 테스트할지 (None이면 전부)
    PER_CLASS_LIMIT = 50

    classifier = TextClassifier()
    ocr = GoogleOCRService()

    # ✅ 학습 때와 동일한 캐시 디렉토리 사용
    cache = OCRCache(cache_dir="ocr_cache")

    confusion = {t: {p: 0 for p in CATS} for t in CATS}
    per_total = defaultdict(int)
    per_correct = defaultdict(int)

    empty_ocr = []
    wrong_cases = []
    cache_hits = 0
    cache_misses = 0

    for true_cat in CATS:
        cat_dir = os.path.join(TEST_DIR, true_cat)
        if not os.path.isdir(cat_dir):
            print(f"⚠️ 폴더 없음: {cat_dir}")
            continue

        files = [f for f in os.listdir(cat_dir) if f.lower().endswith(EXTS)]
        files.sort()
        if PER_CLASS_LIMIT is not None:
            files = files[:PER_CLASS_LIMIT]

        if not files:
            print(f"⚠️ 이미지 없음: {cat_dir}")
            continue

        for f in files:
            img_path = os.path.join(cat_dir, f)

            # 1) OCR 캐시 먼저 확인 (학습 때와 동일)
            cached = cache.load(img_path)
            if cached is not None:
                cache_hits += 1
                response = cached
            else:
                cache_misses += 1
                try:
                    response = _run_ocr(ocr, img_path)
                except Exception as e:
                    print(f"❌ OCR 실패: {true_cat}/{f} | {e}")
                    continue
                cache.save(img_path, response)

            text = _extract_full_text_from_ocr(response)

            if not text or len(text.strip()) < 2:
                empty_ocr.append((true_cat, f))

            # 2) 텍스트 모델 예측
            pred_cat, pred_conf = classifier.predict(text)

            per_total[true_cat] += 1
            confusion[true_cat][pred_cat] += 1

            if pred_cat == true_cat:
                per_correct[true_cat] += 1
            else:
                prev = (text or "").replace("\n", " ")[:80]
                wrong_cases.append((true_cat, pred_cat, pred_conf, prev, f))

    total = sum(per_total.values())
    correct = sum(per_correct.values())

    print("\n======================")
    print("✅ Category Accuracy (Text model)")
    print("======================")
    for c in CATS:
        if per_total[c] == 0:
            print(f"- {c}: 0개")
        else:
            acc = per_correct[c] / per_total[c] * 100
            print(f"- {c}: {per_correct[c]}/{per_total[c]} = {acc:.2f}%")

    if total:
        print(f"\n🎯 Overall: {correct}/{total} = {correct/total*100:.2f}%")
    else:
        print("\n🎯 Overall: 평가할 데이터가 없습니다.")
        raise SystemExit(0)

    print("\n======================")
    print("📌 Confusion Matrix (rows=true, cols=pred)")
    print("======================")
    print("true\\pred\t" + "\t".join(CATS))
    for t in CATS:
        print(t + "\t" + "\t".join(str(confusion[t][p]) for p in CATS))

    print("\n======================")
    print("🈳 OCR 빈 텍스트(또는 너무 짧음)")
    print("======================")
    empty_ratio = len(empty_ocr) / total * 100
    print(f"{len(empty_ocr)} / {total} (빈 OCR 비율: {empty_ratio:.2f}%)")
    if empty_ocr[:10]:
        print("예시(최대 10개): " + ", ".join([f"{c}/{fn}" for c, fn in empty_ocr[:10]]))

    print("\n======================")
    print("🗃️ OCR 캐시 히트/미스")
    print("======================")
    print(f"cache_hit={cache_hits}, cache_miss={cache_misses}")
    if (cache_hits + cache_misses) > 0:
        print(f"cache_hit_rate={cache_hits/(cache_hits+cache_misses)*100:.2f}%")

    wrong_cases.sort(key=lambda x: x[2], reverse=True)
    print("\n======================")
    print("❌ Top wrong (high-confidence) - up to 15")
    print("======================")
    for i, (t, p, conf, prev, fn) in enumerate(wrong_cases[:15], 1):
        print(f"{i:02d}. {t}/{fn} | pred={p} conf={conf*100:.1f}% | ocr='{prev}...'")
