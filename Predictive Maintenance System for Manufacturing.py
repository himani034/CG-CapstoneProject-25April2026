import os
import requests
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


load_dotenv()

API_ENDPOINT = os.getenv("endpoint")
API_KEY = os.getenv("key")

if not API_ENDPOINT or not API_KEY:
    raise ValueError("Please set ENDPOINT and KEY in .env")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MaintenanceAPI")


app = FastAPI(
    title="Smart Predictive Maintenance API",
    version="2.0"
)
class MachineData(BaseModel):
    timestamp: str = Field(..., example="2024-01-01 00:00:00")
    machine_id: str = Field(..., example="M01")
    temperature: float = Field(..., example=75)
    vibration: float = Field(..., example=0.9)
    pressure: float = Field(..., example=45)
    humidity: float = Field(..., example=50)

    @field_validator("timestamp")
    @classmethod
    def check_timestamp(cls, v):
        datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return v

def azure_predict(data: MachineData):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "input_data": {
            "columns": [
                "Timestamp", "MachineID", "Temperature",
                "Vibration", "Pressure", "Humidity"
            ],
            "data": [[
                data.timestamp,
                data.machine_id,
                data.temperature,
                data.vibration,
                data.pressure,
                data.humidity
            ]]
        }
    }

    try:
        res = requests.post(API_ENDPOINT, headers=headers, json=payload)
        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)
    except Exception as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail="Azure connection error")

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Azure prediction failed")

    try:
        return res.json()
    except:
        raise HTTPException(status_code=500, detail="Invalid response")

def is_anomaly(d: MachineData):
    return (
        d.temperature > 100 or
        d.vibration > 1.5 or
        d.pressure > 80
    )

@app.post("/predict-failure")
def predict(data: MachineData):
    start = datetime.utcnow()

    try:
        result = azure_predict(data)

        # safer parsing
        prediction = result.get("predictions", result)

        anomaly_flag = is_anomaly(data)

        latency = (datetime.utcnow() - start).total_seconds()

        return {
            "failure_probability": prediction,
            "anomaly_detected": anomaly_flag,
            "response_time": latency,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(str(e))
        raise HTTPException(status_code=500, detail="Prediction error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)