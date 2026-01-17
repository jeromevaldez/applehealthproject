#!/usr/bin/env python3
"""
Analyze correlation between sleep quality and low heart rate warnings.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
from scipy import stats

def parse_low_hr_events(xml_path):
    """Parse low heart rate events from Apple Health export."""
    events = []

    for event, elem in ET.iterparse(xml_path, events=['end']):
        if elem.tag == 'Record' and elem.get('type') == 'HKCategoryTypeIdentifierLowHeartRateEvent':
            start_date = datetime.strptime(elem.get('startDate')[:19], '%Y-%m-%d %H:%M:%S')
            events.append({
                'start_date': start_date,
                'date': start_date.date()
            })
        elem.clear()

    return pd.DataFrame(events)

def parse_sleep_data(xml_path):
    """Parse sleep analysis data from Apple Health export."""
    records = []

    for event, elem in ET.iterparse(xml_path, events=['end']):
        if elem.tag == 'Record' and elem.get('type') == 'HKCategoryTypeIdentifierSleepAnalysis':
            start_str = elem.get('startDate')[:19]
            end_str = elem.get('endDate')[:19]

            start_date = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')

            duration_min = (end_date - start_date).total_seconds() / 60

            value = elem.get('value', '')
            sleep_type = value.replace('HKCategoryValueSleepAnalysis', '')

            records.append({
                'start_date': start_date,
                'end_date': end_date,
                'duration_min': duration_min,
                'sleep_type': sleep_type,
                'night_of': (start_date - timedelta(hours=12)).date()
            })
        elem.clear()

    return pd.DataFrame(records)

def calculate_nightly_sleep_metrics(sleep_df):
    """Calculate sleep quality metrics for each night."""
    metrics = []

    for night, group in sleep_df.groupby('night_of'):
        total_in_bed = group[group['sleep_type'] == 'InBed']['duration_min'].sum()
        total_asleep = group[group['sleep_type'].isin(['AsleepCore', 'AsleepREM', 'AsleepDeep', 'AsleepUnspecified'])]['duration_min'].sum()
        deep_sleep = group[group['sleep_type'] == 'AsleepDeep']['duration_min'].sum()
        rem_sleep = group[group['sleep_type'] == 'AsleepREM']['duration_min'].sum()
        core_sleep = group[group['sleep_type'] == 'AsleepCore']['duration_min'].sum()
        awake_time = group[group['sleep_type'] == 'Awake']['duration_min'].sum()

        num_awakenings = len(group[group['sleep_type'] == 'Awake'])

        if total_in_bed > 0:
            sleep_efficiency = (total_asleep / total_in_bed) * 100
        else:
            sleep_efficiency = 0

        if total_asleep > 0:
            deep_pct = (deep_sleep / total_asleep) * 100
            rem_pct = (rem_sleep / total_asleep) * 100
        else:
            deep_pct = 0
            rem_pct = 0

        metrics.append({
            'night_of': night,
            'total_sleep_min': total_asleep,
            'total_in_bed_min': total_in_bed,
            'deep_sleep_min': deep_sleep,
            'rem_sleep_min': rem_sleep,
            'core_sleep_min': core_sleep,
            'awake_time_min': awake_time,
            'sleep_efficiency': sleep_efficiency,
            'deep_pct': deep_pct,
            'rem_pct': rem_pct,
            'num_awakenings': num_awakenings
        })

    return pd.DataFrame(metrics)

def analyze_correlations(sleep_metrics, low_hr_events):
    """Analyze correlations between sleep quality and low HR events."""

    # Count low HR events per day
    low_hr_counts = low_hr_events.groupby('date').size().reset_index(name='low_hr_count')
    low_hr_counts['date'] = pd.to_datetime(low_hr_counts['date'])

    # Prepare sleep metrics
    sleep_metrics['night_of'] = pd.to_datetime(sleep_metrics['night_of'])

    # Match low HR events to the PRECEDING night's sleep
    # (If you get a low HR warning during the day, it might relate to last night's sleep)
    # OR the same night (if the warning happens during sleep)

    # Create a binary: did the following day have low HR events?
    sleep_metrics['next_day'] = sleep_metrics['night_of'] + timedelta(days=1)

    merged = sleep_metrics.merge(
        low_hr_counts,
        left_on='next_day',
        right_on='date',
        how='left'
    )
    merged['low_hr_count'] = merged['low_hr_count'].fillna(0)
    merged['had_low_hr'] = (merged['low_hr_count'] > 0).astype(int)

    # Also check same night (for warnings during sleep)
    same_night_merge = sleep_metrics.merge(
        low_hr_counts,
        left_on='night_of',
        right_on='date',
        how='left'
    )
    same_night_merge['low_hr_count_same'] = same_night_merge['low_hr_count'].fillna(0)

    merged['low_hr_same_night'] = same_night_merge['low_hr_count_same'].values
    merged['had_low_hr_either'] = ((merged['low_hr_count'] > 0) | (merged['low_hr_same_night'] > 0)).astype(int)

    return merged

def calculate_correlation_stats(merged_df):
    """Calculate and print correlation statistics."""

    # Filter to nights with valid sleep data
    valid = merged_df[merged_df['total_sleep_min'] > 60].copy()  # At least 1 hour of sleep

    print("=" * 60)
    print("SLEEP QUALITY vs LOW HEART RATE CORRELATION ANALYSIS")
    print("=" * 60)

    print(f"\nTotal nights analyzed: {len(valid)}")
    print(f"Nights followed by low HR events: {valid['had_low_hr'].sum()}")
    print(f"Nights with low HR during sleep: {(valid['low_hr_same_night'] > 0).sum()}")
    print(f"Nights with low HR (either): {valid['had_low_hr_either'].sum()}")

    sleep_vars = [
        ('total_sleep_min', 'Total Sleep Duration'),
        ('deep_sleep_min', 'Deep Sleep Duration'),
        ('rem_sleep_min', 'REM Sleep Duration'),
        ('sleep_efficiency', 'Sleep Efficiency %'),
        ('deep_pct', 'Deep Sleep %'),
        ('rem_pct', 'REM Sleep %'),
        ('num_awakenings', 'Number of Awakenings'),
        ('awake_time_min', 'Awake Time')
    ]

    print("\n" + "-" * 60)
    print("CORRELATIONS: Sleep Metrics vs Low HR (Next Day)")
    print("-" * 60)

    results = []

    for var, label in sleep_vars:
        # Point-biserial correlation (binary vs continuous)
        corr, p_value = stats.pointbiserialr(valid['had_low_hr'], valid[var])

        # Interpretation
        if abs(corr) < 0.1:
            strength = "Negligible"
        elif abs(corr) < 0.3:
            strength = "Weak"
        elif abs(corr) < 0.5:
            strength = "Moderate"
        elif abs(corr) < 0.7:
            strength = "Strong"
        else:
            strength = "Very Strong"

        direction = "positive" if corr > 0 else "negative"
        sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else ""

        results.append({
            'metric': label,
            'correlation': corr,
            'p_value': p_value,
            'strength': strength,
            'direction': direction,
            'significant': p_value < 0.05
        })

        print(f"\n{label}:")
        print(f"  Correlation: {corr:.4f} ({strength} {direction})")
        print(f"  P-value: {p_value:.4f} {sig}")

    # Compare means between groups
    print("\n" + "-" * 60)
    print("MEAN COMPARISON: Nights WITH vs WITHOUT Low HR Events")
    print("-" * 60)

    with_low_hr = valid[valid['had_low_hr'] == 1]
    without_low_hr = valid[valid['had_low_hr'] == 0]

    for var, label in sleep_vars:
        mean_with = with_low_hr[var].mean()
        mean_without = without_low_hr[var].mean()
        diff_pct = ((mean_with - mean_without) / mean_without * 100) if mean_without != 0 else 0

        print(f"\n{label}:")
        print(f"  With Low HR:    {mean_with:.1f}")
        print(f"  Without Low HR: {mean_without:.1f}")
        print(f"  Difference:     {diff_pct:+.1f}%")

    return pd.DataFrame(results)

def main():
    xml_path = '/Users/jeromevaldez/projects/applehealthproject/apple_health_export/export.xml'

    print("Parsing low heart rate events...")
    low_hr_df = parse_low_hr_events(xml_path)
    print(f"Found {len(low_hr_df)} low HR events")

    print("\nParsing sleep data...")
    sleep_df = parse_sleep_data(xml_path)
    print(f"Found {len(sleep_df)} sleep records")

    print("\nCalculating nightly sleep metrics...")
    sleep_metrics = calculate_nightly_sleep_metrics(sleep_df)
    print(f"Calculated metrics for {len(sleep_metrics)} nights")

    print("\nAnalyzing correlations...")
    merged = analyze_correlations(sleep_metrics, low_hr_df)

    results = calculate_correlation_stats(merged)

    # Save detailed data for further analysis
    merged.to_csv('/Users/jeromevaldez/projects/applehealthproject/sleep_hr_analysis.csv', index=False)
    print(f"\nDetailed data saved to sleep_hr_analysis.csv")

    # Print date range
    print(f"\n" + "-" * 60)
    print("DATA RANGE")
    print("-" * 60)
    print(f"Low HR events: {low_hr_df['date'].min()} to {low_hr_df['date'].max()}")
    print(f"Sleep data: {sleep_metrics['night_of'].min()} to {sleep_metrics['night_of'].max()}")

if __name__ == '__main__':
    main()
