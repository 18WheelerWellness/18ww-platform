def validate_required_columns(df, required_columns):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True


def validate_driver_file(df):
    required = [
        "driver_id",
        "first_name",
        "last_name",
    ]
    return validate_required_columns(df, required)


def validate_rom_file(df):
    required = [
        "driver_id",
        "movement",
    ]
    return validate_required_columns(df, required)


def validate_claim_file(df):
    required = [
        "driver_id",
        "claim_date",
        "body_part",
    ]
    return validate_required_columns(df, required)