#!/usr/bin/env python3
"""
Analyze correlation between workouts and low heart rate events.
Question: Does working out during the day lead to more/fewer low HR events that night?
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from scipy import stats

# Load data
low_hr_df = pd.read_csv('low_hr_events.csv', parse_dates=['start_time', 'end_time'])
workout_df = pd.read_csv('workout_data.csv', parse_dates=['timestamp'])

# Filter to overlapping time period (July 16, 2025 onwards - when workout data starts)
cutoff = datetime(2025, 7, 16)
low_hr_df = low_hr_df[low_hr_df['start_time'] >= cutoff].copy()
workout_df = workout_df[workout_df['timestamp'] >= cutoff].copy()

print("=" * 60)
print("SAME-DAY EFFECT ANALYSIS")
print("Do workouts during the day lead to more/fewer low HR events that night?")
print("=" * 60)

print(f"\nData range: {cutoff.date()} to present")
print(f"Low HR events in range: {len(low_hr_df)}")
print(f"Workouts in range: {len(workout_df)}")

# Extract date from each dataset
low_hr_df['date'] = low_hr_df['start_time'].dt.date
workout_df['date'] = workout_df['timestamp'].dt.date

# For low HR events, we need to assign them to the "workout day"
# Events between midnight and ~8am should count as "night following previous day's workout"
# Events between ~8pm and midnight count as same day
def get_associated_workout_day(event_time):
    """
    Assign low HR event to the day whose workout might have caused it.
    - Events 12am-10am: associate with previous day (sleep after that day's workout)
    - Events 10am-midnight: associate with same day
    """
    hour = event_time.hour
    if hour < 10:  # Before 10am, count as previous night's sleep
        return (event_time - timedelta(days=1)).date()
    else:
        return event_time.date()

low_hr_df['workout_day'] = low_hr_df['start_time'].apply(get_associated_workout_day)

# Get all dates in our range
all_dates = pd.date_range(start=cutoff, end=datetime.now()).date
workout_dates = set(workout_df['date'].unique())

# Count low HR events per workout day
events_per_day = low_hr_df.groupby('workout_day').size().to_dict()

# Separate into workout days and non-workout days
workout_day_events = []
non_workout_day_events = []

for date in all_dates:
    event_count = events_per_day.get(date, 0)
    if date in workout_dates:
        workout_day_events.append(event_count)
    else:
        non_workout_day_events.append(event_count)

# Statistics
print("\n" + "-" * 60)
print("RESULTS: Low HR Events by Day Type")
print("-" * 60)

print(f"\n📊 WORKOUT DAYS ({len(workout_day_events)} days):")
print(f"   Total low HR events: {sum(workout_day_events)}")
print(f"   Mean events per night: {np.mean(workout_day_events):.2f}")
print(f"   Median: {np.median(workout_day_events):.1f}")
print(f"   Std dev: {np.std(workout_day_events):.2f}")
print(f"   Days with 0 events: {workout_day_events.count(0)} ({100*workout_day_events.count(0)/len(workout_day_events):.1f}%)")
print(f"   Days with 1+ events: {len([x for x in workout_day_events if x > 0])} ({100*len([x for x in workout_day_events if x > 0])/len(workout_day_events):.1f}%)")

print(f"\n📊 NON-WORKOUT DAYS ({len(non_workout_day_events)} days):")
print(f"   Total low HR events: {sum(non_workout_day_events)}")
print(f"   Mean events per night: {np.mean(non_workout_day_events):.2f}")
print(f"   Median: {np.median(non_workout_day_events):.1f}")
print(f"   Std dev: {np.std(non_workout_day_events):.2f}")
print(f"   Days with 0 events: {non_workout_day_events.count(0)} ({100*non_workout_day_events.count(0)/len(non_workout_day_events):.1f}%)")
print(f"   Days with 1+ events: {len([x for x in non_workout_day_events if x > 0])} ({100*len([x for x in non_workout_day_events if x > 0])/len(non_workout_day_events):.1f}%)")

# Statistical test (Mann-Whitney U test - doesn't assume normal distribution)
statistic, p_value = stats.mannwhitneyu(workout_day_events, non_workout_day_events, alternative='two-sided')

print("\n" + "-" * 60)
print("STATISTICAL SIGNIFICANCE")
print("-" * 60)
print(f"\nMann-Whitney U test (two-sided):")
print(f"   U statistic: {statistic:.1f}")
print(f"   p-value: {p_value:.4f}")

if p_value < 0.05:
    print(f"   ✓ Statistically significant difference (p < 0.05)")
else:
    print(f"   ✗ No statistically significant difference (p >= 0.05)")

# Effect size (rank-biserial correlation)
n1, n2 = len(workout_day_events), len(non_workout_day_events)
effect_size = 1 - (2 * statistic) / (n1 * n2)
print(f"\nEffect size (rank-biserial correlation): {effect_size:.3f}")
if abs(effect_size) < 0.1:
    print("   Interpretation: Negligible effect")
elif abs(effect_size) < 0.3:
    print("   Interpretation: Small effect")
elif abs(effect_size) < 0.5:
    print("   Interpretation: Medium effect")
else:
    print("   Interpretation: Large effect")

# Direction of effect
diff = np.mean(workout_day_events) - np.mean(non_workout_day_events)
print(f"\nDifference in means: {diff:+.2f} events per night")
if diff > 0:
    print("   → Workout days have MORE low HR events")
else:
    print("   → Workout days have FEWER low HR events")

# Breakdown by workout type
print("\n" + "-" * 60)
print("BREAKDOWN BY WORKOUT TYPE")
print("-" * 60)

workout_types = workout_df['workout_type'].unique()
for wtype in workout_types:
    type_dates = set(workout_df[workout_df['workout_type'] == wtype]['date'].unique())
    type_events = [events_per_day.get(d, 0) for d in type_dates]
    if type_events:
        print(f"\n{wtype}:")
        print(f"   Days: {len(type_events)}")
        print(f"   Mean events: {np.mean(type_events):.2f}")
        print(f"   Days with events: {len([x for x in type_events if x > 0])} ({100*len([x for x in type_events if x > 0])/len(type_events):.1f}%)")
