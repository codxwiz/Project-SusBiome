import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor
import joblib
import os

# Create models folder if missing
os.makedirs("models", exist_ok=True)

# Load dataset
df = pd.read_csv("data/training/model_dataset.csv")

print("Dataset loaded successfully")
print("Shape:", df.shape)

# Remove non-numeric columns
X = df.drop(columns=["date", "state"])

# Select target
target = "flood_risk_score"
y = X[target]

# Remove target from features
X = X.drop(columns=[target])

print("Training features:")
print(X.columns)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# Build model
model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=8,
    random_state=42
)

print("Training started...")

# Train
model.fit(X_train, y_train)

# Predict
predictions = model.predict(X_test)

# Metrics
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("\nResults")
print("MAE:", mae)
print("R2 Score:", r2)

# Save model
joblib.dump(model, "models/xgboost_flood_model.pkl")

print("\nModel saved successfully")