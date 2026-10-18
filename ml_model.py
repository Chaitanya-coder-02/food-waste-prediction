"""
Machine Learning module for Food Waste Prediction using Scikit-Learn.
Trains regression models on actual saved MongoDB records, splits train/test,
and computes genuine MAE, RMSE, and R² metrics without synthetic/fake accuracy scores.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import logging

logger = logging.getLogger(__name__)

# Minimum records required to train a machine learning model reliably
MIN_RECORDS_FOR_ML = 5
RECOMMENDED_RECORDS_FOR_SPLIT = 10

def prepare_dataframe(records):
    """Convert MongoDB records into clean pandas DataFrame for ML processing."""
    if not records or len(records) == 0:
        return pd.DataFrame()
    
    data = []
    for r in records:
        try:
            data.append({
                "food_category": str(r.get("food_category", "Other")),
                "day_of_week": str(r.get("day_of_week", "Monday")),
                "quantity_prepared": float(r.get("quantity_prepared", 0.0)),
                "people_served": int(r.get("people_served", 0)),
                "quantity_wasted": float(r.get("quantity_wasted", 0.0))
            })
        except (ValueError, TypeError):
            continue
            
    df = pd.DataFrame(data)
    # Filter out invalid or zero prepared records
    if not df.empty and "quantity_prepared" in df.columns:
        df = df[df["quantity_prepared"] > 0]
    return df

def train_food_waste_model(records):
    """
    Trains a Scikit-Learn regression model to predict food waste (kg).
    Uses genuine train/test evaluation, MAE, RMSE, and R² scores.
    """
    df = prepare_dataframe(records)
    total_records = len(df)
    
    if total_records < MIN_RECORDS_FOR_ML:
        # Calculate baseline historical category waste percentage if any records exist
        baseline_pct = 0.0
        if total_records > 0 and df["quantity_prepared"].sum() > 0:
            baseline_pct = round((df["quantity_wasted"].sum() / df["quantity_prepared"].sum()) * 100, 2)
            
        return {
            "status": "insufficient_data",
            "message": f"Dataset currently has {total_records} record(s). At least {MIN_RECORDS_FOR_ML} records are needed to train a Scikit-Learn Machine Learning model.",
            "total_records": total_records,
            "min_needed": MIN_RECORDS_FOR_ML,
            "pipeline": None,
            "metrics": None,
            "baseline_waste_percentage": baseline_pct
        }

    features = ["food_category", "day_of_week", "quantity_prepared", "people_served"]
    target = "quantity_wasted"
    
    X = df[features]
    y = df[target]

    categorical_features = ["food_category", "day_of_week"]
    numerical_features = ["quantity_prepared", "people_served"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", "passthrough", numerical_features)
        ]
    )

    regressor = RandomForestRegressor(n_estimators=60, max_depth=6, random_state=42)
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", regressor)
    ])

    metrics = {}
    
    if total_records < RECOMMENDED_RECORDS_FOR_SPLIT:
        # Train on all, evaluate training error, note limited test set
        pipeline.fit(X, y)
        y_pred = pipeline.predict(X)
        mae = float(mean_absolute_error(y, y_pred))
        rmse = float(root_mean_squared_error(y, y_pred))
        r2 = float(r2_score(y, y_pred)) if np.var(y) > 0.001 else 0.0
        
        metrics = {
            "evaluation_type": f"Training evaluation ({total_records} samples; add {RECOMMENDED_RECORDS_FOR_SPLIT - total_records} more for train/test split)",
            "train_size": total_records,
            "test_size": 0,
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 2) if r2 is not None else None,
            "note": "Initial model trained. Performance will become more accurate as more records are logged."
        }
        status = "trained_initial"
        message = f"Model trained on {total_records} records. MAE: {metrics['mae']} kg, RMSE: {metrics['rmse']} kg."
    else:
        # Full Train-Test Split (80% train, 20% test)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(root_mean_squared_error(y_test, y_pred))
        
        # Calculate R² safely if test variance > 0
        r2 = None
        if len(y_test) > 1 and np.var(y_test) > 0.0001:
            r2 = round(float(r2_score(y_test, y_pred)), 2)
            
        metrics = {
            "evaluation_type": "Train/Test Split (80% / 20%)",
            "train_size": len(X_train),
            "test_size": len(X_test),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": r2,
            "note": "Model trained and evaluated on an independent test split."
        }
        status = "trained_evaluated"
        message = f"Scikit-Learn Random Forest Regressor trained successfully with {len(X_train)} train and {len(X_test)} test samples."

    return {
        "status": status,
        "message": message,
        "total_records": total_records,
        "pipeline": pipeline,
        "metrics": metrics,
        "categories": sorted(list(df["food_category"].unique())),
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    }

def predict_waste(model_result, input_data):
    """
    Predicts food waste quantity (kg) and waste percentage (%) for given inputs.
    Input format:
    {
        "food_category": "Main Course",
        "day_of_week": "Friday",
        "quantity_prepared": 50.0,
        "people_served": 120
    }
    """
    prepared = float(input_data.get("quantity_prepared", 0.0))
    people = int(input_data.get("people_served", 0))
    category = str(input_data.get("food_category", "Main Course"))
    day = str(input_data.get("day_of_week", "Monday"))
    
    if prepared <= 0:
        return {
            "predicted_wasted_kg": 0.0,
            "predicted_waste_percentage": 0.0,
            "method": "Validation",
            "explanation": "Prepared quantity must be greater than zero."
        }
        
    pipeline = model_result.get("pipeline")
    
    if pipeline is not None and model_result.get("status") in ("trained_initial", "trained_evaluated"):
        # Use trained ML Pipeline
        input_df = pd.DataFrame([{
            "food_category": category,
            "day_of_week": day,
            "quantity_prepared": prepared,
            "people_served": people
        }])
        
        pred_raw = pipeline.predict(input_df)[0]
        # Physically bound prediction: waste cannot be negative or exceed prepared quantity
        pred_wasted = max(0.0, min(float(pred_raw), prepared))
        pred_wasted = round(pred_wasted, 2)
        pred_pct = round((pred_wasted / prepared) * 100, 2)
        
        return {
            "predicted_wasted_kg": pred_wasted,
            "predicted_waste_percentage": pred_pct,
            "method": "Scikit-Learn Random Forest Regression",
            "is_ml_model": True,
            "metrics": model_result.get("metrics"),
            "explanation": f"Predicted using Scikit-Learn regression trained on your hotel's actual data."
        }
    else:
        # Fallback heuristic calculation if dataset is too small
        baseline_pct = model_result.get("baseline_waste_percentage", 12.0)
        if baseline_pct <= 0:
            baseline_pct = 12.0  # Industry standard estimate when zero history
            
        pred_wasted = round((prepared * baseline_pct) / 100.0, 2)
        pred_pct = round(baseline_pct, 2)
        
        return {
            "predicted_wasted_kg": pred_wasted,
            "predicted_waste_percentage": pred_pct,
            "method": "Baseline Formula Estimate (Insufficient records for ML training)",
            "is_ml_model": False,
            "metrics": None,
            "explanation": f"Estimated using baseline historical waste percentage ({pred_pct}%). Train a dedicated ML model once you record {model_result.get('min_needed', MIN_RECORDS_FOR_ML)} or more meals."
        }
