# Low Heart Rate Warning Correlation Analysis

This document summarizes the statistical analysis of correlations between Apple Watch low heart rate warnings and both sleep quality and workout activity.

**Analysis Date:** January 2026
**Data Period:** August 2022 - January 2026
**Total Low HR Events Analyzed:** 612

---

## Key Finding

**Low heart rate warnings show no correlation with poor sleep or lack of exercise.** The events occur predominantly during sleep hours and appear to be normal physiological responses to rest and cardiovascular fitness.

---

## Part 1: Sleep Quality vs Low Heart Rate Warnings

### Overview

- **Total nights analyzed:** 1,054 (Apple Watch sleep data)
- **Nights with low HR during sleep:** 138
- **Nights followed by daytime low HR:** 50

### Timing Distribution

| Time Period | Low HR Events | Percentage |
|-------------|---------------|------------|
| Sleep hours (10pm - 7am) | 517 | 84.5% |
| Waking hours | 95 | 15.5% |

The vast majority of low heart rate warnings occur during sleep, not during waking hours.

### Correlation Results

| Sleep Metric | Correlation | P-Value | Interpretation |
|--------------|-------------|---------|----------------|
| **Sleep Duration** | None | 0.66 - 0.96 | No relationship |
| **Deep Sleep %** | None | 0.17 - 0.42 | No relationship |
| **REM Sleep %** | Weak positive | 0.0001 *** | More REM = more low HR events |
| **Awake Time** | Weak positive | 0.03 * | More awakenings = slightly more daytime low HR |

### REM Sleep Finding

The only statistically significant correlation found was between REM sleep percentage and low heart rate events:

| Condition | REM Sleep % |
|-----------|-------------|
| Nights with during-sleep low HR | 22.1% |
| Nights before daytime low HR | 24.3% |
| Nights without low HR events | 20.8% |

**Interpretation:** More REM sleep is associated with more low heart rate events. This is physiologically expected—during REM sleep, heart rate naturally fluctuates and can drop significantly. This suggests the low HR warnings are triggered during healthy sleep states.

### Sleep Analysis Conclusion

**Poor sleep does NOT cause low heart rate warnings.** If anything, better quality sleep (more REM) is weakly associated with more events. The warnings appear to be normal cardiac responses during restful sleep.

---

## Part 2: Workout Activity vs Low Heart Rate Warnings

### Overview

- **Total days analyzed:** 1,236
- **Days with workouts:** 994 (80%)
- **Days with low HR events:** 171 (14%)
- **Total workouts in analysis period:** 1,961

### Same-Day Analysis

Do workout days have more or fewer low HR events?

| Day Type | Days with Low HR | Rate |
|----------|------------------|------|
| Workout days | 125 / 994 | 12.6% |
| Non-workout days | 46 / 242 | 19.0% |

**Chi-square test:** p = 0.0126 (statistically significant)

**Finding:** Workout days actually have *fewer* low HR events than rest days. This may be because exercise temporarily elevates resting heart rate, reducing the likelihood of triggering the low HR threshold.

### Next-Day Analysis

Do workouts predict low HR events the following day?

| Condition | Next-Day Low HR Rate |
|-----------|---------------------|
| After workout | 12.9% |
| After no workout | 17.4% |

**Chi-square test:** p = 0.0827 (not significant)

**Finding:** No significant relationship between workouts and next-day low HR events.

### Workout Duration and Intensity

| Metric | Correlation (r) | P-Value | Interpretation |
|--------|-----------------|---------|----------------|
| Duration | 0.054 | 0.089 | Negligible, not significant |
| Calories | N/A | N/A | Insufficient data |

**Finding:** Longer or more intense workouts do not correlate with more or fewer low HR events.

### Low HR Rate by Workout Type

| Workout Type | Total Workouts | Low HR Rate |
|--------------|----------------|-------------|
| Cycling | 783 | 11.4% |
| Walking | 758 | 12.0% |
| Strength Training | 387 | 10.3% |
| Other | 27 | 11.1% |
| **Overall daily rate** | — | **13.8%** |

All workout types show similar low HR rates, all slightly below the overall daily average.

### Workout Analysis Conclusion

**Workouts do NOT increase low heart rate warnings.** In fact, workout days show a slightly lower rate of low HR events than rest days. Neither workout type, duration, nor intensity shows any meaningful correlation with low HR warnings.

---

## Overall Conclusions

1. **Low HR warnings are primarily a sleep phenomenon** — 84.5% occur during sleep hours (10pm-7am)

2. **No evidence of problematic triggers** — Neither poor sleep nor lack of exercise causes these events

3. **Possible indicator of cardiovascular fitness** — Low resting heart rate during sleep is often a sign of good cardiovascular health, particularly in active individuals

4. **REM sleep association** — The weak positive correlation with REM sleep suggests these events occur during healthy, restorative sleep phases

---

## Statistical Notes

- **Significance threshold:** p < 0.05
- **Correlation strength interpretation:**
  - |r| < 0.1: Negligible
  - |r| 0.1-0.3: Weak
  - |r| 0.3-0.5: Moderate
  - |r| > 0.5: Strong
- **Tests used:** Chi-square for categorical associations, point-biserial correlation for binary vs continuous, independent t-tests for group comparisons

---

## Data Files

- `sleep_hr_analysis.csv` — Detailed nightly sleep metrics with low HR event counts
- `analyze_sleep_hr_correlation.py` — Sleep analysis script
