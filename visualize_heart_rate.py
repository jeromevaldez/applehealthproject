#!/usr/bin/env python3
"""
Heart Rate Data Visualization

Visualizes Apple Watch heart rate data from Apple Health export,
highlighting sub-40 bpm readings as larger red markers.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import webbrowser
import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import workout parsing functions
from export_workouts import parse_workout_data, clean_workout_type
from visualize_low_hr_events import parse_low_hr_events
from compare_sleep_sources import parse_sleep_data, aggregate_by_night, add_fill_between_traces


def parse_heart_rate_data(xml_path: str, source_filter: str = "Jerome") -> pd.DataFrame:
    """
    Parse heart rate records from Apple Health export XML.

    Args:
        xml_path: Path to export.xml file
        source_filter: Filter for sourceName (partial match)

    Returns:
        DataFrame with timestamp and heart_rate columns
    """
    print(f"Parsing XML file: {xml_path}")

    records = []

    # Use iterparse for memory-efficient parsing of large XML
    context = ET.iterparse(xml_path, events=("end",))

    for event, elem in context:
        if elem.tag == "Record" and elem.get("type") == "HKQuantityTypeIdentifierHeartRate":
            source_name = elem.get("sourceName", "")

            if source_filter in source_name:
                start_date = elem.get("startDate")
                value = elem.get("value")

                if start_date and value:
                    records.append({
                        "timestamp": start_date,
                        "heart_rate": float(value)
                    })

        # Clear element to save memory
        elem.clear()

    print(f"Found {len(records)} heart rate records (filtered by '{source_filter}')")

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
    Export heart rate data to CSV for dashboard use.

    Args:
        df: DataFrame with timestamp and heart_rate columns
        output_path: Path to save CSV file
    """
    # Create export DataFrame with is_low flag
    export_df = df.copy()
    export_df["is_low"] = export_df["heart_rate"] < 40

    # Format timestamp as ISO format (without timezone)
    export_df["timestamp"] = export_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Save to CSV
    export_df.to_csv(output_path, index=False)
    print(f"CSV exported to: {output_path}")
    print(f"  Total records: {len(export_df)}")
    print(f"  Low HR records (is_low=True): {export_df['is_low'].sum()}")


def create_visualization(hr_df: pd.DataFrame, low_hr_events_df: pd.DataFrame, workout_df: pd.DataFrame,
                         sleep_comparison_df: pd.DataFrame, output_path: str) -> None:
    """
    Create interactive Plotly visualization with heart rate, low HR events, workouts, and sleep charts.

    Args:
        hr_df: DataFrame with timestamp and heart_rate columns
        low_hr_events_df: DataFrame with low heart rate events (start_time, end_time, duration_minutes)
        workout_df: DataFrame with workout data (timestamp, duration_minutes, workout_type, source)
        sleep_comparison_df: DataFrame with sleep comparison data (Apple Watch vs Eight Sleep)
        output_path: Path to save HTML file
    """
    # Split heart rate data into normal and low
    normal_hr = hr_df[hr_df["heart_rate"] >= 40]
    low_hr = hr_df[hr_df["heart_rate"] < 40]

    print(f"Normal HR readings (≥40 bpm): {len(normal_hr)}")
    print(f"Low HR readings (<40 bpm): {len(low_hr)}")
    print(f"Low HR events (10+ min): {len(low_hr_events_df)}")
    print(f"Workout records: {len(workout_df)}")

    # Color scheme for workout types
    workout_colors = {
        "Cycling": "#1f77b4",  # Blue
        "Walking": "#2ca02c",  # Green
        "Traditional Strength Training": "#ff7f0e",  # Orange
        "Running": "#9467bd",  # Purple
    }
    default_color = "#7f7f7f"  # Gray for other types

    # Create subplots: 7 rows, shared x-axis
    fig = make_subplots(
        rows=7, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            "Heart Rate - Sub-40 bpm readings highlighted in red",
            "Low Heart Rate Events - HR below 40 bpm for 10+ minutes",
            "Workouts - Duration by Type",
            "Total Sleep Duration (Apple Watch vs Eight Sleep)",
            "Deep Sleep (Apple Watch vs Eight Sleep)",
            "REM Sleep (Apple Watch vs Eight Sleep)",
            "Light/Core Sleep (Apple Watch vs Eight Sleep)"
        ),
        row_heights=[0.20, 0.10, 0.14, 0.14, 0.14, 0.14, 0.14]
    )

    # --- Row 1: Heart Rate Chart ---
    # Normal heart rate readings - small blue markers
    fig.add_trace(go.Scatter(
        x=normal_hr["timestamp"],
        y=normal_hr["heart_rate"],
        mode="markers",
        name="Normal HR (≥40 bpm)",
        marker=dict(
            size=4,
            color="steelblue",
            opacity=0.5
        ),
        hovertemplate="<b>%{x}</b><br>Heart Rate: %{y:.0f} bpm<extra></extra>",
        legendgroup="heart_rate"
    ), row=1, col=1)

    # Low heart rate readings - larger red markers
    fig.add_trace(go.Scatter(
        x=low_hr["timestamp"],
        y=low_hr["heart_rate"],
        mode="markers",
        name="Low HR (<40 bpm)",
        marker=dict(
            size=10,
            color="red",
            symbol="circle",
            line=dict(width=1, color="darkred")
        ),
        hovertemplate="<b>%{x}</b><br>Heart Rate: %{y:.0f} bpm ⚠️<extra></extra>",
        legendgroup="heart_rate"
    ), row=1, col=1)

    # Reference line at 40 bpm
    fig.add_hline(
        y=40,
        line_dash="dash",
        line_color="red",
        opacity=0.7,
        annotation_text="40 bpm threshold",
        annotation_position="bottom right",
        row=1, col=1
    )

    # Doctor's appointment marker - November 13th, 2025
    fig.add_vline(
        x=datetime(2025, 11, 13),
        line_dash="dash",
        line_color="green",
        opacity=0.8,
        row=1, col=1
    )
    fig.add_annotation(
        x=datetime(2025, 11, 13),
        y=1.0,
        yref="y domain",
        text="Doctor's Appt",
        showarrow=False,
        font=dict(size=11, color="green"),
        bgcolor="rgba(255,255,255,0.8)",
        row=1, col=1
    )

    # --- Row 2: Low Heart Rate Events Chart ---
    if not low_hr_events_df.empty:
        # Extract hour of day for y-axis positioning
        events_df = low_hr_events_df.copy()
        events_df["hour_of_day"] = events_df["start_time"].dt.hour + events_df["start_time"].dt.minute / 60

        # Create hover text
        event_hover_text = [
            f"<b>{row['start_time'].strftime('%Y-%m-%d')}</b><br>"
            f"Start: {row['start_time'].strftime('%H:%M:%S')}<br>"
            f"End: {row['end_time'].strftime('%H:%M:%S')}<br>"
            f"Duration: {row['duration_minutes']:.1f} minutes"
            for _, row in events_df.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=events_df["start_time"],
            y=events_df["hour_of_day"],
            mode="markers",
            name="Low HR Event (10+ min)",
            marker=dict(
                size=8,
                color="darkred",
                symbol="diamond",
                line=dict(width=1, color="red")
            ),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=event_hover_text,
            legendgroup="low_hr_events"
        ), row=2, col=1)

        # Doctor's appointment marker on low HR events chart too
        fig.add_vline(
            x=datetime(2025, 11, 13),
            line_dash="dash",
            line_color="green",
            opacity=0.8,
            row=2, col=1
        )

    # --- Row 3: Workout Bar Chart ---
    # Filter out outliers (workouts > 500 minutes are likely bad data)
    workout_filtered = workout_df[workout_df["duration_minutes"] < 500].copy()
    print(f"Workout records after filtering outliers: {len(workout_filtered)}")

    # Group workouts by type for color-coded bars
    workout_types = workout_filtered["workout_type"].unique()

    # Bar width in milliseconds (1 day = 86400000 ms)
    bar_width_ms = 86400000

    for workout_type in workout_types:
        type_df = workout_filtered[workout_filtered["workout_type"] == workout_type]
        color = workout_colors.get(workout_type, default_color)

        # Create hover text with date, duration, type, and source
        hover_text = [
            f"<b>{row['timestamp'].strftime('%Y-%m-%d %H:%M')}</b><br>"
            f"Duration: {row['duration_minutes']:.1f} min<br>"
            f"Type: {row['workout_type']}<br>"
            f"Source: {row['source']}"
            for _, row in type_df.iterrows()
        ]

        fig.add_trace(go.Bar(
            x=type_df["timestamp"],
            y=type_df["duration_minutes"],
            name=workout_type,
            marker_color=color,
            width=bar_width_ms,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
            legendgroup="workouts"
        ), row=3, col=1)

    # --- Rows 4-7: Sleep Charts ---
    # Colors for sleep sources
    apple_sleep_color = "#007AFF"  # Apple blue
    eight_sleep_color = "#FF6B35"  # Eight Sleep orange

    if sleep_comparison_df is not None and not sleep_comparison_df.empty:
        # Sleep chart configurations: (row, apple_col, eight_col, y_label)
        sleep_charts = [
            (4, "apple_total_sleep", "eight_total_sleep", "Total Sleep (min)"),
            (5, "apple_deep", "eight_deep", "Deep Sleep (min)"),
            (6, "apple_rem", "eight_rem", "REM Sleep (min)"),
            (7, "apple_core", "eight_core", "Core Sleep (min)"),
        ]

        for row, apple_col, eight_col, y_label in sleep_charts:
            # Add fill-between traces first (so lines appear on top)
            add_fill_between_traces(fig, sleep_comparison_df, apple_col, eight_col,
                                   row=row, apple_color=apple_sleep_color, eight_color=eight_sleep_color)

            # Add Apple Watch line
            show_legend = (row == 4)  # Only show legend on first sleep chart
            fig.add_trace(go.Scatter(
                x=sleep_comparison_df.index, y=sleep_comparison_df[apple_col],
                mode="lines+markers", name="Apple Watch (Sleep)",
                line=dict(color=apple_sleep_color), marker=dict(size=4),
                showlegend=show_legend, legendgroup="apple_sleep"
            ), row=row, col=1)

            # Add Eight Sleep line
            fig.add_trace(go.Scatter(
                x=sleep_comparison_df.index, y=sleep_comparison_df[eight_col],
                mode="lines+markers", name="Eight Sleep",
                line=dict(color=eight_sleep_color), marker=dict(size=4),
                showlegend=show_legend, legendgroup="eight_sleep"
            ), row=row, col=1)

            # Update y-axis label
            fig.update_yaxes(title_text=y_label, row=row, col=1)

    # Layout
    fig.update_layout(
        title=dict(
            text="Apple Health Data - Last 6 Months",
            x=0.5,
            xanchor="center",
            font=dict(size=20)
        ),
        hovermode="closest",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        template="plotly_white",
        height=1800,
        barmode="group"
    )

    # Update axes
    fig.update_yaxes(title_text="Heart Rate (bpm)", row=1, col=1)
    # Low HR events y-axis shows time of day
    fig.update_yaxes(
        title_text="Time of Day",
        tickmode="array",
        tickvals=[0, 4, 8, 12, 16, 20, 24],
        ticktext=["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM", "12 AM"],
        range=[0, 24],
        row=2, col=1
    )
    # Cap workout y-axis at 300 minutes (5 hours) to handle outliers
    fig.update_yaxes(title_text="Duration (minutes)", range=[0, 300], row=3, col=1)
    fig.update_xaxes(title_text="Date", row=7, col=1)

    # Add range slider only on bottom chart for navigation
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=14, label="2w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(step="all", label="All")
            ])
        ),
        row=7, col=1
    )

    # Calculate date range for JavaScript
    # Find the max date across all data for dynamic range calculation
    max_date = hr_df["timestamp"].max()
    max_date_str = max_date.strftime("%Y-%m-%d")

    # Custom CSS for mobile-friendly filter buttons
    custom_css = """
    <style>
        .filter-container {
            display: flex;
            justify-content: center;
            gap: 12px;
            padding: 16px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            position: sticky;
            top: 0;
            z-index: 1000;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            border: 2px solid #007AFF;
            background: white;
            color: #007AFF;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 100px;
            min-height: 48px;
            touch-action: manipulation;
        }
        .filter-btn:hover {
            background: #007AFF;
            color: white;
        }
        .filter-btn.active {
            background: #007AFF;
            color: white;
        }
        /* Mobile styles */
        @media (max-width: 600px) {
            .filter-container {
                padding: 12px 16px;
                gap: 8px;
            }
            .filter-btn {
                flex: 1;
                min-width: 90px;
                padding: 14px 16px;
                font-size: 15px;
            }
        }
    </style>
    """

    # Custom HTML for filter buttons
    filter_html = """
    <div class="filter-container">
        <button class="filter-btn" data-range="1" onclick="setDateRange(1)">1 Month</button>
        <button class="filter-btn" data-range="3" onclick="setDateRange(3)">3 Months</button>
        <button class="filter-btn active" data-range="6" onclick="setDateRange(6)">All</button>
    </div>
    """

    # Custom JavaScript for date filtering
    custom_js = f"""
    <script>
        const maxDate = new Date('{max_date_str}');

        function setDateRange(months) {{
            // Update active button state
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            document.querySelector(`[data-range="${{months}}"]`).classList.add('active');

            // Calculate start date
            const startDate = new Date(maxDate);
            startDate.setMonth(startDate.getMonth() - months);

            // Get the Plotly graph div
            const graphDiv = document.querySelector('.plotly-graph-div');
            if (!graphDiv) return;

            // Update x-axis range for all subplots
            const update = {{
                'xaxis.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis2.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis3.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis4.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis5.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis6.range': [startDate.toISOString(), maxDate.toISOString()],
                'xaxis7.range': [startDate.toISOString(), maxDate.toISOString()],
            }};

            Plotly.relayout(graphDiv, update);
        }}
    </script>
    """

    # Generate HTML string
    html_content = fig.to_html(include_plotlyjs=True, full_html=True)

    # Inject custom CSS into <head>
    html_content = html_content.replace('</head>', custom_css + '</head>')

    # Inject filter buttons after <body>
    html_content = html_content.replace('<body>', '<body>' + filter_html)

    # Inject JavaScript before </body>
    html_content = html_content.replace('</body>', custom_js + '</body>')

    # Write modified HTML to file
    with open(output_path, 'w') as f:
        f.write(html_content)

    print(f"\nVisualization saved to: {output_path}")


def main():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(script_dir, "apple_health_export", "export.xml")
    html_output_path = os.path.join(script_dir, "heart_rate_visualization.html")
    csv_output_path = os.path.join(script_dir, "heart_rate_data.csv")

    # Parse heart rate data
    hr_df = parse_heart_rate_data(xml_path)

    if hr_df.empty:
        print("No heart rate data found!")
        return

    # Filter heart rate to last 6 months
    hr_df = filter_last_six_months(hr_df)

    if hr_df.empty:
        print("No heart rate data in the specified date range!")
        return

    # Parse workout data
    workout_df = parse_workout_data(xml_path)

    if workout_df.empty:
        print("No workout data found!")
        workout_df = pd.DataFrame(columns=["timestamp", "duration_minutes", "workout_type", "source"])
    else:
        # Filter workouts to last 6 months using the same cutoff
        cutoff_date = datetime(2025, 7, 16)
        workout_df = workout_df[workout_df["timestamp"] >= cutoff_date].copy()
        print(f"Filtered to {len(workout_df)} workout records from {cutoff_date.date()} onwards")

    # Parse low heart rate events
    low_hr_events_df = parse_low_hr_events(xml_path)

    if low_hr_events_df.empty:
        print("No low heart rate events found!")
        low_hr_events_df = pd.DataFrame(columns=["start_time", "end_time", "duration_minutes", "source"])
    else:
        # Filter to last 6 months using the same cutoff
        cutoff_date = datetime(2025, 7, 16)
        low_hr_events_df = low_hr_events_df[low_hr_events_df["start_time"] >= cutoff_date].copy()
        print(f"Filtered to {len(low_hr_events_df)} low HR events from {cutoff_date.date()} onwards")

    # Parse sleep data for Apple Watch vs Eight Sleep comparison
    sleep_comparison_df = None
    sleep_df = parse_sleep_data(xml_path)

    if not sleep_df.empty:
        # Filter to last 6 months
        cutoff_date = datetime(2025, 7, 16)
        sleep_df = sleep_df[sleep_df["start_time"] >= cutoff_date]
        print(f"Filtered to {len(sleep_df)} sleep records from {cutoff_date.date()} onwards")

        # Aggregate by night
        nightly_df = aggregate_by_night(sleep_df)

        # Create comparison dataframe for overlapping nights
        apple = nightly_df[nightly_df["source"] == "Apple Watch"].set_index("sleep_night")
        eight = nightly_df[nightly_df["source"] == "Eight Sleep"].set_index("sleep_night")
        common_nights = sorted(set(apple.index) & set(eight.index))
        print(f"Sleep: {len(common_nights)} nights with data from both Apple Watch and Eight Sleep")

        if common_nights:
            sleep_comparison_df = pd.DataFrame(index=common_nights)
            sleep_comparison_df["apple_total_sleep"] = apple.loc[common_nights, "total_sleep_min"]
            sleep_comparison_df["eight_total_sleep"] = eight.loc[common_nights, "total_sleep_min"]
            sleep_comparison_df["apple_deep"] = apple.loc[common_nights, "deep_min"]
            sleep_comparison_df["eight_deep"] = eight.loc[common_nights, "deep_min"]
            sleep_comparison_df["apple_rem"] = apple.loc[common_nights, "rem_min"]
            sleep_comparison_df["eight_rem"] = eight.loc[common_nights, "rem_min"]
            sleep_comparison_df["apple_core"] = apple.loc[common_nights, "core_min"]
            sleep_comparison_df["eight_core"] = eight.loc[common_nights, "core_min"]
            sleep_comparison_df.index = pd.to_datetime(sleep_comparison_df.index)
            sleep_comparison_df = sleep_comparison_df.sort_index()
    else:
        print("No sleep data found!")

    # Export heart rate to CSV for dashboard use
    export_to_csv(hr_df, csv_output_path)

    # Create visualization with all datasets
    create_visualization(hr_df, low_hr_events_df, workout_df, sleep_comparison_df, html_output_path)

    # Open in browser
    print("Opening in browser...")
    webbrowser.open(f"file://{html_output_path}")


if __name__ == "__main__":
    main()
