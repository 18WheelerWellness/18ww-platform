import pandas as pd


def load_csv(path):
    return pd.read_csv(path)


def load_excel(path, sheet_name=0):
    return pd.read_excel(path, sheet_name=sheet_name)


def load_driver_file(path):
    if path.lower().endswith(".csv"):
        return load_csv(path)
    elif path.lower().endswith(".xlsx"):
        return load_excel(path)
    else:
        raise ValueError("Unsupported driver file type. Use CSV or XLSX.")


def load_rom_file(path):
    if path.lower().endswith(".csv"):
        return load_csv(path)
    elif path.lower().endswith(".xlsx"):
        return load_excel(path)
    else:
        raise ValueError("Unsupported ROM file type. Use CSV or XLSX.")


def load_claim_file(path):
    if path.lower().endswith(".csv"):
        return load_csv(path)
    elif path.lower().endswith(".xlsx"):
        return load_excel(path)
    else:
        raise ValueError("Unsupported claim file type. Use CSV or XLSX.")