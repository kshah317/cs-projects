"""
estimates heart rate during the walk/run, using only age plus the workout's speed
and incline (no fitness test, no personal max heart rate measurement). this is a
rougher estimate than the calorie math in calories.py, since it has to guess at
things like your max heart rate and your fitness level instead of measuring them,
so treat it as a ballpark, not a real reading.

the chain of formulas, all standard and published, none invented here:

1. estimate max heart rate from age, using the tanaka formula (208 - 0.7 x age),
   a more modern replacement for the old "220 minus age" rule of thumb.

2. estimate vo2max (how much oxygen your body can use at full effort) from that
   max heart rate and an assumed resting heart rate, using the uth-sorensen-
   overgaard-pedersen non-exercise formula: vo2max = 15.3 x (hr max / hr rest).
   this lets us guess a fitness level without ever measuring one directly.

3. use acsm's well-established principle that percent heart-rate-reserve and
   percent vo2-reserve rise together at roughly the same rate, so the workout's
   oxygen cost (from calories.py) tells us what percent of heart rate reserve
   we're likely using, and from there, the estimated heart rate itself.
"""

from calories import ONE_MET_VO2_ML_PER_KG_PER_MIN, total_vo2_ml_per_kg_per_minute

# the tanaka formula for estimated max heart rate: 208 minus 0.7 times age. this
# is a more accurate modern replacement for the classic (and less accurate)
# "220 minus age" rule of thumb
TANAKA_MAX_HEART_RATE_INTERCEPT = 208
TANAKA_MAX_HEART_RATE_AGE_COEFFICIENT = 0.7

# since we only have age (not a measured resting heart rate), we assume a
# typical adult resting heart rate of 70 beats per minute
ASSUMED_RESTING_HEART_RATE_BPM = 70

# the constant in the uth-sorensen-overgaard-pedersen formula that estimates
# vo2max from the ratio of max heart rate to resting heart rate, without
# needing an actual exercise fitness test
UTH_NON_EXERCISE_VO2MAX_CONSTANT = 15.3


def estimated_max_heart_rate_bpm(age_years):
    """estimates max heart rate from age alone, using the tanaka formula"""
    return TANAKA_MAX_HEART_RATE_INTERCEPT - (TANAKA_MAX_HEART_RATE_AGE_COEFFICIENT * age_years)


def estimated_vo2_max_ml_per_kg_per_minute(age_years, resting_heart_rate_bpm=ASSUMED_RESTING_HEART_RATE_BPM):
    """
    estimates vo2max (peak oxygen use, in ml per kg of body weight per minute)
    from the ratio of estimated max heart rate to resting heart rate, using the
    uth non-exercise formula. this stands in for an actual fitness test, which
    this simulator has no way to run
    """
    max_heart_rate = estimated_max_heart_rate_bpm(age_years)
    return UTH_NON_EXERCISE_VO2MAX_CONSTANT * (max_heart_rate / resting_heart_rate_bpm)


def estimated_heart_rate_bpm(age_years, speed_mph, incline_percent):
    """
    estimates heart rate during the workout by figuring out what percent of vo2
    reserve the workout demands, then assuming percent heart-rate-reserve rises
    at roughly the same rate (acsm's %hrr ~= %vo2r principle), and converting
    that percentage back into an actual beats-per-minute number
    """
    max_heart_rate = estimated_max_heart_rate_bpm(age_years)
    resting_heart_rate = ASSUMED_RESTING_HEART_RATE_BPM
    vo2_max = estimated_vo2_max_ml_per_kg_per_minute(age_years, resting_heart_rate)

    # vo2 reserve is the gap between max effort and resting effort, in vo2 terms
    vo2_reserve = vo2_max - ONE_MET_VO2_ML_PER_KG_PER_MIN
    workout_vo2 = total_vo2_ml_per_kg_per_minute(speed_mph, incline_percent)
    percent_vo2_reserve = (workout_vo2 - ONE_MET_VO2_ML_PER_KG_PER_MIN) / vo2_reserve

    # clamp to [0, 1]: a very fast/steep workout could otherwise imply demanding
    # more oxygen than our estimated vo2max allows, which isn't physically
    # meaningful, so we treat anything above 100% effort as simply "max effort"
    percent_vo2_reserve = max(0.0, min(1.0, percent_vo2_reserve))

    # acsm's %hrr ~= %vo2r principle: apply that same percentage to heart rate
    # reserve (the gap between resting and max heart rate) instead
    heart_rate_reserve = max_heart_rate - resting_heart_rate
    return resting_heart_rate + (percent_vo2_reserve * heart_rate_reserve)
