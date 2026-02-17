# classification/services/image_classifier.py
import os
from pathlib import Path
from django.conf import settings
from typing import List, Tuple

import torch
import timm
from PIL import Image
from torchvision import transforms

# ✅ HEIC 지원
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass


class ImageClassifier:
    """
    ✅ EfficientNet 이미지 분류기 (최종 4카테고리)
    - predict(): (top1_cat, top1_conf)
    - predict_proba(): (top1_cat, top1_conf, top2_cat, top2_conf, margin)
    """

    # ✅ 4카테고리(폴더명/라벨명과 동일)
    # ⚠️ 순서는 "학습 때 ImageFolder가 만든 classes 순서"와 같아야 함.
    #    (보통 알파벳순: finance, info, others, study_note)
    CATEGORIES: List[str] = [
        "finance",
        "info",
        "others",
        "study_note",
    ]

    CATEGORY_KR = {
        "finance": "결제/예약",
        "study_note": "학습/노트",
        "info": "정보",
        "others": "기타",
    }

    def __init__(
        self,
        model_name: str = "efficientnet_b0",
        model_path: str = None,
        device: str = "cpu",
    ):
        self.device = torch.device(device)

        print("🔧 이미지 분류 모델 로딩 중...")

        base_dir = Path(settings.BASE_DIR)

        # ✅ (1) 기본 후보 경로들
        default_path = base_dir / "classification" / "models" / "efficientnet_v1.pth"
        alt_path = base_dir / "saved_models" / "efficientnet_v1.pth"

        # ✅ (2) Render 같은 환경에서 쓸 임시 저장 위치 (/tmp는 보통 write 가능)
        tmp_path = Path("/tmp/efficientnet_v1.pth")

        # ✅ (3) 우선순위: 직접 지정 > default > alt > tmp(이미 다운된 경우)
        candidates = []
        if model_path:
            candidates.append(Path(model_path))
        candidates.extend([default_path, alt_path, tmp_path])

        resolved = None
        for p in candidates:
            if p.exists() and p.is_file() and p.stat().st_size > 1024 * 1024:
                resolved = p
                break

        # ✅ (4) 없으면 HF URL에서 다운로드
        if resolved is None:
            url = os.getenv("EFFICIENTNET_MODEL_URL")
            if not url:
                raise FileNotFoundError(
                    f"❌ 모델 파일이 없습니다:\n"
                    f"- {default_path}\n"
                    f"- {alt_path}\n"
                    f"또는 환경변수 EFFICIENTNET_MODEL_URL을 설정하세요.\n"
                    f"cwd={os.getcwd()}"
                )

            self._download_model(url, tmp_path)

            if not tmp_path.exists() or tmp_path.stat().st_size < 1024 * 1024:
                raise FileNotFoundError(
                    f"❌ 모델 다운로드 실패: {tmp_path}\n"
                    f"url={url}\n"
                    f"cwd={os.getcwd()}"
                )

            resolved = tmp_path

        model_path = str(resolved)
        print(f"   📂 모델 파일: {model_path} ({Path(model_path).stat().st_size} bytes)")

        # ✅ 모델 로드
        self.model = timm.create_model(
            model_name,
            pretrained=False,
            num_classes=len(self.CATEGORIES),
        ).to(self.device)
        self.model.eval()

        ckpt = torch.load(model_path, map_location=self.device)
        if isinstance(ckpt, dict) and "state_dict" in ckpt:
            ckpt = ckpt["state_dict"]
        if isinstance(ckpt, dict):
            ckpt = {k.replace("module.", ""): v for k, v in ckpt.items()}

        self.model.load_state_dict(ckpt, strict=True)

        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

        self.categories = self.CATEGORIES[:]
        self.category_kr = self.CATEGORY_KR.copy()

        print(f"✅ 모델 준비 완료! (카테고리: {self.categories})\n")

    def _download_model(self, url: str, out_path: Path):
        """
        모델 파일을 URL에서 내려받아 out_path에 저장
        - HF resolve URL을 그대로 넣으면 됨
        """
        import requests

        # 이미 받아둔 게 있으면 재사용(너무 자잘한 파일이면 재다운)
        if out_path.exists() and out_path.stat().st_size > 10 * 1024 * 1024:
            print(f"   ℹ️ 기존 다운로드 모델 재사용: {out_path}")
            return

        print(f"⬇️ 모델 다운로드 시작: {url}")

        r = requests.get(url, timeout=180, stream=True)
        r.raise_for_status()

        out_path.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)

        # ✅ 너무 작으면 HTML 에러 페이지 다운로드 가능성 있음 → 진단 로그
        print(f"✅ 모델 다운로드 완료: {out_path} ({total} bytes)")

        if total < 1024 * 1024:
            try:
                head = out_path.read_bytes()[:200]
                print("⚠️ 다운로드 파일이 너무 작습니다. HEAD(200bytes):", head)
            except Exception:
                pass

    @torch.no_grad()
    def predict(self, image_path: str) -> Tuple[str, float]:
        img = Image.open(image_path).convert("RGB")
        x = self.transform(img).unsqueeze(0).to(self.device)

        logits = self.model(x)
        probs = torch.softmax(logits, dim=1).squeeze(0)

        top_idx = int(torch.argmax(probs).item())
        conf = float(probs[top_idx].item())
        return self.categories[top_idx], conf

    @torch.no_grad()
    def predict_proba(self, image_path: str):
        """
        Returns:
            top1_cat, top1_conf, top2_cat, top2_conf, margin
        """
        img = Image.open(image_path).convert("RGB")
        x = self.transform(img).unsqueeze(0).to(self.device)

        logits = self.model(x)
        probs = torch.softmax(logits, dim=1).squeeze(0)

        top2 = torch.topk(probs, k=2)
        idx1 = int(top2.indices[0].item())
        idx2 = int(top2.indices[1].item())
        p1 = float(top2.values[0].item())
        p2 = float(top2.values[1].item())

        c1 = self.categories[idx1]
        c2 = self.categories[idx2]
        margin = p1 - p2
        return c1, p1, c2, p2, margin

    def predict_with_korean(self, image_path: str):
        cat, conf = self.predict(image_path)
        return cat, self.category_kr.get(cat, cat), float(conf)