def fleet_risk_summary(scored_df):
    total_drivers = len(scored_df)

    green_count = len(scored_df[scored_df["risk_tier"] == "green"])
    yellow_count = len(scored_df[scored_df["risk_tier"] == "yellow"])
    red_count = len(scored_df[scored_df["risk_tier"] == "red"])

    return {
        "total_drivers": total_drivers,
        "green_count": green_count,
        "yellow_count": yellow_count,
        "red_count": red_count,
    }


def top_risk_drivers(scored_df, n=10):
    return scored_df.sort_values("total_score", ascending=False).head(n)