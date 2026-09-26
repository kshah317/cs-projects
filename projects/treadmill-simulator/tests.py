"""
unit tests for the calorie, heart rate, and session formulas. the formula tests
check against numbers worked out by hand from the same published acsm,
mifflin-st jeor, tanaka, and uth equations, so we know the code matches the real
math, not just that it runs without crashing.
"""

# unittest is python's built-in testing framework
import unittest

from calories import (
    pounds_to_kilograms,
    feet_and_inches_to_centimeters,
    mifflin_st_jeor_resting_kcal_per_day,
    acsm_exercise_vo2_ml_per_kg_per_minute,
    total_vo2_ml_per_kg_per_minute,
)
from heart_rate import (
    estimated_max_heart_rate_bpm,
    estimated_vo2_max_ml_per_kg_per_minute,
    estimated_heart_rate_bpm,
    ASSUMED_RESTING_HEART_RATE_BPM,
)
from session import compute_session


class UnitConversionTests(unittest.TestCase):
    """checks the small unit conversion helpers used at the input boundary"""

    def test_pounds_to_kilograms(self):
        # 154 lbs is a commonly cited reference weight, about 69.85 kg
        self.assertAlmostEqual(pounds_to_kilograms(154), 69.853, places=2)

    def test_feet_and_inches_to_centimeters(self):
        # 5 feet 10 inches is 70 inches total, which is 177.8 cm
        self.assertAlmostEqual(feet_and_inches_to_centimeters(5, 10), 177.8, places=1)


class MifflinStJeorTests(unittest.TestCase):
    """checks the resting metabolic rate formula against hand-calculated values"""

    def test_male_resting_rate(self):
        # 70 kg, 170 cm, 30 years old, male:
        # 10*70 + 6.25*170 - 5*30 + 5 = 700 + 1062.5 - 150 + 5 = 1617.5
        rate = mifflin_st_jeor_resting_kcal_per_day(70, 170, 30, "male")
        self.assertAlmostEqual(rate, 1617.5, places=1)

    def test_female_resting_rate(self):
        # same stats, female: 700 + 1062.5 - 150 - 161 = 1451.5
        rate = mifflin_st_jeor_resting_kcal_per_day(70, 170, 30, "female")
        self.assertAlmostEqual(rate, 1451.5, places=1)

    def test_invalid_sex_raises(self):
        # anything other than male/female should fail loudly, not guess
        with self.assertRaises(ValueError):
            mifflin_st_jeor_resting_kcal_per_day(70, 170, 30, "other")


class AcsmExerciseVo2Tests(unittest.TestCase):
    """checks the walking and running vo2 formulas against hand-calculated values"""

    def test_walking_flat_ground(self):
        # 3.0 mph is 80.47 m/min (3.0 * 1609.34 / 60). at 0% grade, exercise-only
        # vo2 (with the 3.5 resting term already excluded) is 0.1 * 80.47 = 8.047
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(3.0, 0)
        self.assertAlmostEqual(vo2, 8.047, places=1)

    def test_running_flat_ground(self):
        # 6.0 mph is 160.93 m/min. running formula, 0% grade: 0.2*160.93 = 32.19
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(6.0, 0)
        self.assertAlmostEqual(vo2, 32.19, places=1)

    def test_total_vo2_includes_resting_baseline(self):
        # total vo2 should be exactly 3.5 more than the exercise-only vo2, since
        # it adds back the generic one-MET resting term that acsm's exercise-only
        # number has stripped out
        exercise_only = acsm_exercise_vo2_ml_per_kg_per_minute(4.0, 2)
        total = total_vo2_ml_per_kg_per_minute(4.0, 2)
        self.assertAlmostEqual(total - exercise_only, 3.5, places=6)


class HeartRateTests(unittest.TestCase):
    """checks the age/intensity based heart rate estimate against hand-calculated values"""

    def test_max_heart_rate_from_age(self):
        # tanaka formula: 208 - 0.7*30 = 187
        self.assertAlmostEqual(estimated_max_heart_rate_bpm(30), 187, places=1)

    def test_vo2_max_from_age(self):
        # max heart rate at 30 is 187, so vo2max = 15.3 * (187/70) = 40.87...
        vo2_max = estimated_vo2_max_ml_per_kg_per_minute(30, ASSUMED_RESTING_HEART_RATE_BPM)
        self.assertAlmostEqual(vo2_max, 15.3 * (187 / 70), places=2)

    def test_heart_rate_stays_within_resting_and_max(self):
        # however intense the workout, the estimate should never fall below the
        # assumed resting heart rate or exceed the estimated max heart rate
        heart_rate = estimated_heart_rate_bpm(30, 6.0, 10)
        self.assertGreaterEqual(heart_rate, ASSUMED_RESTING_HEART_RATE_BPM)
        self.assertLessEqual(heart_rate, estimated_max_heart_rate_bpm(30))

    def test_faster_speed_raises_estimated_heart_rate(self):
        # this mirrors the same "faster means more effort" relationship the
        # calorie math has: a faster walk/run at the same incline should raise
        # the heart rate estimate, not lower or leave it unchanged
        slow_heart_rate = estimated_heart_rate_bpm(30, 3.0, 2)
        fast_heart_rate = estimated_heart_rate_bpm(30, 5.5, 2)
        self.assertGreater(fast_heart_rate, slow_heart_rate)

    def test_steeper_incline_raises_estimated_heart_rate(self):
        flat_heart_rate = estimated_heart_rate_bpm(30, 3.0, 0)
        steep_heart_rate = estimated_heart_rate_bpm(30, 3.0, 10)
        self.assertGreater(steep_heart_rate, flat_heart_rate)

    def test_extreme_effort_clamps_at_max_heart_rate(self):
        # a very fast, steep, long effort could otherwise imply needing more
        # oxygen than the estimated vo2max allows, which isn't meaningful, so
        # the estimate should clamp at the estimated max heart rate instead
        heart_rate = estimated_heart_rate_bpm(60, 12.0, 15)
        self.assertAlmostEqual(heart_rate, estimated_max_heart_rate_bpm(60), places=6)


class SessionCalculationTests(unittest.TestCase):
    """checks that a single session's distance, calorie range, heart rate range, and elevation gain are correct"""

    def test_distance_is_speed_times_time(self):
        result = compute_session(70, 170, 30, "male", speed_mph=6.0, incline_percent=0, duration_minutes=30)
        # 6.0 mph for 30 minutes (half an hour) is 3.0 miles
        self.assertAlmostEqual(result.distance_miles, 3.0, places=6)

    def test_calorie_range_is_centered_on_estimate(self):
        result = compute_session(70, 170, 30, "male", speed_mph=4.0, incline_percent=2, duration_minutes=20)
        self.assertAlmostEqual(result.calories_high - result.calories_estimate, 20, places=6)
        self.assertAlmostEqual(result.calories_estimate - result.calories_low, 20, places=6)

    def test_calorie_low_floors_at_zero(self):
        # a very short, easy session could otherwise produce a negative low end,
        # which doesn't mean anything for calories burned
        result = compute_session(70, 170, 30, "male", speed_mph=1.0, incline_percent=0, duration_minutes=1)
        self.assertGreaterEqual(result.calories_low, 0)

    def test_heart_rate_range_is_centered_on_estimate(self):
        result = compute_session(70, 170, 30, "male", speed_mph=4.0, incline_percent=2, duration_minutes=20)
        self.assertAlmostEqual(result.heart_rate_high - result.heart_rate_estimate, 10, places=6)
        self.assertAlmostEqual(result.heart_rate_estimate - result.heart_rate_low, 10, places=6)

    def test_elevation_gain_is_exact_geometry(self):
        # 5% grade over 1 mile means climbing 5% of 5280 feet = 264 feet. here,
        # 4.0 mph for 30 minutes (half an hour) covers exactly 2.0 miles, so
        # a 5% grade over that distance is 2.0 * 5280 * 0.05 = 528 feet
        result = compute_session(70, 170, 30, "male", speed_mph=4.0, incline_percent=5, duration_minutes=30)
        self.assertAlmostEqual(result.elevation_gain_ft, 528, places=1)

    def test_flat_ground_has_zero_elevation_gain(self):
        result = compute_session(70, 170, 30, "male", speed_mph=4.0, incline_percent=0, duration_minutes=30)
        self.assertAlmostEqual(result.elevation_gain_ft, 0, places=6)


if __name__ == "__main__":
    unittest.main()
