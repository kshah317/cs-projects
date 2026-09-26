"""
the interactive front end for the treadmill simulator. asks for your stats once,
then asks for the speed, incline, and length of a single walk/run, and prints an
instant results card with the three outputs: an estimated calorie range, an
estimated heart rate range, and an exact elevation gain.

all the actual math lives in calories.py, heart_rate.py, and session.py, this
file just presents it.
"""

# rich's Console is the main object used to print styled text to the terminal
from rich.console import Console
# Prompt/FloatPrompt ask the user a question and validate/convert their answer
from rich.prompt import Prompt, FloatPrompt
# Panel draws a bordered box around text, used for the welcome banner and results card
from rich.panel import Panel

# our own modules: unit conversion helpers, and the single-session math
from calories import pounds_to_kilograms, feet_and_inches_to_centimeters
from session import compute_session

# a single console object is reused everywhere, this is rich's recommended pattern
console = Console()

# real gym treadmills like precor's cap incline at 15 percent grade, so we keep
# the same cap here rather than accepting an unrealistic value
MINIMUM_INCLINE_PERCENT = 0
MAXIMUM_INCLINE_PERCENT = 15

# lets the sex prompt accept short forms (m/f) in any case, normalized down
# to the "male"/"female" strings the mifflin-st jeor formula expects
SEX_INPUT_ALIASES = {
    "male": "male",
    "m": "male",
    "female": "female",
    "f": "female",
}


def collect_user_stats():
    """
    asks for the four inputs the calorie and heart rate formulas need, with
    friendly prompts and basic validation, and returns them already converted
    into the metric units the math functions expect
    """
    console.print(Panel.fit(
        "[bold cyan]Treadmill Simulator[/bold cyan]\n"
        "Let's get your stats so the estimates are personalized to you.",
        border_style="cyan",
    ))

    # FloatPrompt.ask keeps re-asking automatically if the person types something
    # that isn't a valid number, so we don't need to write our own retry loop
    weight_lbs = FloatPrompt.ask("Weight (lbs)")
    height_feet = FloatPrompt.ask("Height, feet part")
    height_inches = FloatPrompt.ask("Height, remaining inches part")
    age_years = FloatPrompt.ask("Age (years)")
    # accept short forms (m/f, any case) alongside the full words, then
    # normalize down to "male"/"female" so nothing downstream has to think
    # about which spelling the person typed
    sex_input = Prompt.ask(
        "Biological sex (male/female, or m/f)",
        choices=["male", "female", "m", "f"],
        case_sensitive=False,
        show_choices=False,
    )
    sex = SEX_INPUT_ALIASES[sex_input.lower()]

    # convert everything into the metric units calories.py works in, right at the
    # boundary between "user input" and "math", so nothing downstream has to
    # think about units again
    weight_kg = pounds_to_kilograms(weight_lbs)
    height_cm = feet_and_inches_to_centimeters(height_feet, height_inches)

    return weight_kg, height_cm, age_years, sex


def collect_session_inputs():
    """
    asks for the speed, incline, and duration of a single walk/run, with basic
    range checks so the incline stays inside what a real treadmill supports
    """
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Now describe the walk/run[/bold cyan]",
        border_style="cyan",
    ))

    speed_mph = FloatPrompt.ask("Speed (mph)")

    # keep re-asking until the incline is inside the range a real treadmill supports
    while True:
        incline_percent = FloatPrompt.ask(
            f"Incline ({MINIMUM_INCLINE_PERCENT} to {MAXIMUM_INCLINE_PERCENT} percent grade)"
        )
        if MINIMUM_INCLINE_PERCENT <= incline_percent <= MAXIMUM_INCLINE_PERCENT:
            break
        console.print(
            f"[red]Incline must be between {MINIMUM_INCLINE_PERCENT} and {MAXIMUM_INCLINE_PERCENT}.[/red]"
        )

    duration_minutes = FloatPrompt.ask("Length of walk/run (minutes)")

    return speed_mph, incline_percent, duration_minutes


def print_results(result):
    """prints the results card with the three outputs, once the session has been computed"""
    console.print()
    console.print(Panel.fit(
        f"[bold]Distance:[/bold] {result.distance_miles:.2f} mi\n\n"
        f"[bold]Estimated calories burned:[/bold] "
        f"{result.calories_low:.0f}-{result.calories_high:.0f} kcal "
        f"(estimate: {result.calories_estimate:.0f})\n"
        f"[bold]Estimated heart rate:[/bold] "
        f"{result.heart_rate_low:.0f}-{result.heart_rate_high:.0f} bpm "
        f"(estimate: {result.heart_rate_estimate:.0f}, "
        f"max heart rate: {result.max_heart_rate_bpm:.0f})\n"
        f"[bold]Workout Intensity based on MHR:[/bold] {result.workout_intensity_zone}\n"
        f"[bold]Elevation gain:[/bold] {result.elevation_gain_ft:.0f} ft",
        title="Results",
        border_style="magenta",
    ))


def main():
    """entry point: collects stats and session inputs, computes the result, prints it"""
    weight_kg, height_cm, age_years, sex = collect_user_stats()
    speed_mph, incline_percent, duration_minutes = collect_session_inputs()

    result = compute_session(weight_kg, height_cm, age_years, sex, speed_mph, incline_percent, duration_minutes)
    print_results(result)


if __name__ == "__main__":
    main()
