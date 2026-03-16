# Group: [Your Group Number]
# Date: 2026-03-16
# Members: [Names]
#
# Launch: python run.py
# Or for visualization: solara run server.py

from model import RobotMission


def run_headless(steps=200):
    """Run the simulation without visualization and print results."""
    model = RobotMission()
    for i in range(steps):
        model.step()
        if (i + 1) % 20 == 0:
            data = model.datacollector.get_model_vars_dataframe().iloc[-1]
            print(
                f"Step {i+1:>4d} | "
                f"Green: {int(data['Green Waste']):>2d} | "
                f"Yellow: {int(data['Yellow Waste']):>2d} | "
                f"Red: {int(data['Red Waste']):>2d} | "
                f"Stored: {int(data['Stored Waste']):>2d}"
            )

    print("\n--- Final ---")
    final = model.datacollector.get_model_vars_dataframe().iloc[-1]
    print(f"Green waste remaining:  {int(final['Green Waste'])}")
    print(f"Yellow waste remaining: {int(final['Yellow Waste'])}")
    print(f"Red waste remaining:    {int(final['Red Waste'])}")
    print(f"Waste stored (disposed):{int(final['Stored Waste'])}")


if __name__ == "__main__":
    run_headless()
