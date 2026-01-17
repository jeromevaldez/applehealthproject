#!/usr/bin/env python3
"""
Low Heart Rate Events Timeline Visualization

Visualizes Apple Watch low heart rate events (HR < 40 bpm for 10+ minutes)
from Apple Health export as a timeline.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import webbrowser
import os

import pandas as pd
import plotly.graph_objects as go


def parse_low_hr_events(xml_path: str) -> pd.DataFrame:
    """
    Parse low heart rate event records from Apple Health export XML.

    These are HKCategoryTypeIdentifierLowHeartRateEvent records that Apple Watch
    creates when heart rate is below 40 bpm for 10+ minutes.

    Args:
        xml_path: Path to export.xml file

    Returns:
        DataFrame with start_time, end_time, and duration_minutes columns
    """
    print(f"Parsing XML file for low heart rate events: {xml_path}")

    records = []

    # Use iterparse for memory-efficient parsing of large XML
    context = ET.iterparse(xml_path, events=("end",))

    for event, elem in context:
        if elem.tag == "Record" and elem.get("type") == "HKCategoryTypeIdentifierLowHeartRateEvent":
            start_date = elem.get("startDate")
            end_date = elem.get("endDate")
            source_name = elem.get("sourceName", "")

            if start_date and end_date:
                records.append({
                    "start_time": start_date,
                    "end_time": end_date,
                    "source": source_name
                })

        # Clear element to save memory
        elem.clear()

    print(f"Found {len(records)} low heart rate events")

    df = pd.DataFrame(records)

    if not df.empty:
        # Parse timestamps - Apple Health format: 2025-11-16 08:30:00 -0800
        df["start_time"] = pd.to_datetime(df["start_time"].str.replace(r" [-+]\d{4}$", "", regex=True))
        df["end_time"] = pd.to_datetime(df["end_time"].str.replace(r" [-+]\d{4}$", "", regex=True))

        # Calculate duration in minutes
        df["duration_minutes"] = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60

        df = df.sort_values("start_time")

    return df


def create_timeline_visualization(df: pd.DataFrame, output_path: str) -> None:
    """
    Create interactive timeline visualization of low heart rate events.

    Args:
        df: DataFrame with start_time, end_time, duration_minutes columns
        output_path: Path to save HTML file
    """
    print(f"\nCreating timeline visualization...")
    print(f"Date range: {df['start_time'].min().date()} to {df['start_time'].max().date()}")
    print(f"Average duration: {df['duration_minutes'].mean():.1f} minutes")
    print(f"Max duration: {df['duration_minutes'].max():.1f} minutes")

    # Create figure
    fig = go.Figure()

    # Add events as bars on timeline
    # Each event is a horizontal bar from start_time to end_time
    # Use y-axis to show time of day for pattern analysis

    # Extract hour of day for y-axis positioning
    df["hour_of_day"] = df["start_time"].dt.hour + df["start_time"].dt.minute / 60

    # Color by duration (longer = more intense red)
    max_duration = df["duration_minutes"].max()

    # Create hover text
    hover_text = [
        f"<b>{row['start_time'].strftime('%Y-%m-%d')}</b><br>"
        f"Start: {row['start_time'].strftime('%H:%M:%S')}<br>"
        f"End: {row['end_time'].strftime('%H:%M:%S')}<br>"
        f"Duration: {row['duration_minutes']:.1f} minutes"
        for _, row in df.iterrows()
    ]

    # Add scatter plot - each point is an event
    fig.add_trace(go.Scatter(
        x=df["start_time"],
        y=df["hour_of_day"],
        mode="markers",
        name="Low HR Event",
        marker=dict(
            size=10 + (df["duration_minutes"] / max_duration) * 10,  # Size by duration
            color=df["duration_minutes"],
            colorscale="Reds",
            colorbar=dict(
                title="Duration (min)",
                x=1.02
            ),
            line=dict(width=1, color="darkred")
        ),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_text
    ))

    # Add monthly aggregation as a secondary view
    df["month"] = df["start_time"].dt.to_period("M")
    monthly_counts = df.groupby("month").size().reset_index(name="count")
    monthly_counts["month_start"] = monthly_counts["month"].dt.to_timestamp()

    # Layout
    fig.update_layout(
        title=dict(
            text="Low Heart Rate Events Timeline<br><sup>Heart rate below 40 bpm for 10+ minutes</sup>",
            x=0.5,
            xanchor="center",
            font=dict(size=20)
        ),
        xaxis_title="Date",
        yaxis_title="Time of Day (hour)",
        hovermode="closest",
        template="plotly_white",
        height=600,
        yaxis=dict(
            tickmode="array",
            tickvals=[0, 4, 8, 12, 16, 20, 24],
            ticktext=["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM", "12 AM"],
            range=[0, 24]
        )
    )

    # Add range slider for navigation
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ])
        )
    )

    # Save to HTML
    fig.write_html(output_path, include_plotlyjs=True, full_html=True)
    print(f"\nTimeline visualization saved to: {output_path}")


def print_summary_stats(df: pd.DataFrame) -> None:
    """Print summary statistics about low heart rate events."""
    print("\n" + "="*60)
    print("LOW HEART RATE EVENTS SUMMARY")
    print("="*60)

    print(f"\nTotal events: {len(df)}")
    print(f"Date range: {df['start_time'].min().date()} to {df['start_time'].max().date()}")

    # Duration stats
    print(f"\nDuration statistics:")
    print(f"  Average: {df['duration_minutes'].mean():.1f} minutes")
    print(f"  Median: {df['duration_minutes'].median():.1f} minutes")
    print(f"  Min: {df['duration_minutes'].min():.1f} minutes")
    print(f"  Max: {df['duration_minutes'].max():.1f} minutes")

    # Time of day distribution
    df["hour"] = df["start_time"].dt.hour
    print(f"\nTime of day distribution:")
    print(f"  Night (12 AM - 6 AM): {len(df[(df['hour'] >= 0) & (df['hour'] < 6)])} events")
    print(f"  Morning (6 AM - 12 PM): {len(df[(df['hour'] >= 6) & (df['hour'] < 12)])} events")
    print(f"  Afternoon (12 PM - 6 PM): {len(df[(df['hour'] >= 12) & (df['hour'] < 18)])} events")
    print(f"  Evening (6 PM - 12 AM): {len(df[(df['hour'] >= 18) & (df['hour'] < 24)])} events")

    # Monthly trend
    df["month"] = df["start_time"].dt.to_period("M")
    monthly = df.groupby("month").size()
    print(f"\nMonthly event counts (last 12 months):")
    for month, count in monthly.tail(12).items():
        print(f"  {month}: {count} events")

    print("="*60)


def main():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(script_dir, "apple_health_export", "export.xml")
    html_output_path = os.path.join(script_dir, "low_hr_events_timeline.html")
    csv_output_path = os.path.join(script_dir, "low_hr_events.csv")

    # Parse low heart rate events
    df = parse_low_hr_events(xml_path)

    if df.empty:
        print("No low heart rate events found!")
        return

    # Print summary statistics
    print_summary_stats(df)

    # Export to CSV
    export_df = df[["start_time", "end_time", "duration_minutes", "source"]].copy()
    export_df["start_time"] = export_df["start_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    export_df["end_time"] = export_df["end_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    export_df.to_csv(csv_output_path, index=False)
    print(f"\nCSV exported to: {csv_output_path}")

    # Create visualization
    create_timeline_visualization(df, html_output_path)

    # Open in browser
    print("Opening in browser...")
    webbrowser.open(f"file://{html_output_path}")


if __name__ == "__main__":
    main()
