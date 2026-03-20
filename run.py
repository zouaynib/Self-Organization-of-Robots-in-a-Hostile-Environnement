# =============================================================================
# run.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================
# Headless simulation runner.  Runs the model for N steps without the
# Solara GUI, then prints a summary and optionally saves a CSV of metrics.
#
# Usage
# -----
#   python run.py                    # 200 steps, no CSV
#   python run.py --steps 500        # 500 steps
#   python run.py --steps 300 --csv  # save results.csv

import argparse
import sys

from model import RobotMission


def run(steps: int = 200, save_csv: bool = False, communication: bool = True):
    print("=" * 60)
    print("Self-organization of Robots — Headless Simulation")
    print("=" * 60)
    print(f"  Steps        : {steps}")
    print(f"  Communication: {communication}")
    print("-" * 60)

    model = RobotMission(communication=communication)

    for step in range(1, steps + 1):
        model.step()

        # Progress every 50 steps
        if step % 50 == 0 or step == steps:
            wc = model.waste_counts
            total = wc["green"] + wc["yellow"] + wc["red"]
            print(
                f"  Step {step:>4d} | "
                f"Green: {wc['green']:>3d}  "
                f"Yellow: {wc['yellow']:>3d}  "
                f"Red: {wc['red']:>3d}  "
                f"Disposed: {wc['disposed']:>3d}  "
                f"Total: {total:>3d}"
            )

        # Early stopping: all waste disposed
        if model.waste_counts["disposed"] > 0 and \
           model.waste_counts["green"] == 0 and \
           model.waste_counts["yellow"] == 0 and \
           model.waste_counts["red"] == 0:
            print(f"\n✅  All waste disposed at step {step}!")
            break

    print("-" * 60)
    print("Simulation complete.")

    if save_csv:
        df = model.datacollector.get_model_vars_dataframe()
        df.to_csv("results.csv")
        print("📊  Metrics saved to results.csv")

    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Robot Mission simulation headlessly."
    )
    parser.add_argument(
        "--steps", type=int, default=200,
        help="Number of simulation steps (default: 200)"
    )
    parser.add_argument(
        "--csv", action="store_true",
        help="Save data-collector output to results.csv"
    )
    parser.add_argument(
        "--no-comm", action="store_true",
        help="Disable inter-agent communication"
    )
    args = parser.parse_args()

    run(steps=args.steps, save_csv=args.csv, communication=not args.no_comm)