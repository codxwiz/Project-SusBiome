from fastapi import FastAPI
import joblib
import pandas as pd


# ==========================================
# LOAD MODELS
# ==========================================

flood_model = joblib.load("models/flood_model.pkl")
drought_model = joblib.load("models/drought_model.pkl")
cyclone_model = joblib.load("models/cyclone_model.pkl")
state_encoder = joblib.load("models/state_encoder.pkl")


# ==========================================
# CREATE APP
# ==========================================

app = FastAPI()

print("API started successfully")


# ==========================================
# ROOT ROUTE
# ==========================================

@app.get("/")
def home():
    return {
        "message": "SusBiome Climate Prediction API Running"
    }


# ==========================================
# PREDICTION ROUTE
# ==========================================

@app.get("/predict")
def predict(
    state: str,
    temperature: float,
    rainfall: float,
    humidity: float,
    wind_speed: float,
    pressure: float,
    month: int
):

    # Encode state
    state_encoded = state_encoder.transform([state])[0]

    # Temporary engineered features
    rainfall_7day_avg = rainfall
    rainfall_30day_avg = rainfall
    rainfall_90day_avg = rainfall

    temp_90day_avg = temperature
    humidity_90day_avg = humidity

    pressure_anomaly = 0
    rainfall_acceleration = 0
    consecutive_dry_days = 0

    # Build dataframe
    input_data = pd.DataFrame([{

        "temperature": temperature,
        "rainfall": rainfall,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "pressure": pressure,

        "month": month,

        "rainfall_7day_avg": rainfall_7day_avg,
        "rainfall_30day_avg": rainfall_30day_avg,
        "rainfall_90day_avg": rainfall_90day_avg,

        "temp_90day_avg": temp_90day_avg,
        "humidity_90day_avg": humidity_90day_avg,

        "pressure_anomaly": pressure_anomaly,
        "rainfall_acceleration": rainfall_acceleration,
        "consecutive_dry_days": consecutive_dry_days,

        "state": state_encoded
    }])

    # Predict
    flood_prediction = flood_model.predict(input_data)[0]
    drought_prediction = drought_model.predict(input_data)[0]
    cyclone_prediction = cyclone_model.predict(input_data)[0]

    return {
        "flood_risk": round(float(flood_prediction), 2),
        "drought_risk": round(float(drought_prediction), 2),
        "cyclone_risk": round(float(cyclone_prediction), 2)
    }