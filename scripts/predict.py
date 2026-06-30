import joblib
import pandas as pd


# ==========================================
# LOAD MODELS
# ==========================================

flood_model = joblib.load("models/flood_model.pkl")
drought_model = joblib.load("models/drought_model.pkl")
cyclone_model = joblib.load("models/cyclone_model.pkl")

state_encoder = joblib.load("models/state_encoder.pkl")

print("Models loaded successfully")


# ==========================================
# USER INPUT
# ==========================================

state = "Assam"
temperature = 30
rainfall = 120
humidity = 80
wind_speed = 20
pressure = 1000
month = 6


# ==========================================
# ENCODE STATE
# ==========================================

state_encoded = state_encoder.transform([state])[0]


# ==========================================
# TEMPORARY ENGINEERED FEATURES
# MVP ONLY
# ==========================================

rainfall_7day_avg = rainfall
rainfall_30day_avg = rainfall
rainfall_90day_avg = rainfall

temp_90day_avg = temperature
humidity_90day_avg = humidity

pressure_anomaly = 0

rainfall_acceleration = 0

consecutive_dry_days = 0


# ==========================================
# BUILD INPUT DATAFRAME
# ==========================================

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


# ==========================================
# PREDICTIONS
# ==========================================

flood_prediction = flood_model.predict(input_data)[0]

drought_prediction = drought_model.predict(input_data)[0]

cyclone_prediction = cyclone_model.predict(input_data)[0]


# ==========================================
# OUTPUT
# ==========================================

print("\n===== CLIMATE RISK PREDICTION =====")

print(f"Flood Risk Score: {round(flood_prediction, 2)}")

print(f"Drought Risk Score: {round(drought_prediction, 2)}")

print(f"Cyclone Risk Score: {round(cyclone_prediction, 2)}")