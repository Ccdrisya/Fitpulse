# analysis.py
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────
THRESHOLDS = {
    "heart_rate_bpm": {
        "critical_high": 120,   # Tachycardia → Critical
        "warning_high":  100,   # Elevated HR  → Warning
        "critical_low":   45,   # Bradycardia  → Critical
        "warning_low":    55,   # Low HR       → Warning
        "sleep_high":     90,   # HR too high during sleep → Warning
    },
    "spo2_pct": {
        "critical_low": 94,     # Low SpO2 → Critical
        "warning_low":  96,     # Borderline SpO2 → Warning
    },
    "sleep": {
        "critical_low": 5.0,    # Very low sleep → Critical
        "warning_low":  6.0,    # Low sleep → Warning
    },
    "steps": {
        "sleep_active": 50,     # Steps during sleep → Warning
    },
}


def preprocess_data(df):
    """Normalize timestamps and sort."""
    df = df.copy()

    # Rename timestamp → ds if needed
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'ds'})

    date_cols = ['ds', 'date', 'time', 'entry_time']
    found_col = next((c for c in date_cols if c in df.columns), None)

    if found_col:
        df[found_col] = pd.to_datetime(df[found_col], errors='coerce')
        df = df.dropna(subset=[found_col])
        df = df.sort_values(found_col).reset_index(drop=True)

    return df


def _resolve_columns(df):
    """Normalise column names so downstream logic finds them."""
    df = df.copy()

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

    for col in ['sleep', 'sleep_hours', 'sleep_duration']:
        if col in df.columns:
            df['sleep'] = df[col]
            break

    # Defaults for completely missing columns
    if 'heart_rate_bpm' not in df.columns:
        df['heart_rate_bpm'] = 70
    if 'steps' not in df.columns:
        df['steps'] = 0
    if 'spo2_pct' not in df.columns:
        df['spo2_pct'] = 98
    if 'sleep' not in df.columns:
        df['sleep'] = 7

    return df


def rule_based_detection(df):
    """
    Flag anomalies with two severity tiers: Warning and Critical.

    Flags set:
        flag_critical  – any Critical-level rule triggered
        flag_warning   – any Warning-level rule triggered (but not Critical)
    """
    df = _resolve_columns(df)
    T = THRESHOLDS

    hr  = df['heart_rate_bpm']
    sp  = df['spo2_pct']
    sl  = df['sleep']

    # ── Critical rules ──
    df['rule_tachycardia']  = (hr >= T['heart_rate_bpm']['critical_high']).astype(int)
    df['rule_bradycardia']  = (hr <= T['heart_rate_bpm']['critical_low']).astype(int)
    df['rule_low_spo2']     = (sp <  T['spo2_pct']['critical_low']).astype(int)
    df['rule_sleep_critical']= (sl <  T['sleep']['critical_low']).astype(int)

    # ── Warning rules ──
    df['rule_hr_elevated']  = (
        (hr >= T['heart_rate_bpm']['warning_high']) &
        (hr <  T['heart_rate_bpm']['critical_high'])
    ).astype(int)

    df['rule_hr_low_warn']  = (
        (hr <= T['heart_rate_bpm']['warning_low']) &
        (hr >  T['heart_rate_bpm']['critical_low'])
    ).astype(int)

    df['rule_spo2_warn']    = (
        (sp >= T['spo2_pct']['critical_low']) &
        (sp <  T['spo2_pct']['warning_low'])
    ).astype(int)

    df['rule_sleep_warn']   = (
        (sl >= T['sleep']['critical_low']) &
        (sl <  T['sleep']['warning_low'])
    ).astype(int)

    # Sleep-activity anomaly (Warning only)
    if 'sleeping' in df.columns:
        df['rule_sleep_steps'] = (
            (df['sleeping'] == 1) &
            (df['steps'] > T['steps']['sleep_active'])
        ).astype(int)
        df['rule_sleep_hr'] = (
            (df['sleeping'] == 1) &
            (hr > T['heart_rate_bpm']['sleep_high'])
        ).astype(int)
    else:
        df['rule_sleep_steps'] = 0
        df['rule_sleep_hr']    = 0

    critical_cols = ['rule_tachycardia', 'rule_bradycardia',
                     'rule_low_spo2',    'rule_sleep_critical']
    warning_cols  = ['rule_hr_elevated', 'rule_hr_low_warn',
                     'rule_spo2_warn',   'rule_sleep_warn',
                     'rule_sleep_steps', 'rule_sleep_hr']

    df['flag_critical'] = df[critical_cols].any(axis=1).astype(int)
    df['flag_warning']  = (
        df[warning_cols].any(axis=1) & (df['flag_critical'] == 0)
    ).astype(int)
    df['rule_anomaly']  = (df['flag_critical'] | df['flag_warning']).astype(int)

    return df


def compute_severity(df):
    """
    Map flags → status strings that match the CSS badge classes:
        'Critical'  →  .critical  (red)
        'Warning'   →  .warning   (orange/yellow)
        'Healthy'   →  .healthy   (green)
    """
    df = df.copy()

    def _status(row):
        if row.get('flag_critical', 0):
            return 'Critical'
        if row.get('flag_warning', 0):
            return 'Warning'
        return 'Healthy'

    df['severity'] = df.apply(_status, axis=1)

    # Keep a numeric anomaly_score for compatibility with Streamlit dashboard
    df['anomaly_score'] = df['flag_critical'] * 2 + df['flag_warning']
    df['final_anomaly'] = (df['anomaly_score'] > 0).astype(int)

    return df


def process_full_analysis(df):
    """Full pipeline: preprocess → rules → severity."""
    df = preprocess_data(df)
    df = rule_based_detection(df)
    df = compute_severity(df)
    return df