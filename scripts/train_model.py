import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error


# ==========================================
# LOAD DATASET
# ==========================================

df = pd.read_csv("data/training/model_dataset.csv")

print("Dataset loaded successfully")


# ==========================================
# ENCODE STATE COLUMN
# ==========================================

encoder = LabelEncoder()

df["state"] = encoder.fit_transform(df["state"])

# Save encoder for future prediction API
joblib.dump(encoder, "models/state_encoder.pkl")


# ==========================================
# SELECT INPUT FEATURES
# ==========================================

FEATURES = [

    "temperature",
    "rainfall",
    "humidity",
    "wind_speed",
    "pressure",

    "month",

    "rainfall_7day_avg",
    "rainfall_30day_avg",
    "rainfall_90day_avg",

    "temp_90day_avg",
    "humidity_90day_avg",

    "pressure_anomaly",
    "rainfall_acceleration",
    "consecutive_dry_days",

    "state"
]

X = df[FEATURES]


# ==========================================
# TRAIN FUNCTION
# ==========================================

def train_model(target_column, model_name):

    print(f"\nTraining {model_name}...")

    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    error = mean_absolute_error(y_test, predictions)

    print(f"{model_name} MAE: {error}")

    joblib.dump(model, f"models/{model_name}.pkl")

    print(f"{model_name} saved successfully")


# ==========================================
# TRAIN ALL MODELS
# ==========================================

train_model("flood_risk_score", "flood_model")

train_model("drought_risk_score", "drought_model")

train_model("cyclone_risk_score", "cyclone_model")


print("\nAll models trained successfully")