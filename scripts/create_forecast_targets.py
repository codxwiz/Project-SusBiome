import pandas as pd

# Load training dataset
df = pd.read_csv("data/training/model_dataset.csv")

print("Dataset loaded")
print("Original shape:", df.shape)

# Create future prediction targets (30 days ahead)
# shift(-30) means: value 30 rows in the future
df["rainfall_next_30d"] = df["rainfall"].shift(-30)
df["temperature_next_30d"] = df["temperature"].shift(-30)
df["humidity_next_30d"] = df["humidity"].shift(-30)

# Remove rows with empty future values
df = df.dropna()

print("New shape:", df.shape)

# Save new forecasting dataset
df.to_csv("data/training/forecast_dataset.csv", index=False)

print("Forecast dataset created successfully")