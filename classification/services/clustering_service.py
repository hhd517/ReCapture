# services/clustering_service.py
#실제 서비스에서 쓰는 클러스터링 엔진
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer

# 임베딩
from sentence_transformers import SentenceTransformer

# 클러스터링
import hdbscan


@dataclass
class ClusterItem:
    path: str
    text: str


class ClusteringService:
    """
    study_note 2차 분류용 클러스터링 서비스

    - 입력: 이미지 path + OCR text 리스트
    - 출력: cluster_id별 묶음 + 대표 키워드 + suggested_name
    - noise는 cluster_id = -1 로 처리
    """

    def __init__(
        self,
        embed_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        min_cluster_size: int = 3,
        min_samples: Optional[int] = None,
        cluster_selection_epsilon: float = 0.0,
        topk_keywords: int = 5,
    ):
        self.embedder = SentenceTransformer(embed_model_name)
        self.min_cluster_size = int(min_cluster_size)
        self.min_samples = min_samples
        self.cluster_selection_epsilon = float(cluster_selection_epsilon)
        self.topk_keywords = int(topk_keywords)

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        # normalize_embeddings=True => cosine 기반 거리에서 안정적인 편
        vecs = self.embedder.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vecs

    def _cluster(self, X: np.ndarray) -> np.ndarray:
        # cosine distance 기반
        clusterer = hdbscan.HDBSCAN(
            metric="euclidean",  # normalize_embeddings=True면 유클리드~코사인 유사
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            prediction_data=False,
        )
        labels = clusterer.fit_predict(X)  # noise = -1
        return labels

    def _keywords_by_cluster(self, texts: List[str], labels: np.ndarray) -> Dict[int, List[str]]:
        # cluster별 문서 합친 뒤 TF-IDF 상위 단어 추출
        # 한국어는 형태소 분석 없이도 “추천용”으로는 충분히 쓸만함(완벽X).
        vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
        )

        # cluster별 텍스트 묶기
        cluster_texts: Dict[int, str] = {}
        for t, lab in zip(texts, labels):
            if lab == -1:
                continue
            cluster_texts.setdefault(int(lab), "")
            cluster_texts[int(lab)] += " " + (t or "")

        if not cluster_texts:
            return {}

        keys = sorted(cluster_texts.keys())
        docs = [cluster_texts[k] for k in keys]

        tfidf = vectorizer.fit_transform(docs)
        feature_names = np.array(vectorizer.get_feature_names_out())

        out: Dict[int, List[str]] = {}
        for row_i, cid in enumerate(keys):
            row = tfidf[row_i].toarray().reshape(-1)
            if row.size == 0:
                out[cid] = []
                continue
            top_idx = np.argsort(row)[::-1][: self.topk_keywords]
            kws = feature_names[top_idx].tolist()
            # 너무 짧은 토큰/숫자 위주 제거
            kws = [w for w in kws if len(w) >= 2 and not w.isdigit()]
            out[cid] = kws[: self.topk_keywords]
        return out

    def cluster_items(self, items: List[ClusterItem]) -> Dict[str, Any]:
        if not items:
            return {"clusters": {}, "noise": [], "summary": "입력 없음"}

        texts = [(it.text or "").strip() for it in items]
        paths = [it.path for it in items]

        # 텍스트가 거의 없는 건 noise 후보로 빼도 됨(선택)
        # 여기서는 일단 다 포함시키되, 너무 짧으면 임베딩이 불안정해질 수 있음.
        safe_texts = [t if len(t) >= 3 else " " for t in texts]

        X = self._embed_texts(safe_texts)
        labels = self._cluster(X)

        # cluster별 키워드
        kw_map = self._keywords_by_cluster(texts=safe_texts, labels=labels)

        clusters: Dict[int, Dict[str, Any]] = {}
        noise: List[str] = []

        for p, lab in zip(paths, labels):
            lab = int(lab)
            if lab == -1:
                noise.append(p)
                continue
            clusters.setdefault(lab, {"images": [], "keywords": [], "suggested_name": ""})
            clusters[lab]["images"].append(p)

        for cid in sorted(clusters.keys()):
            kws = kw_map.get(cid, [])
            clusters[cid]["keywords"] = kws
            clusters[cid]["suggested_name"] = "/".join(kws[:3]) if kws else f"cluster_{cid}"

        summary = f"총 {len(clusters)}개 그룹, noise {len(noise)}개"
        return {"clusters": clusters, "noise": noise, "summary": summary}
