import os
import random
from collections import defaultdict

import torch
import timm
from PIL import Image
from torchvision import transforms


class ImageClassifier:
    """이미지 분류기 (EfficientNet-B0) - 4 Class Version"""

    def __init__(self, model_path: str = "models/efficientnet_v1.pth"):
        """모델 로드"""
        print("🔧 이미지 분류 모델 로딩 중...")

        # ---------------------------------------------------------
        # 1. 모델 경로
        # ---------------------------------------------------------
        if not os.path.exists(model_path):
            # 혹시 saved_models에 있을 수도 있으니 체크
            alt = "saved_models/efficientnet_v1.pth"
            if os.path.exists(alt):
                model_path = alt
            else:
                raise FileNotFoundError(
                    f"❌ 모델 파일이 없습니다: {model_path}\n"
                    f"먼저 training/train_image.py를 실행해서 모델을 학습하세요!"
                )

        print(f"   📂 모델 파일: {model_path}")

        # ---------------------------------------------------------
        # 2. 모델 생성 (num_classes=4)
        # ---------------------------------------------------------
        self.model = timm.create_model(
            "efficientnet_b0",
            pretrained=False,
            num_classes=4,  # [finance, info, others, study_note]
        )

        # ---------------------------------------------------------
        # 3. 가중치 로드
        # ---------------------------------------------------------
        try:
            self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
            self.model.eval()  # 평가 모드
        except Exception as e:
            raise RuntimeError(f"모델 가중치 로드 실패 (혹시 카테고리 수가 안 맞나요?): {e}")

        # 전처리 (학습 시와 동일)
        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

        # ---------------------------------------------------------
        # 4. 카테고리 이름 (알파벳 순서 필수!)
        # ---------------------------------------------------------
        self.categories = sorted(["finance", "info", "others", "study_note"])

        # ---------------------------------------------------------
        # 5. 한글 매핑
        # ---------------------------------------------------------
        self.category_kr = {
            "finance": "결제/금융",
            "info": "정보",
            "others": "기타(비정보)",
            "study_note": "학습/노트",
        }

        print(f"✅ 모델 준비 완료! (카테고리: {self.categories})\n")

    def predict(self, image_path):
        """
        이미지 분류 예측
        Returns: (카테고리, 확률)
        """
        # 이미지 로드
        if isinstance(image_path, str):
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")
            image = Image.open(image_path).convert("RGB")
        else:
            # Django UploadedFile 객체인 경우
            image = Image.open(image_path).convert("RGB")

        # 전처리
        image_tensor = self.transform(image).unsqueeze(0)

        # 예측
        with torch.no_grad():
            output = self.model(image_tensor)
            probs = torch.softmax(output, dim=1)
            pred_idx = torch.argmax(probs).item()
            confidence = probs[0][pred_idx].item()

        category = self.categories[pred_idx]
        return category, confidence

    def predict_with_korean(self, image_path):
        """한글 카테고리와 함께 반환"""
        category, confidence = self.predict(image_path)
        category_kr = self.category_kr.get(category, category)
        return category, category_kr, confidence


# ========================================
# 테스트 코드 (test_data 전체 평가 + 혼동행렬 + 오답 Top)
# ========================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 이미지 분류 테스트 (4 Class) - test_data 전체 평가")
    print("=" * 60)

    try:
        classifier = ImageClassifier()

        # 테스트 이미지 경로
        test_dir = "test_data"

        # 폴더당 몇 장 평가할지 (None이면 전부)
        PER_CLASS_LIMIT = None  # 예: 50 (폴더당 50장만), 전체 돌리려면 None

        # 지원 확장자 (jpg만 쓰면 놓치는 경우가 많아서 확장)
        EXTS = (".jpg", ".jpeg", ".png", ".webp")

        if not os.path.exists(test_dir):
            print("⚠️ 테스트할 폴더가 없습니다.")
            raise SystemExit(0)

        print(f"📸 '{test_dir}' 폴더의 이미지로 테스트합니다.\n")
        print("폴더 구조 예시:")
        print("test_data/finance, test_data/info, test_data/others, test_data/study_note\n")

        # confusion[true][pred] = count
        confusion = {t: {p: 0 for p in classifier.categories} for t in classifier.categories}
        per_cat_total = defaultdict(int)
        per_cat_correct = defaultdict(int)
        wrong_cases = []  # (true, pred, conf, filename)

        for true_cat in classifier.categories:
            cat_dir = os.path.join(test_dir, true_cat)
            if not os.path.isdir(cat_dir):
                print(f"⚠️ 폴더 없음: {cat_dir}")
                continue

            files = [f for f in os.listdir(cat_dir) if f.lower().endswith(EXTS)]
            files.sort()

            if PER_CLASS_LIMIT is not None and len(files) > PER_CLASS_LIMIT:
                # 대표성 위해 랜덤 샘플링
                random.seed(42)
                files = random.sample(files, PER_CLASS_LIMIT)

            if not files:
                print(f"⚠️ 이미지 없음: {cat_dir}")
                continue

            for f in files:
                img_path = os.path.join(cat_dir, f)
                pred_cat, conf = classifier.predict(img_path)

                per_cat_total[true_cat] += 1
                confusion[true_cat][pred_cat] += 1

                if pred_cat == true_cat:
                    per_cat_correct[true_cat] += 1
                else:
                    wrong_cases.append((true_cat, pred_cat, conf, f))

        # ----- 출력 -----
        total = sum(per_cat_total.values())
        correct = sum(per_cat_correct.values())

        print("\n======================")
        print("✅ Category Accuracy")
        print("======================")
        for c in classifier.categories:
            if per_cat_total[c] == 0:
                print(f"- {c}: 0개")
            else:
                acc = per_cat_correct[c] / per_cat_total[c] * 100
                print(f"- {c}: {per_cat_correct[c]}/{per_cat_total[c]} = {acc:.2f}%")

        if total > 0:
            print(f"\n🎯 Overall: {correct}/{total} = {correct/total*100:.2f}%")

        print("\n======================")
        print("📌 Confusion Matrix (rows=true, cols=pred)")
        print("======================")
        header = "true\\pred\t" + "\t".join(classifier.categories)
        print(header)
        for t in classifier.categories:
            row = [str(confusion[t][p]) for p in classifier.categories]
            print(f"{t}\t" + "\t".join(row))

        wrong_cases.sort(key=lambda x: x[2], reverse=True)
        print("\n======================")
        print("❌ Top wrong (high-confidence) - up to 15")
        print("======================")
        for i, (t, p, conf, f) in enumerate(wrong_cases[:15], 1):
            print(f"{i:02d}. {f} | true={t} pred={p} conf={conf*100:.1f}%")

    except Exception as e:
        print(f"\n❌ 오류: {e}")
