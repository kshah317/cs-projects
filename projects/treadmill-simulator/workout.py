"""
this file loads a predefined workout plan from a json file, and runs the math that
turns "a list of segments" plus "a person's stats" into minute-by-minute totals for
distance, time, and calories, the same way a treadmill console accumulates these
numbers live as you exercise.
"""

# json is python's standard library tool for reading .json files
import json
# dataclass gives us a clean way to define small data-holding classes without
# writing boilerplate __init__ methods by hand
from dataclasses import dataclass
# List is used purely for type hints, so the workout structure is self-documenting
from typing import List

# our own calorie math lives in calories.py, imported here so workout.py never
# has to know the formulas itself, just how to apply them over time
from calories import total_kcal_per_minute


@dataclass
class Segment:
    """
    one block of a workout, e.g. "5 minutes at 3.0 mph, 0% incline". a full workout
    is just a list of these, played one after another
    """
    duration_minutes: float  # how long this segment lasts
    speed_mph: float          # treadmill belt speed during this segment
    incline_percent: float    # treadmill incline during this segment, 0 to 15


@dataclass
class SegmentResult:
    """the computed outcome of a single segment, once we know the person's stats"""
    segment: Segment          # the original segment this result came from
    distance_miles: float     # how far this segment covered
    calories: float           # how many calories this segment burned
    kcal_per_minute: float    # the burn rate during this segment, used for the chart


@dataclass
class WorkoutResult:
    """the full computed outcome of an entire workout: every segment, plus running totals"""
    segment_results: List[SegmentResult]  # one entry per segment, in order
    total_minutes: float                   # sum of every segment's duration
    total_distance_miles: float            # sum of every segment's distance
    total_calories: float                  # sum of every segment's calories

    @property
    def average_pace_minutes_per_mile(self):
        """
        pace is usually reported as minutes per mile, not miles per minute, since
        that is the more familiar way runners and walkers talk about speed
        """
        # guard against dividing by zero if somehow no distance was covered
        if self.total_distance_miles == 0:
            return 0.0
        return self.total_minutes / self.total_distance_miles


def load_workout_plan(json_path):
    """
    reads a workout plan from a json file and turns it into a list of Segment
    objects. the expected json shape is a list of objects, each with
    duration_minutes, speed_mph, and incline_percent keys
    """
    with open(json_path, "r") as workout_file:
        raw_segments = json.load(workout_file)

    segments = []
    for raw_segment in raw_segments:
        # ** unpacks the dictionary's keys directly into the Segment's constructor
        # arguments, so the json keys must exactly match the Segment field names
        segments.append(Segment(**raw_segment))
    return segments


def run_workout(segments, weight_kg, height_cm, age_years, sex):
    """
    walks through every segment in order, computing that segment's distance and
    calories, and building up the running totals a treadmill console would show
    """
    segment_results = []
    total_minutes = 0.0
    total_distance_miles = 0.0
    total_calories = 0.0

    for segment in segments:
        # miles covered in this segment is just speed times how long we spent at that speed
        distance_miles = segment.speed_mph * (segment.duration_minutes / 60.0)

        # the calorie burn rate at this segment's speed and incline, personalized
        # to this specific person's weight, height, age, and sex
        kcal_per_minute = total_kcal_per_minute(
            weight_kg, height_cm, age_years, sex,
            segment.speed_mph, segment.incline_percent,
        )
        # total calories for this segment is just that rate multiplied by how long it lasted
        calories = kcal_per_minute * segment.duration_minutes

        # record this segment's individual result before moving on to the next one
        segment_results.append(SegmentResult(
            segment=segment,
            distance_miles=distance_miles,
            calories=calories,
            kcal_per_minute=kcal_per_minute,
        ))

        # fold this segment's numbers into the running workout totals
        total_minutes += segment.duration_minutes
        total_distance_miles += distance_miles
        total_calories += calories

    return WorkoutResult(
        segment_results=segment_results,
        total_minutes=total_minutes,
        total_distance_miles=total_distance_miles,
        total_calories=total_calories,
    )
