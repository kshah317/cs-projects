"""
takes a single walk/run session (speed, incline, how long) plus the person's own
stats, and turns it into the three outputs the program reports: an estimated
calorie range, an estimated heart rate range, and an exact elevation gain. this
file just does the math and packages up the result, it never talks to the
terminal or asks the user anything.
"""

from dataclasses import dataclass

from calories import total_kcal_per_minute
from heart_rate import estimated_heart_rate_bpm, estimated_max_heart_rate_bpm

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

# the standard five heart-rate-reserve training zones, each defined by the
# minimum percent of max heart rate it starts at. checked from highest to
# lowest so a percentage lands in the first (and therefore highest) zone it
# qualifies for
HEART_RATE_ZONES = [
    (90, "Maximum"),
    (80, "Hard"),
    (70, "Moderate"),
    (60, "Light"),
    (0, "Very Light"),
]


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
    max_heart_rate_bpm: float
    workout_intensity_zone: str
    elevation_gain_ft: float


def workout_intensity_zone(heart_rate_estimate, max_heart_rate_bpm):
    """
    classifies the estimated heart rate as a percent of max heart rate into
    one of the five standard training zones (very light through maximum)
    """
    percent_of_max = (heart_rate_estimate / max_heart_rate_bpm) * 100.0

    # walk down the zone list until we find the highest zone this percentage
    # qualifies for
    for minimum_percent, zone_name in HEART_RATE_ZONES:
        if percent_of_max >= minimum_percent:
            return zone_name

    # unreachable in practice since the last zone's minimum is 0, but keeps
    # the function total in case percent_of_max is somehow negative
    return "Very Light"


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

    # max heart rate (tanaka formula) on its own, so the person can see the
    # ceiling their estimated heart rate is being measured against
    max_heart_rate_bpm = estimated_max_heart_rate_bpm(age_years)

    # classify the estimated heart rate into a training zone, based on what
    # percent of max heart rate it represents
    intensity_zone = workout_intensity_zone(heart_rate_estimate, max_heart_rate_bpm)

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
        max_heart_rate_bpm=max_heart_rate_bpm,
        workout_intensity_zone=intensity_zone,
        elevation_gain_ft=elevation_gain_ft,
    )
