import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

# 특징 데이터 로드
df = pd.read_csv('audio_features.csv')

# 라벨 생성: 파일명에 'dementia' 들어가면 1, 아니면 0
df['label'] = df['filename'].apply(lambda x: 1 if 'dementia' in x.lower() else 0)

# 특징과 라벨 분리
X = df.drop(['filename', 'label'], axis=1)
y = df['label']

# 학습/테스트 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 로지스틱 회귀 모델 학습
model = LogisticRegression()
model.fit(X_train, y_train)

# 예측
y_pred = model.predict(X_test)

# 🔍 라벨 분포 확인
print("✅ 라벨 분포:\n", df['label'].value_counts())

# 성능 평가
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))