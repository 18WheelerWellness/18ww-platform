import csv
import os


def calculate_cost_per_fte(incurred_losses: float, man_hours: float) -> float:
    if man_hours == 0:
        return 0.0
    return (incurred_losses * 2000) / man_hours


def run_cost_per_fte() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    input_file = os.path.join(base_dir, "data", "inputs", "company_inputs.csv")
    output_file = os.path.join(base_dir, "data", "outputs", "cost_per_fte_results.csv")

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Input file not found: {input_file}. "
            "Create data/inputs/company_inputs.csv first."
        )

    results = []

    with open(input_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required_cols = {"company", "period", "incurred_losses", "man_hours"}
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Missing required columns in company_inputs.csv: {sorted(missing)}"
            )

        for row in reader:
            company = row["company"]
            period = row["period"]
            incurred_losses = float(row["incurred_losses"])
            man_hours = float(row["man_hours"])

            cost_per_fte = calculate_cost_per_fte(incurred_losses, man_hours)

            results.append({
                "company": company,
                "period": period,
                "incurred_losses": incurred_losses,
                "man_hours": man_hours,
                "cost_per_fte": round(cost_per_fte, 2),
            })

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "company",
            "period",
            "incurred_losses",
            "man_hours",
            "cost_per_fte",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return output_file