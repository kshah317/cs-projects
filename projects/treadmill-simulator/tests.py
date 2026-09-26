"""
unit tests for the calorie formulas and workout accumulation logic. the formula
tests check against numbers worked out by hand from the same published acsm and
mifflin-st jeor equations, so we know the code matches the real math, not just
that it runs without crashing.
"""

# unittest is python's built-in testing framework
import unittest
# json and tempfile are used to build a small throwaway workout file for the loader test
import json
import tempfile
import os

from calories import (
    pounds_to_kilograms,
    feet_and_inches_to_centimeters,
    mifflin_st_jeor_resting_kcal_per_day,
    acsm_exercise_vo2_ml_per_kg_per_minute,
)
from workout import Segment, load_workout_plan, run_workout


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

    def test_sex_input_is_case_insensitive(self):
        # "Male" and "male" should give the identical result
        rate_lower = mifflin_st_jeor_resting_kcal_per_day(70, 170, 30, "male")
        rate_mixed_case = mifflin_st_jeor_resting_kcal_per_day(70, 170, 30, "Male")
        self.assertEqual(rate_lower, rate_mixed_case)


class AcsmExerciseVo2Tests(unittest.TestCase):
    """checks the walking and running vo2 formulas against hand-calculated values"""

    def test_walking_flat_ground(self):
        # 3.0 mph is 80.47 m/min (3.0 * 1609.34 / 60). at 0% grade, exercise-only
        # vo2 (with the 3.5 resting term already excluded) is 0.1 * 80.47 = 8.047
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(3.0, 0)
        self.assertAlmostEqual(vo2, 8.047, places=1)

    def test_walking_with_incline(self):
        # same 3.0 mph, now at 5% grade: 0.1*80.47 + 1.8*80.47*0.05 = 8.047 + 7.24 = 15.29
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(3.0, 5)
        self.assertAlmostEqual(vo2, 15.29, places=1)

    def test_running_flat_ground(self):
        # 6.0 mph is 160.93 m/min. running formula, 0% grade: 0.2*160.93 = 32.19
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(6.0, 0)
        self.assertAlmostEqual(vo2, 32.19, places=1)

    def test_crossover_point_uses_running_formula(self):
        # exactly 5.0 mph should use the running formula, not walking, since the
        # crossover check is "speed < 5.0 uses walking", so 5.0 itself is running
        walking_style_result = 0.1 * (5.0 * 1609.34 / 60)
        running_style_result = 0.2 * (5.0 * 1609.34 / 60)
        vo2 = acsm_exercise_vo2_ml_per_kg_per_minute(5.0, 0)
        self.assertAlmostEqual(vo2, running_style_result, places=1)
        self.assertNotAlmostEqual(vo2, walking_style_result, places=1)


class WorkoutAccumulationTests(unittest.TestCase):
    """checks that segments accumulate into correct running totals"""

    def test_single_segment_distance_and_calories(self):
        # 10 minutes at 3.0 mph should cover exactly 0.5 miles
        segment = Segment(duration_minutes=10, speed_mph=3.0, incline_percent=0)
        result = run_workout([segment], weight_kg=70, height_cm=170, age_years=30, sex="male")
        self.assertAlmostEqual(result.total_distance_miles, 0.5, places=3)
        # calories should be strictly positive and finite for a normal workout
        self.assertGreater(result.total_calories, 0)

    def test_multiple_segments_sum_correctly(self):
        # two 10 minute segments should sum to 20 total minutes and the sum of
        # each segment's own distance and calories
        segments = [
            Segment(duration_minutes=10, speed_mph=3.0, incline_percent=0),
            Segment(duration_minutes=10, speed_mph=4.0, incline_percent=2),
        ]
        result = run_workout(segments, weight_kg=70, height_cm=170, age_years=30, sex="male")
        self.assertAlmostEqual(result.total_minutes, 20, places=3)
        expected_distance = 3.0 * (10 / 60) + 4.0 * (10 / 60)
        self.assertAlmostEqual(result.total_distance_miles, expected_distance, places=3)
        # the sum of the two segments' individual calorie totals should equal the workout total
        summed_calories = sum(sr.calories for sr in result.segment_results)
        self.assertAlmostEqual(summed_calories, result.total_calories, places=6)

    def test_average_pace_is_time_over_distance(self):
        segment = Segment(duration_minutes=15, speed_mph=5.0, incline_percent=0)
        result = run_workout([segment], weight_kg=70, height_cm=170, age_years=30, sex="male")
        # at 5.0 mph for 15 minutes, distance is 1.25 miles, so pace is 15/1.25 = 12 min/mile
        self.assertAlmostEqual(result.average_pace_minutes_per_mile, 12.0, places=3)

    def test_faster_speed_burns_more_calories_per_minute(self):
        # this is the "almost linear" relationship the whole project is built
        # around: a faster segment at the same incline should burn calories
        # faster, not slower or the same
        slow_segment = Segment(duration_minutes=10, speed_mph=3.0, incline_percent=2)
        fast_segment = Segment(duration_minutes=10, speed_mph=4.5, incline_percent=2)
        result = run_workout(
            [slow_segment, fast_segment], weight_kg=70, height_cm=170, age_years=30, sex="male"
        )
        slow_rate = result.segment_results[0].kcal_per_minute
        fast_rate = result.segment_results[1].kcal_per_minute
        self.assertGreater(fast_rate, slow_rate)

    def test_steeper_incline_burns_more_calories_per_minute(self):
        # same idea, but holding speed fixed and increasing incline instead
        flat_segment = Segment(duration_minutes=10, speed_mph=3.0, incline_percent=0)
        steep_segment = Segment(duration_minutes=10, speed_mph=3.0, incline_percent=10)
        result = run_workout(
            [flat_segment, steep_segment], weight_kg=70, height_cm=170, age_years=30, sex="male"
        )
        flat_rate = result.segment_results[0].kcal_per_minute
        steep_rate = result.segment_results[1].kcal_per_minute
        self.assertGreater(steep_rate, flat_rate)


class WorkoutPlanLoaderTests(unittest.TestCase):
    """checks that a workout plan json file loads into the right Segment objects"""

    def test_load_workout_plan_from_json(self):
        # build a tiny two-segment workout file in a temp location, load it back,
        # and confirm the fields all round-tripped correctly
        raw_segments = [
            {"duration_minutes": 5, "speed_mph": 3.0, "incline_percent": 0},
            {"duration_minutes": 10, "speed_mph": 4.5, "incline_percent": 3},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(raw_segments, temp_file)
            temp_path = temp_file.name

        try:
            segments = load_workout_plan(temp_path)
            self.assertEqual(len(segments), 2)
            self.assertEqual(segments[0].duration_minutes, 5)
            self.assertEqual(segments[1].speed_mph, 4.5)
            self.assertEqual(segments[1].incline_percent, 3)
        finally:
            # clean up the temp file regardless of whether the assertions passed
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
