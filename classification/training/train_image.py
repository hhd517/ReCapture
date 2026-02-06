import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import timm
import os

#이미지 모델 학습 파일(efficientnet_v1)-> 결과 저장:models/efficientnet_v1.pth

def train_model():
    """EfficientNet 이미지 분류 모델 학습"""
    
    print("=" * 70)
    print("🤖 이미지 분류 모델 학습 시작")
    print("=" * 70)
    
    # 1. 데이터 전처리 설정
    transform = transforms.Compose([
        transforms.Resize((224, 224)),           # 224x224로 리사이즈
        transforms.ToTensor(),                    # 텐서 변환
        transforms.Normalize(                     # 정규화
            [0.485, 0.456, 0.406],               # ImageNet 평균
            [0.229, 0.224, 0.225]                # ImageNet 표준편차
        )
    ])
    
    # 2. 데이터 로드
    print("\n📁 데이터 로딩 중...")
    train_dataset = datasets.ImageFolder('train_data', transform=transform)
    train_loader = DataLoader(
        train_dataset, 
        batch_size=4,      # 한 번에 4장씩 처리
        shuffle=True       # 데이터 섞기
    )
    
    # 카테고리 정보
    print(f"✅ 카테고리: {train_dataset.classes}")
    print(f"✅ 총 이미지: {len(train_dataset)}장")
    print(f"✅ 배치 크기: 4")
    
    # 3. EfficientNet 모델 로드
    print("\n🔧 EfficientNet-B0 모델 로딩...")
    model = timm.create_model(
        'efficientnet_b0',    # EfficientNet-B0
        pretrained=True,       # ImageNet 사전학습 가중치 사용
        num_classes=4          # 6개 카테고리
    )
    print("✅ 모델 로드 완료")
    
    # GPU 사용 가능하면 GPU로
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"✅ 디바이스: {device}")
    
    # 4. 학습 설정
    criterion = nn.CrossEntropyLoss()  # 손실 함수
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)  # 최적화
    
    # 5. 학습 시작
    print("\n" + "=" * 70)
    print("🔥 학습 시작 (25 에포크)")
    print("=" * 70)
    
    num_epochs = 10
    
    for epoch in range(num_epochs):
        model.train()  # 학습 모드
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            # GPU로 이동
            images = images.to(device)
            labels = labels.to(device)
            
            # 순전파
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            # 역전파
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # 통계
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
        
        # 에포크 결과
        accuracy = 100 * correct / total
        avg_loss = total_loss / len(train_loader)
        
        print(f"Epoch [{epoch+1:2d}/{num_epochs}] "
              f"Loss: {avg_loss:.4f} | "
              f"Accuracy: {accuracy:.2f}%")
    
    # 6. 모델 저장
    print("\n" + "=" * 70)
    print("💾 모델 저장 중...")
    
    os.makedirs('models', exist_ok=True)
    save_path = 'models/efficientnet_v1.pth'
    torch.save(model.state_dict(), save_path)
    
    print(f"✅ 모델 저장 완료: {save_path}")
    print("=" * 70)
    
    # 카테고리 순서 출력 (중요!)
    print(f"\n⚠️  중요: 카테고리 순서")
    print(f"   {train_dataset.classes}")
    print("   → image_classifier.py에서 이 순서대로 써야 함!")
    
    return train_dataset.classes

if __name__ == "__main__":
    categories = train_model()