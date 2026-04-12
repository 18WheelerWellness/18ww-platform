import csv
import os


def calculate_savings(old_cost_per_fte: float, new_cost_per_fte: float, current_fte_count: float) -> float:
    return (old_cost_per_fte - new_cost_per_fte) * current_fte_count


def run_savings_to_date() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    input_file = os.path.join(base_dir, "data", "inputs", "savings_inputs.csv")
    output_file = os.path.join(base_dir, "data", "outputs", "savings_to_date_results.csv")

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Input file not found: {input_file}. "
            "Create data/inputs/savings_inputs.csv first."
        )

    results = []

    with open(input_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required_cols = {
            "company",
            "old_period",
            "new_period",
            "old_cost_per_fte",
            "new_cost_per_fte",
            "current_fte_count",
        }
        missing = required_cols - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Missing required columns in savings_inputs.csv: {sorted(missing)}"
            )

        for row in reader:
            company = row["company"]
            old_period = row["old_period"]
            new_period = row["new_period"]
            old_cost = float(row["old_cost_per_fte"])
            new_cost = float(row["new_cost_per_fte"])
            fte_count = float(row["current_fte_count"])

            savings = calculate_savings(old_cost, new_cost, fte_count)

            results.append({
                "company": company,
                "old_period": old_period,
                "new_period": new_period,
                "old_cost_per_fte": round(old_cost, 2),
                "new_cost_per_fte": round(new_cost, 2),
                "current_fte_count": round(fte_count, 2),
                "savings_to_date": round(savings, 2),
            })

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "company",
            "old_period",
            "new_period",
            "old_cost_per_fte",
            "new_cost_per_fte",
            "current_fte_count",
            "savings_to_date",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return output_file