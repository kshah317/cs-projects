"""
takes a single walk/run session (speed, incline, how long) plus the person's own
stats, and turns it into the three outputs the program reports: an estimated
calorie range, an estimated heart rate range, and an exact elevation gain. this
file just does the math and packages up the result, it never talks to the
terminal or asks the user anything.
"""

from dataclasses import dataclass

from calories import total_kcal_per_minute
from heart_rate import estimated_heart_rate_bpm

# how many feet are in one mile, used to turn incline percent and distance into
# an actual elevation gain in feet
FEET_PER_MILE = 5280

# the calorie estimate is reported as a plus-or-minus band around the point
# estimate, rather than a single exact number, since real calorie burn depends
# on things (exact stride, fitness level) this model can't know
CALORIE_RANGE_KCAL = 20

# same idea for heart rate, but wider relative to the number itself, since heart
# rate here is estimated from age and workout intensity alone, with no actual
# fitness measurement behind it
HEART_RATE_RANGE_BPM = 10


@dataclass
class SessionResult:
    """everything the cli needs to print out about one walk/run session"""

    distance_miles: float
    calories_estimate: float
    calories_low: float
    calories_high: float
    heart_rate_estimate: float
    heart_rate_low: float
    heart_rate_high: float
    elevation_gain_ft: float


def compute_session(weight_kg, height_cm, age_years, sex, speed_mph, incline_percent, duration_minutes):
    """
    runs all three output calculations for one walk/run session and returns them
    bundled together in a SessionResult
    """
    # distance is just speed times time, converted from minutes to hours
    distance_miles = speed_mph * (duration_minutes / 60.0)

    # calories: point estimate from the existing personalized formula, then a
    # flat plus-or-minus band around it, floored at zero since negative
    # calories burned doesn't mean anything
    kcal_per_minute = total_kcal_per_minute(weight_kg, height_cm, age_years, sex, speed_mph, incline_percent)
    calories_estimate = kcal_per_minute * duration_minutes
    calories_low = max(calories_estimate - CALORIE_RANGE_KCAL, 0.0)
    calories_high = calories_estimate + CALORIE_RANGE_KCAL

    # heart rate: point estimate from the age/intensity based method, then a
    # flat plus-or-minus band around it
    heart_rate_estimate = estimated_heart_rate_bpm(age_years, speed_mph, incline_percent)
    heart_rate_low = max(heart_rate_estimate - HEART_RATE_RANGE_BPM, 0.0)
    heart_rate_high = heart_rate_estimate + HEART_RATE_RANGE_BPM

    # elevation gain is exact geometry, not an estimate: a 5% grade means you
    # climb 5 feet for every 100 feet walked forward, so no plus-or-minus band
    elevation_gain_ft = distance_miles * FEET_PER_MILE * (incline_percent / 100.0)

    return SessionResult(
        distance_miles=distance_miles,
        calories_estimate=calories_estimate,
        calories_low=calories_low,
        calories_high=calories_high,
        heart_rate_estimate=heart_rate_estimate,
        heart_rate_low=heart_rate_low,
        heart_rate_high=heart_rate_high,
        elevation_gain_ft=elevation_gain_ft,
    )
