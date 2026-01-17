# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Apple Health data visualization project that parses Apple Health export XML files and creates interactive Plotly visualizations for heart rate and workout data.

## Commands

```bash
# Run main visualization (parses XML, generates HTML, opens in browser)
python visualize_heart_rate.py

# Export workout data to CSV only
python export_workouts.py
```

## Dependencies

- pandas
- plotly

## Data Flow

1. Apple Health export (`apple_health_export/export.xml`) is parsed using memory-efficient `iterparse`
2. Heart rate data filtered by source name (default: "Jerome")
3. Workout data collected from all sources (Apple Watch, Strava, Strong)
4. Data filtered to last 6 months (cutoff: July 16, 2025)
5. Interactive HTML visualization generated with two stacked charts

## Architecture

**visualize_heart_rate.py** - Main entry point
- `parse_heart_rate_data()` - Extracts HKQuantityTypeIdentifierHeartRate records
- `parse_workout_data()` - Imported from export_workouts.py
- `create_visualization()` - Builds Plotly subplots (heart rate scatter + workout bars)
- Outputs: `heart_rate_visualization.html`, `heart_rate_data.csv`

**export_workouts.py** - Workout parsing module
- `parse_workout_data()` - Extracts Workout elements from XML
- `clean_workout_type()` - Converts HKWorkoutActivityType to readable names
- Outputs: `workout_data.csv`

## Key Implementation Details

- Bar charts with datetime x-axes require explicit `width` parameter (in milliseconds) or bars render invisibly
- Workout outliers (>500 min) are filtered to prevent y-axis scale issues
- Workout colors: Cycling=blue, Walking=green, Strength Training=orange, Running=purple
- Timeline markers (like doctor appointments) use `add_vline()` + `add_annotation()`
