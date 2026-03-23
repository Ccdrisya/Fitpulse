"""
=============================================================
FitPulse — Health Anomaly Detection (Main Runner)
=============================================================
Runs all 4 milestones end-to-end.

Usage:
    python main.py              # Run all milestones
    python main.py --m1         # Only Milestone 1
    python main.py --m1 --m2    # Milestones 1 & 2
    
Launch dashboard:
    streamlit run modules/milestone4_dashboard.py
=============================================================
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.generate_dataset import generate_fitness_data, generate_daily_summary
from modules.milestone1_preprocessing import run_milestone1
from modules.milestone2_modeling import run_milestone2
from modules.milestone3_anomaly import run_milestone3


def main():
    parser = argparse.ArgumentParser(description="FitPulse Anomaly Detection Pipeline")
    parser.add_argument("--m1", action="store_true", help="Run Milestone 1: Preprocessing")
    parser.add_argument("--m2", action="store_true", help="Run Milestone 2: Modeling")
    parser.add_argument("--m3", action="store_true", help="Run Milestone 3: Anomaly Detection")
    parser.add_argument("--all", action="store_true", default=True, help="Run all milestones (default)")
    args = parser.parse_args()

    run_all = not any([args.m1, args.m2, args.m3]) or args.all

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   FitPulse — Health Anomaly Detection System        ║")
    print("╚══════════════════════════════════════════════════════╝")

    # ── Generate Dataset ──
    if not os.path.exists("data/fitness_data_raw.csv"):
        print("\n📦 Generating synthetic fitness dataset...")
        df_raw = generate_fitness_data(days=60)
        os.makedirs("data", exist_ok=True)
        df_raw.to_csv("data/fitness_data_raw.csv", index=False)
        daily = generate_daily_summary(df_raw)
        daily.to_csv("data/fitness_data_daily.csv", index=False)
        print(f"   ✅ Dataset ready: {len(df_raw)} records")
    else:
        print("\n📂 Using existing dataset: data/fitness_data_raw.csv")

    os.makedirs("outputs", exist_ok=True)

    # ── Milestone 1 ──
    df_clean = None
    if run_all or args.m1:
        df_clean = run_milestone1("data/fitness_data_raw.csv")

    # ── Milestone 2 ──
    m2_results = None
    if run_all or args.m2:
        import pandas as pd
        if df_clean is None:
            df_clean = pd.read_csv("outputs/cleaned_data.csv", index_col=0, parse_dates=True)
        m2_results = run_milestone2(df_clean)

    # ── Milestone 3 ──
    if run_all or args.m3:
        import pandas as pd
        if df_clean is None:
            df_clean = pd.read_csv("outputs/cleaned_data.csv", index_col=0, parse_dates=True)
        feat_df = m2_results["features"] if m2_results else None
        prophet = m2_results["prophet"] if m2_results else None
        df_anomaly = run_milestone3(df_clean, feat_df=feat_df, prophet_results=prophet)

    # ── Summary ──
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   ✅ ALL MILESTONES COMPLETE                        ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║  Output files in: ./outputs/                        ║")
    print("║  • cleaned_data.csv          (Milestone 1)          ║")
    print("║  • milestone1_preview.png                           ║")
    print("║  • feature_matrix.csv        (Milestone 2)          ║")
    print("║  • prophet_heart_rate_bpm.png                       ║")
    print("║  • prophet_steps.png                                ║")
    print("║  • prophet_spo2_pct.png                             ║")
    print("║  • milestone2_clusters.png                          ║")
    print("║  • anomaly_results.csv       (Milestone 3)          ║")
    print("║  • milestone3_heartrate.png                         ║")
    print("║  • milestone3_sleep.png                             ║")
    print("║  • milestone3_steps_spo2.png                        ║")
    print("║  • milestone3_summary.png                           ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║  Launch Dashboard (Milestone 4):                    ║")
    print("║  streamlit run modules/milestone4_dashboard.py      ║")
    print("╚══════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
