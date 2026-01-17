#!/usr/bin/env python3
"""
Workout Data Export

Exports Apple Health workout data to CSV for dashboard use.
Includes all workout sources (Apple Watch, Strava, Strong, etc.)
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import os
import re

import pandas as pd


def clean_workout_type(raw_type: str) -> str:
    """
    Convert HKWorkoutActivityType names to readable format.

    Example: HKWorkoutActivityTypeCycling -> Cycling
    """
    # Remove the prefix
    cleaned = raw_type.replace("HKWorkoutActivityType", "")

    # Add spaces before capital letters (for compound names)
    # e.g., TraditionalStrengthTraining -> Traditional Strength Training
    cleaned = re.sub(r'(?<!^)(?=[A-Z])', ' ', cleaned)

    return cleaned


def parse_workout_data(xml_path: str) -> pd.DataFrame:
    """
    Parse workout records from Apple Health export XML.

    Args:
        xml_path: Path to export.xml file

    Returns:
        DataFrame with workout data
    """
    print(f"Parsing XML file: {xml_path}")

    records = []

    # Use iterparse for memory-efficient parsing of large XML
    context = ET.iterparse(xml_path, events=("end",))

    for event, elem in context:
        if elem.tag == "Workout":
            workout_type = elem.get("workoutActivityType", "")
            duration = elem.get("duration")
            duration_unit = elem.get("durationUnit", "min")
            source_name = elem.get("sourceName", "")
            start_date = elem.get("startDate")

            if start_date and duration:
                records.append({
                    "timestamp": start_date,
                    "duration_minutes": float(duration) if duration_unit == "min" else float(duration) / 60,
                    "workout_type": clean_workout_type(workout_type),
                    "source": source_name
                })

        # Clear element to save memory
        elem.clear()

    print(f"Found {len(records)} workout records")

    df = pd.DataFrame(records)

    if not df.empty:
        # Parse timestamp - Apple Health format: 2025-11-16 08:30:00 -0800
        df["timestamp"] = pd.to_datetime(df["timestamp"].str.replace(r" [-+]\d{4}$", "", regex=True))
        df = df.sort_values("timestamp")

    return df


def filter_last_six_months(df: pd.DataFrame) -> pd.DataFrame:
    """Filter data to last 6 months (July 16, 2025 onwards)."""
    cutoff_date = datetime(2025, 7, 16)
    filtered = df[df["timestamp"] >= cutoff_date].copy()
    print(f"Filtered to {len(filtered)} records from {cutoff_date.date()} onwards")
    return filtered


def export_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """
    Export workout data to CSV.

    Args:
        df: DataFrame with workout data
        output_path: Path to save CSV file
    """
    export_df = df.copy()

    # Format timestamp as ISO format (without timezone)
    export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Round duration to 2 decimal places
    export_df["duration_minutes"] = export_df["duration_minutes"].round(2)

    # Save to CSV
    export_df.to_csv(output_path, index=False)
    print(f"\nCSV exported to: {output_path}")
    print(f"  Total records: {len(export_df)}")

    # Print summary by workout type
    print("\nWorkouts by type:")
    type_counts = df["workout_type"].value_counts()
    for workout_type, count in type_counts.items():
        print(f"  {workout_type}: {count}")

    # Print summary by source
    print("\nWorkouts by source:")
    source_counts = df["source"].value_counts()
    for source, count in source_counts.items():
        print(f"  {source}: {count}")


def main():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(script_dir, "apple_health_export", "export.xml")
    csv_output_path = os.path.join(script_dir, "workout_data.csv")

    # Parse workout data
    df = parse_workout_data(xml_path)

    if df.empty:
        print("No workout data found!")
        return

    # Filter to last 6 months
    df = filter_last_six_months(df)

    if df.empty:
        print("No data in the specified date range!")
        return

    # Export to CSV
    export_to_csv(df, csv_output_path)


if __name__ == "__main__":
    main()
