from fastapi import FastAPI
import pickle
import numpy as np
import os

app = FastAPI()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "model.pkl")

model = pickle.load(open(model_path, "rb"))

@app.post("/predict-demand")
def predict(
    product_id: int,
    category: int,
    region: int,
    price: float,
    discount: float,
    holiday: int
):

    try:
        data = np.array([[
            product_id,
            category,
            region,
            price,
            discount,
            holiday
        ]])

        prediction = model.predict(data)

        return {
            "predicted_units_sold": float(prediction[0])
        }

    except Exception as e:
        return {
            "error": str(e)
        }

