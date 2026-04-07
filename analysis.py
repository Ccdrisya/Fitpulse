# analysis.py
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings("ignore")

# --- Constants from Milestone 3 ---
THRESHOLDS = {
    "heart_rate_bpm": {"high": 120, "low": 45, "sleep_high": 90},
    "spo2_pct": {"low": 94},
    "steps": {"sleep_active": 50},
}

# --- Milestone 1 & 3 Logic ---

def preprocess_data(df):
    """Normalize timestamps and sort."""
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'ds'})
    
    # Try to find a date column
    date_cols = ['ds', 'date', 'time', 'entry_time']
    found_col = next((c for c in date_cols if c in df.columns), None)
    
    if not found_col:
        return df # Return as is if no date found
    
    df[found_col] = pd.to_datetime(df[found_col], errors='coerce')
    df = df.dropna(subset=[found_col])
    df = df.sort_values(found_col).reset_index(drop=True)
    return df

def rule_based_detection(df):
    """Apply rule-based thresholds."""
    df = df.copy()
    
    # Ensure columns exist
    for col in ['heart_rate_bpm', 'heart_rate', 'hr']:
        if col in df.columns:
            df['heart_rate_bpm'] = df[col]
            break
            
    for col in ['steps', 'step_count']:
        if col in df.columns:
            df['steps'] = df[col]
            break
            
    for col in ['spo2_pct', 'spo2', 'oxygen']:
        if col in df.columns:
            df['spo2_pct'] = df[col]
            break

    # Default values if columns missing
    if 'heart_rate_bpm' not in df.columns: df['heart_rate_bpm'] = 70
    if 'steps' not in df.columns: df['steps'] = 0
    if 'spo2_pct' not in df.columns: df['spo2_pct'] = 98

    # Rules
    df["rule_tachycardia"] = (df["heart_rate_bpm"] > THRESHOLDS["heart_rate_bpm"]["high"]).astype(int)
    df["rule_bradycardia"] = (df["heart_rate_bpm"] < THRESHOLDS["heart_rate_bpm"]["low"]).astype(int)
    df["rule_low_spo2"] = (df["spo2_pct"] < THRESHOLDS["spo2_pct"]["low"]).astype(int)
    
    # Sleep logic (simplified for web app)
    if "sleeping" in df.columns:
        df["rule_sleep_steps"] = ((df["sleeping"] == 1) & (df["steps"] > THRESHOLDS["steps"]["sleep_active"])).astype(int)
    else:
        df["rule_sleep_steps"] = 0

    rule_cols = ["rule_tachycardia", "rule_bradycardia", "rule_low_spo2", "rule_sleep_steps"]
    df["rule_anomaly"] = df[rule_cols].any(axis=1).astype(int)
    return df

def run_prophet_anomaly(df, metric='heart_rate_bpm'):
    """Run Prophet and return anomalies."""
    if metric not in df.columns or len(df) < 10:
        return df
    
    prophet_df = df[[metric]].copy()
    prophet_df = prophet_df.reset_index()
    prophet_df.columns = ['ds', 'y']
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
    prophet_df = prophet_df.dropna()

    if len(prophet_df) < 10:
        return df

    try:
        m = Prophet(daily_seasonality=True).fit(prophet_df)
        future = m.make_future_dataframe(periods=0)
        forecast = m.predict(future)
        
        # Merge back
        forecast = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        df_temp = prophet_df.merge(forecast, on='ds')
        df_temp['is_anomaly'] = ((df_temp['y'] > df_temp['yhat_upper']) | (df_temp['y'] < df_temp['yhat_lower'])).astype(int)
        
        # Map back to original df index
        df['prophet_anomaly'] = 0
        df.loc[df_temp['ds'].values, 'prophet_anomaly'] = df_temp['is_anomaly'].values
    except Exception as e:
        print(f"Prophet error: {e}")
        df['prophet_anomaly'] = 0
        
    return df

def compute_severity(df):
    """Combine rules and prophet into a final score."""
    df = df.copy()
    
    # Ensure columns exist
    if 'prophet_anomaly' not in df.columns: df['prophet_anomaly'] = 0
    
    score_cols = ["rule_anomaly", "prophet_anomaly"]
    df["anomaly_score"] = df[score_cols].sum(axis=1)
    
    def get_severity(score):
        if score == 0: return "Normal"
        elif score == 1: return "Warning"
        else: return "Critical"
    
    df["severity"] = df["anomaly_score"].apply(get_severity)
    return df

def process_full_analysis(df):
    def get_status(row):
        hr = row.get('heart_rate_bpm', 0)
        steps = row.get('steps', 0)
        sleep = row.get('sleep', 0)

        # 🚨 CRITICAL CONDITIONS
        if hr > 110 or hr < 50 or steps < 1000 or sleep < 4:
            return "Critical"

        # ⚠️ WARNING CONDITIONS
        elif hr > 90 or hr < 60 or steps < 5000 or sleep < 6:
            return "Warning"

        # ✅ HEALTHY
        else:
            return "Healthy"

    df['severity'] = df.apply(get_status, axis=1)
    return df