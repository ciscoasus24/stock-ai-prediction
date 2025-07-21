import os
from dotenv import load_dotenv
import openai
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

ticker = "005930.KS"  # Samsung Electronics Co., Ltd.
df = yf.download(ticker, start="2015-01-01", end="2024-12-31")
print(df.head())

# 종가만 사용
data = df['Close'].values.reshape(-1, 1)

# 데이터 정규화
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

# 시퀀스 생성
def create_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len])
    return np.array(X), np.array(y)

seq_len = 20
X, y = create_sequences(scaled_data, seq_len)

class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

model = LSTMModel()
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# DataLoader
X_tensor = torch.tensor(X, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.float32)
dataset = TensorDataset(X_tensor, y_tensor)
loader = DataLoader(dataset, batch_size=64, shuffle=True)

# 학습 루프
for epoch in range(30):
    for batch_x, batch_y in loader:
        out = model(batch_x)
        loss = criterion(out, batch_y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f"Epoch {epoch+1}, Loss: {loss.item():.5f}")

with torch.no_grad():
    last_seq = torch.tensor(scaled_data[-seq_len:], dtype=torch.float32).unsqueeze(0)  # (1, seq_len, 1)
    pred_scaled = model(last_seq).item()
    pred = scaler.inverse_transform([[pred_scaled]])
    print(f"내일 예측 종가: {pred[0][0]:.2f} 원")