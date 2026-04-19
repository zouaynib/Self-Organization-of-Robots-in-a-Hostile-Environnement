# Group: XX | Date: 2026-04-19 | Members: ...
"""run.py — Headless simulation runner."""

import argparse
import csv
from src.model import RobotMission


def main():
    parser = argparse.ArgumentParser(description="Robot Mission — Headless Simulation")
    parser.add_argument("--steps",   type=int,  default=200)
    parser.add_argument("--csv",     action="store_true")
    parser.add_argument("--no-comm", action="store_true")
    parser.add_argument("--seed",    type=int,  default=42)
    args = parser.parse_args()

    print("=" * 60)
    print("Self-organization of Robots — Headless Simulation")
    print("=" * 60)
    print(f"  Steps        : {args.steps}")
    print(f"  Communication: {not args.no_comm}")
    print(f"  Vision radius: {2} (5×5 patch)")
    print("-" * 60)

    model = RobotMission(communication=not args.no_comm, seed=args.seed)

    for step in range(1, args.steps + 1):
        model.step()
        wc = model.waste_counts
        total = wc["green"] + wc["yellow"] + wc["red"]

        if step % 50 == 0:
            print(
                f"  Step {step:4d} | "
                f"Green: {wc['green']:3d}  "
                f"Yellow: {wc['yellow']:3d}  "
                f"Red: {wc['red']:3d}  "
                f"Disposed: {wc['disposed']:3d}  "
                f"Total: {total:3d}"
            )
        if total == 0:
            print(f"\n✅  All waste disposed at step {step}!")
            break

    print("-" * 60)
    print("Simulation complete.")

    if args.csv:
        df = model.datacollector.get_model_vars_dataframe()
        df.to_csv("results.csv")
        print("Metrics saved to results.csv")


if __name__ == "__main__":
    main()
