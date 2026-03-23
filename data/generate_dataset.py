import pandas as pd
import numpy as np

def generate_fitness_data(days=60):
    # Generate timestamps (5-minute intervals)
    timestamps = pd.date_range(
        end=pd.Timestamp.now(),
        periods=days * 288,  # 288 = 24h * 12 (5-min intervals)
        freq="5min"
    )

    np.random.seed(42)

    heart_rate = np.random.normal(loc=75, scale=10, size=len(timestamps))
    heart_rate = np.clip(heart_rate, 45, 140)

    steps = np.random.poisson(lam=5, size=len(timestamps))
    spo2 = np.random.normal(loc=97, scale=1, size=len(timestamps))
    spo2 = np.clip(spo2, 90, 100)

    sleeping = np.array([
        1 if (t.hour >= 23 or t.hour <= 6) else 0
        for t in timestamps
    ])

    df = pd.DataFrame({
        "timestamp": timestamps,
        "heart_rate_bpm": heart_rate.astype(int),
        "steps": steps,
        "spo2_pct": spo2.round(1),
        "sleeping": sleeping
    })

    return df


def generate_daily_summary(df):
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date

    summary = df.groupby("date").agg({
        "heart_rate_bpm": "mean",
        "steps": "sum",
        "spo2_pct": "mean"
    }).reset_index()

    return summary