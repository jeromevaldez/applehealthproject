#!/usr/bin/env python3
"""
Compare sleep data from Apple Watch vs Eight Sleep for the last 6 months.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def parse_sleep_data(xml_path: str) -> pd.DataFrame:
    """Parse all sleep analysis records from Apple Health export."""
    print(f"Parsing sleep data from: {xml_path}")

    records = []
    context = ET.iterparse(xml_path, events=("end",))

    for event, elem in context:
        if elem.tag == "Record" and elem.get("type") == "HKCategoryTypeIdentifierSleepAnalysis":
            source = elem.get("sourceName", "")

            # Only keep Apple Watch and Eight Sleep
            # Note: Apple Watch source has special characters (curly apostrophe and non-breaking space)
            if "Apple" in source and "Watch" in source:
                source_type = "Apple Watch"
            elif "Eight Sleep" in source:
                source_type = "Eight Sleep"
            else:
                continue

            if True:  # Keep the indentation level
                start_date = elem.get("startDate")
                end_date = elem.get("endDate")
                value = elem.get("value", "")

                if start_date and end_date:
                    records.append({
                        "source": source_type,
                        "start_time": start_date,
                        "end_time": end_date,
                        "stage": value.replace("HKCategoryValueSleepAnalysis", "")
                    })

        elem.clear()

    print(f"Found {len(records)} sleep records (before deduplication)")

    df = pd.DataFrame(records)

    if not df.empty:
        # Deduplicate - Eight Sleep creates duplicate records with different creation dates
        # Keep only unique (source, start_time, end_time, stage) combinations
        original_len = len(df)
        df = df.drop_duplicates(subset=["source", "start_time", "end_time", "stage"])
        print(f"After deduplication: {len(df)} records (removed {original_len - len(df)} duplicates)")

        # Parse timestamps
        df["start_time"] = pd.to_datetime(df["start_time"].str.replace(r" [-+]\d{4}$", "", regex=True))
        df["end_time"] = pd.to_datetime(df["end_time"].str.replace(r" [-+]\d{4}$", "", regex=True))
        df["duration_minutes"] = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60

        # Assign each record to a "sleep night" (date when you went to bed)
        # Records between 6pm-midnight: same day. Records midnight-6pm: previous day
        def get_sleep_night(ts):
            if ts.hour < 18:  # Before 6pm, count as previous night
                return (ts - timedelta(days=1)).date()
            return ts.date()

        df["sleep_night"] = df["start_time"].apply(get_sleep_night)

    return df


def aggregate_by_night(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sleep data by night and source."""

    # Group by sleep_night and source
    nightly = []

    for (night, source), group in df.groupby(["sleep_night", "source"]):
        # Total sleep time (excluding Awake and InBed)
        sleep_stages = ["AsleepCore", "AsleepREM", "AsleepDeep", "AsleepUnspecified"]
        total_sleep = group[group["stage"].isin(sleep_stages)]["duration_minutes"].sum()

        # Time in each stage
        core = group[group["stage"] == "AsleepCore"]["duration_minutes"].sum()
        rem = group[group["stage"] == "AsleepREM"]["duration_minutes"].sum()
        deep = group[group["stage"] == "AsleepDeep"]["duration_minutes"].sum()
        awake = group[group["stage"] == "Awake"]["duration_minutes"].sum()
        in_bed = group[group["stage"] == "InBed"]["duration_minutes"].sum()
        unspecified = group[group["stage"] == "AsleepUnspecified"]["duration_minutes"].sum()

        # Bed time and wake time
        bed_time = group["start_time"].min()
        wake_time = group["end_time"].max()

        nightly.append({
            "sleep_night": night,
            "source": source,
            "total_sleep_min": total_sleep,
            "core_min": core,
            "rem_min": rem,
            "deep_min": deep,
            "awake_min": awake,
            "in_bed_min": in_bed,
            "unspecified_min": unspecified,
            "bed_time": bed_time,
            "wake_time": wake_time,
            "time_in_bed_min": (wake_time - bed_time).total_seconds() / 60
        })

    return pd.DataFrame(nightly)


def add_fill_between_traces(fig, comparison_df, apple_col, eight_col, row, apple_color, eight_color, fill_opacity=0.3):
    """
    Add fill-between traces to show which source reports higher values.

    Apple Watch above Eight Sleep → Blue fill
    Eight Sleep above Apple Watch → Orange fill
    """
    x = comparison_df.index
    apple_vals = comparison_df[apple_col].values
    eight_vals = comparison_df[eight_col].values

    # Find segments where each source is higher
    # We'll iterate through and create filled regions for each continuous segment
    n = len(x)
    if n < 2:
        return

    i = 0
    while i < n:
        # Skip NaN values
        if pd.isna(apple_vals[i]) or pd.isna(eight_vals[i]):
            i += 1
            continue

        # Determine which source is higher at this point
        apple_higher = apple_vals[i] >= eight_vals[i]

        # Find the extent of this segment (same relationship)
        segment_start = i
        while i < n:
            if pd.isna(apple_vals[i]) or pd.isna(eight_vals[i]):
                break
            current_apple_higher = apple_vals[i] >= eight_vals[i]
            if current_apple_higher != apple_higher:
                break
            i += 1
        segment_end = i

        # Extract segment data
        seg_x = list(x[segment_start:segment_end])
        seg_apple = list(apple_vals[segment_start:segment_end])
        seg_eight = list(eight_vals[segment_start:segment_end])

        if len(seg_x) < 1:
            continue

        # For proper fill-between, we need to add the lower line first,
        # then the upper line with fill='tonexty'
        if apple_higher:
            # Apple is higher - fill with blue
            lower_vals = seg_eight
            upper_vals = seg_apple
            fill_color = f"rgba(0, 122, 255, {fill_opacity})"  # Apple blue
        else:
            # Eight Sleep is higher - fill with orange
            lower_vals = seg_apple
            upper_vals = seg_eight
            fill_color = f"rgba(255, 107, 53, {fill_opacity})"  # Eight Sleep orange

        # Add lower boundary (invisible line)
        fig.add_trace(go.Scatter(
            x=seg_x, y=lower_vals,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ), row=row, col=1)

        # Add upper boundary with fill to lower
        fig.add_trace(go.Scatter(
            x=seg_x, y=upper_vals,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor=fill_color,
            showlegend=False,
            hoverinfo='skip'
        ), row=row, col=1)


def create_comparison_visualization(nightly_df: pd.DataFrame, output_path: str):
    """Create visualization comparing Apple Watch vs Eight Sleep."""

    # Pivot to have both sources side by side
    apple = nightly_df[nightly_df["source"] == "Apple Watch"].set_index("sleep_night")
    eight = nightly_df[nightly_df["source"] == "Eight Sleep"].set_index("sleep_night")

    # Find overlapping nights
    common_nights = sorted(set(apple.index) & set(eight.index))
    print(f"\nNights with data from BOTH sources: {len(common_nights)}")

    if len(common_nights) == 0:
        print("No overlapping nights found!")
        return

    # Create comparison dataframe for overlapping nights
    comparison = pd.DataFrame(index=common_nights)
    comparison["apple_total_sleep"] = apple.loc[common_nights, "total_sleep_min"]
    comparison["eight_total_sleep"] = eight.loc[common_nights, "total_sleep_min"]
    comparison["apple_deep"] = apple.loc[common_nights, "deep_min"]
    comparison["eight_deep"] = eight.loc[common_nights, "deep_min"]
    comparison["apple_rem"] = apple.loc[common_nights, "rem_min"]
    comparison["eight_rem"] = eight.loc[common_nights, "rem_min"]
    comparison["apple_core"] = apple.loc[common_nights, "core_min"]
    comparison["eight_core"] = eight.loc[common_nights, "core_min"]
    comparison["apple_awake"] = apple.loc[common_nights, "awake_min"]
    comparison["eight_awake"] = eight.loc[common_nights, "awake_min"]

    # Convert index to datetime for plotting
    comparison.index = pd.to_datetime(comparison.index)
    comparison = comparison.sort_index()

    # Create figure with subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            "Total Sleep Duration (minutes)",
            "Deep Sleep (minutes)",
            "REM Sleep (minutes)",
            "Light/Core Sleep (minutes)"
        ),
        row_heights=[0.25, 0.25, 0.25, 0.25]
    )

    # Colors
    apple_color = "#007AFF"  # Apple blue
    eight_color = "#FF6B35"  # Eight Sleep orange

    # Add fill-between traces FIRST (so lines appear on top)
    # Row 1: Total Sleep fill
    add_fill_between_traces(fig, comparison, "apple_total_sleep", "eight_total_sleep",
                           row=1, apple_color=apple_color, eight_color=eight_color)
    # Row 2: Deep Sleep fill
    add_fill_between_traces(fig, comparison, "apple_deep", "eight_deep",
                           row=2, apple_color=apple_color, eight_color=eight_color)
    # Row 3: REM Sleep fill
    add_fill_between_traces(fig, comparison, "apple_rem", "eight_rem",
                           row=3, apple_color=apple_color, eight_color=eight_color)
    # Row 4: Core Sleep fill
    add_fill_between_traces(fig, comparison, "apple_core", "eight_core",
                           row=4, apple_color=apple_color, eight_color=eight_color)

    # Row 1: Total Sleep
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["apple_total_sleep"],
        mode="lines+markers", name="Apple Watch",
        line=dict(color=apple_color), marker=dict(size=4),
        legendgroup="apple"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["eight_total_sleep"],
        mode="lines+markers", name="Eight Sleep",
        line=dict(color=eight_color), marker=dict(size=4),
        legendgroup="eight"
    ), row=1, col=1)

    # Row 2: Deep Sleep
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["apple_deep"],
        mode="lines+markers", name="Apple Watch",
        line=dict(color=apple_color), marker=dict(size=4),
        showlegend=False, legendgroup="apple"
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["eight_deep"],
        mode="lines+markers", name="Eight Sleep",
        line=dict(color=eight_color), marker=dict(size=4),
        showlegend=False, legendgroup="eight"
    ), row=2, col=1)

    # Row 3: REM Sleep
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["apple_rem"],
        mode="lines+markers", name="Apple Watch",
        line=dict(color=apple_color), marker=dict(size=4),
        showlegend=False, legendgroup="apple"
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["eight_rem"],
        mode="lines+markers", name="Eight Sleep",
        line=dict(color=eight_color), marker=dict(size=4),
        showlegend=False, legendgroup="eight"
    ), row=3, col=1)

    # Row 4: Core/Light Sleep
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["apple_core"],
        mode="lines+markers", name="Apple Watch",
        line=dict(color=apple_color), marker=dict(size=4),
        showlegend=False, legendgroup="apple"
    ), row=4, col=1)
    fig.add_trace(go.Scatter(
        x=comparison.index, y=comparison["eight_core"],
        mode="lines+markers", name="Eight Sleep",
        line=dict(color=eight_color), marker=dict(size=4),
        showlegend=False, legendgroup="eight"
    ), row=4, col=1)

    # Layout
    fig.update_layout(
        title=dict(
            text="Sleep Data Comparison: Apple Watch vs Eight Sleep",
            x=0.5, xanchor="center", font=dict(size=20)
        ),
        height=1000,
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
        hovermode="x unified"
    )

    fig.update_xaxes(title_text="Date", row=4, col=1)

    # Save
    fig.write_html(output_path)
    print(f"\nVisualization saved to: {output_path}")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS (overlapping nights)")
    print("=" * 60)

    print(f"\nTotal Sleep Duration:")
    print(f"  Apple Watch - Mean: {comparison['apple_total_sleep'].mean():.1f} min, Std: {comparison['apple_total_sleep'].std():.1f}")
    print(f"  Eight Sleep - Mean: {comparison['eight_total_sleep'].mean():.1f} min, Std: {comparison['eight_total_sleep'].std():.1f}")
    diff = comparison["apple_total_sleep"] - comparison["eight_total_sleep"]
    print(f"  Mean difference (Apple - Eight): {diff.mean():+.1f} min")

    # Correlation
    corr = comparison["apple_total_sleep"].corr(comparison["eight_total_sleep"])
    print(f"  Correlation: {corr:.3f}")

    print(f"\nDeep Sleep:")
    print(f"  Apple Watch - Mean: {comparison['apple_deep'].mean():.1f} min")
    print(f"  Eight Sleep - Mean: {comparison['eight_deep'].mean():.1f} min")
    corr_deep = comparison["apple_deep"].corr(comparison["eight_deep"])
    print(f"  Correlation: {corr_deep:.3f}")

    print(f"\nREM Sleep:")
    print(f"  Apple Watch - Mean: {comparison['apple_rem'].mean():.1f} min")
    print(f"  Eight Sleep - Mean: {comparison['eight_rem'].mean():.1f} min")
    corr_rem = comparison["apple_rem"].corr(comparison["eight_rem"])
    print(f"  Correlation: {corr_rem:.3f}")

    print(f"\nCore/Light Sleep:")
    print(f"  Apple Watch - Mean: {comparison['apple_core'].mean():.1f} min")
    print(f"  Eight Sleep - Mean: {comparison['eight_core'].mean():.1f} min")
    corr_core = comparison["apple_core"].corr(comparison["eight_core"])
    print(f"  Correlation: {corr_core:.3f}")

    return comparison


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(script_dir, "apple_health_export", "export.xml")
    output_path = os.path.join(script_dir, "sleep_comparison.html")

    # Parse sleep data
    sleep_df = parse_sleep_data(xml_path)

    if sleep_df.empty:
        print("No sleep data found!")
        return

    # Filter to last 6 months
    cutoff = datetime(2025, 7, 16)
    sleep_df = sleep_df[sleep_df["start_time"] >= cutoff]
    print(f"\nFiltered to {len(sleep_df)} records from {cutoff.date()} onwards")

    # Show breakdown by source
    print("\nRecords by source:")
    print(sleep_df["source"].value_counts())

    print("\nStages by source:")
    print(sleep_df.groupby(["source", "stage"]).size().unstack(fill_value=0))

    # Aggregate by night
    nightly_df = aggregate_by_night(sleep_df)

    print(f"\nNightly records: {len(nightly_df)}")
    print(f"  Apple Watch nights: {len(nightly_df[nightly_df['source'] == 'Apple Watch'])}")
    print(f"  Eight Sleep nights: {len(nightly_df[nightly_df['source'] == 'Eight Sleep'])}")

    # Create comparison visualization
    comparison = create_comparison_visualization(nightly_df, output_path)

    # Export comparison data
    if comparison is not None:
        csv_path = os.path.join(script_dir, "sleep_comparison.csv")
        comparison.to_csv(csv_path)
        print(f"\nComparison data saved to: {csv_path}")

    # Open in browser
    import webbrowser
    print("\nOpening visualization in browser...")
    webbrowser.open(f"file://{output_path}")


if __name__ == "__main__":
    main()
