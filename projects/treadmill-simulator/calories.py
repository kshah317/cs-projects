"""
this file holds every formula the simulator uses to turn "weight, height, age, sex,
speed, incline" into a calories-per-minute number. nothing in here talks to the
terminal or reads files, it is pure math, which makes it easy to unit test on its own.

the model has two parts that get added together:

1. a personalized resting burn rate, from the mifflin-st jeor equation. this is the
   standard modern replacement for the older harris-benedict equation, and it uses
   your actual weight, height, age, and sex instead of a generic default.

2. an exercise-only burn rate, from acsm's (american college of sports medicine)
   walking or running metabolic equations. these are the same formulas most gym
   equipment is built on, and they only need speed, incline, and weight.

the acsm equations technically already include a generic "resting" term built in
(the 3.5 constant, equal to one MET). since we already have a personalized resting
rate from mifflin-st jeor, we strip that generic term out of the acsm formula and
only use its speed/incline-driven part, so we are not counting resting metabolism
twice, once generically and once personally.
"""

# a single MET (metabolic equivalent) is defined as 3.5 ml of oxygen per kg of body
# weight per minute, this is the standard "resting" oxygen cost every acsm formula
# below is built around, and we subtract it out since mifflin-st jeor already
# supplies a personalized resting rate
ONE_MET_VO2_ML_PER_KG_PER_MIN = 3.5

# one mile is 1609.34 meters, and there are 60 minutes in an hour, so this converts
# a speed in miles per hour into meters per minute, which is what the acsm formulas
# are written in terms of
METERS_PER_MINUTE_PER_MPH = 1609.34 / 60.0

# acsm's walking equation is validated for speeds roughly in this walking range,
# and the running equation for speeds above it. real treadmills have a similar
# ambiguous gap between "fast walk" and "jog", so we pick 5.0 mph as the single
# crossover point between the two formulas, which sits right at the boundary
# most published acsm references use for "walking versus running"
WALK_TO_RUN_CROSSOVER_MPH = 5.0

# a commonly used conversion from oxygen consumed to energy released: burning
# roughly one liter of oxygen releases about 5 kilocalories, this approximation
# is what acsm's own worked examples use, so we use it too for consistency
KCAL_PER_LITER_OF_OXYGEN = 5.0

# there are 1440 minutes in a day, used to convert a daily resting calorie total
# (what mifflin-st jeor outputs) into a per-minute rate we can add to exercise burn
MINUTES_PER_DAY = 24 * 60


def pounds_to_kilograms(pounds):
    """converts a weight from pounds to kilograms, since every formula below works in kg"""
    # 1 kilogram is about 2.20462 pounds
    return pounds / 2.20462


def feet_and_inches_to_centimeters(feet, inches):
    """converts a height given as feet and inches into centimeters"""
    # first collapse feet and inches into a single inches total
    total_inches = feet * 12 + inches
    # then convert inches to centimeters, since 1 inch is exactly 2.54 cm
    return total_inches * 2.54


def mifflin_st_jeor_resting_kcal_per_day(weight_kg, height_cm, age_years, sex):
    """
    estimates resting metabolic rate in kcal per day, i.e. roughly how many calories
    you would burn lying still for 24 hours, using your actual weight, height, age,
    and biological sex. this is the equation almost every modern fitness app and
    dietitian uses in place of the older, less accurate harris-benedict equation.
    """
    # the weight, height, and age terms are identical for men and women, only the
    # final constant differs by sex
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years)
    # normalize to lowercase so "Male", "male", "M" style inputs are all handled the same way
    sex_normalized = sex.strip().lower()
    if sex_normalized in ("male", "m"):
        # men's constant is +5
        return base + 5
    elif sex_normalized in ("female", "f"):
        # women's constant is -161
        return base - 161
    else:
        # anything else is a usage error, better to fail loudly than silently guess
        raise ValueError(f"sex must be 'male' or 'female', got {sex!r}")


def resting_kcal_per_minute(weight_kg, height_cm, age_years, sex):
    """converts the daily resting rate above into a per-minute rate, for adding to exercise burn"""
    daily_kcal = mifflin_st_jeor_resting_kcal_per_day(weight_kg, height_cm, age_years, sex)
    return daily_kcal / MINUTES_PER_DAY


def acsm_exercise_vo2_ml_per_kg_per_minute(speed_mph, incline_percent):
    """
    computes the exercise-only oxygen cost (in ml per kg of body weight per minute)
    of walking or running at a given speed and incline, using acsm's published
    metabolic equations. the generic resting term (one MET) has already been
    removed from both formulas below, since we add a personalized resting rate
    from mifflin-st jeor separately instead.
    """
    # convert the incoming speed and incline into the units the raw acsm formulas expect
    speed_m_per_min = speed_mph * METERS_PER_MINUTE_PER_MPH
    # acsm's grade term is a fraction (e.g. 8% incline is 0.08), not a whole percent
    grade_fraction = incline_percent / 100.0

    if speed_mph < WALK_TO_RUN_CROSSOVER_MPH:
        # walking equation: 0.1 ml/kg/min for every meter/min of speed, plus
        # 1.8 ml/kg/min for every meter/min of speed multiplied by the grade
        exercise_vo2 = (0.1 * speed_m_per_min) + (1.8 * speed_m_per_min * grade_fraction)
    else:
        # running equation: same shape, different constants, since running is a
        # less economical gait than walking at a matched speed
        exercise_vo2 = (0.2 * speed_m_per_min) + (0.9 * speed_m_per_min * grade_fraction)

    # exercise_vo2 here is already "on top of resting", since we never added the
    # 3.5 ml/kg/min baseline term in the first place
    return exercise_vo2


def exercise_kcal_per_minute(speed_mph, incline_percent, weight_kg):
    """
    converts the exercise-only vo2 rate above into an actual calories-per-minute
    number, by scaling by body weight and then by the oxygen-to-energy conversion
    """
    # multiplying the per-kg vo2 rate by weight gives total ml of oxygen per minute
    vo2_ml_per_min = acsm_exercise_vo2_ml_per_kg_per_minute(speed_mph, incline_percent) * weight_kg
    # convert milliliters of oxygen to liters, then liters to kilocalories
    vo2_liters_per_min = vo2_ml_per_min / 1000.0
    return vo2_liters_per_min * KCAL_PER_LITER_OF_OXYGEN


def total_kcal_per_minute(weight_kg, height_cm, age_years, sex, speed_mph, incline_percent):
    """
    the single function the rest of the program calls: adds the personalized
    resting rate to the exercise-only rate to get one combined calories-per-minute
    number for a given moment of the workout
    """
    resting = resting_kcal_per_minute(weight_kg, height_cm, age_years, sex)
    exercise = exercise_kcal_per_minute(speed_mph, incline_percent, weight_kg)
    return resting + exercise
