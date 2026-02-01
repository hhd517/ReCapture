import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AdamW
import pandas as pd
import os
import json

class TextDataset(Dataset):
    """CSV 파일에서 텍스트를 읽어오는 데이터셋 (OCR 과정 없음!)"""
    
    def __init__(self, csv_file, tokenizer, max_length=256):
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 1. CSV 파일 로드
        print(f"📂 데이터셋 로딩 중: {csv_file}")
        self.df = pd.read_csv(csv_file)
        
        # 2. 라벨 인코딩 (문자열 -> 숫자)
        # 중요: 알파벳 순으로 정렬해야 나중에 이미지 모델과 순서가 맞음!
        self.categories = sorted(self.df['category'].unique())
        self.label_to_idx = {cat: idx for idx, cat in enumerate(self.categories)}
        
        print(f"✅ 카테고리 맵핑: {self.label_to_idx}")
        print(f"✅ 총 데이터 개수: {len(self.df)}개")
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        # CSV에서 행(row) 가져오기
        row = self.df.iloc[idx]
        text = str(row['text']) # 텍스트 컬럼
        category = row['category']
        
        # 라벨 변환
        label = self.label_to_idx[category]
        
        # 텍스트가 비어있거나 너무 짧으면 대체
        if len(text.strip()) < 2:
            text = "내용 없음"
        
        # 토크나이징
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def train_model():
    print("=" * 70)
    print("🤖 텍스트 모델 학습 시작 (KoELECTRA-Base)")
    print("=" * 70)
    
    # 1. 설정 (Base 모델 사용)
    model_name = "monologg/koelectra-base-v3-discriminator"
    csv_path = "train_text.csv"  # 아까 만든 CSV 파일 경로
    
    # 2. 토크나이저 & 모델 로드
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # 데이터셋을 먼저 로드해서 카테고리 개수를 알아냄
    full_dataset = TextDataset(csv_path, tokenizer)
    num_labels = len(full_dataset.categories)
    
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels
    )
    
    # 3. 데이터 로더 (학습용)
    train_loader = DataLoader(full_dataset, batch_size=8, shuffle=True) # Base모델은 4~8 추천
    
    # 4. GPU 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    # 5. 최적화 도구
    optimizer = AdamW(model.parameters(), lr=3e-5) # Base모델은 2e-5 ~ 5e-5 추천
    
    # 6. 학습 루프
    num_epochs = 10
    print(f"\n🔥 학습 시작 (Epochs: {num_epochs})")
    
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch in train_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            loss = outputs.loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs.logits, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        acc = 100 * correct / total
        avg_loss = total_loss / len(train_loader)
        print(f"Epoch [{epoch+1}/{num_epochs}] Loss: {avg_loss:.4f} | Acc: {acc:.2f}%")

    # 7. 저장
    save_dir = 'models/text_model_v1'
    os.makedirs(save_dir, exist_ok=True)
    
    model.save_pretrained(save_dir)
    tokenizer.save_pretrained(save_dir)
    
    # ★중요★ 라벨 맵핑도 같이 저장해야 나중에 안 헷갈림
    with open(os.path.join(save_dir, 'label_map.json'), 'w', encoding='utf-8') as f:
        json.dump(full_dataset.label_to_idx, f, ensure_ascii=False, indent=4)
        
    print(f"💾 모델 저장 완료: {save_dir}")

if __name__ == "__main__":
    train_model()