"""
the interactive front end for the treadmill simulator. this file is the only one
that talks to the terminal: it asks the person running it for their stats, plays
back a predefined workout with a live animated display, and prints a final summary
card plus a small chart showing calories building up over the workout.

all the actual math lives in calories.py and workout.py, this file just presents it.
"""

# sys is used to read an optional workout file path from the command line
import sys
# time.sleep is what makes the playback animate instead of printing everything instantly
import time

# rich's Console is the main object used to print styled text to the terminal
from rich.console import Console
# Prompt/FloatPrompt/IntPrompt ask the user a question and validate/convert their answer
from rich.prompt import Prompt, FloatPrompt, IntPrompt
# Panel draws a bordered box around text, used for the welcome banner and summary card
from rich.panel import Panel
# Progress and its columns build the animated progress bar during playback
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
# Table renders the segment-by-segment breakdown at the end in neat columns
from rich.table import Table
# Live lets us redraw a chunk of the terminal in place, instead of scrolling forever
from rich.live import Live
# Group stacks several renderables (the progress bar and the stats panel) into one
# object, so a single live.update() call redraws both together without leftover output
from rich.console import Group

# our own modules: the pure calorie math, and the workout loading/accumulation logic
from calories import pounds_to_kilograms, feet_and_inches_to_centimeters
from workout import load_workout_plan, run_workout, total_kcal_per_minute

# a single console object is reused everywhere, this is rich's recommended pattern
console = Console()

# controls how fast the animated playback runs: this many real seconds pass for
# every one simulated minute of the workout, kept small so even a 45 minute
# workout finishes animating in well under a minute
ANIMATION_SECONDS_PER_SIMULATED_MINUTE = 0.25

# how many little animation "ticks" we break each segment into, higher means
# smoother-looking progress bar movement within a single segment
TICKS_PER_SEGMENT = 20


def collect_user_stats():
    """
    asks the person running the program for the four inputs the calorie formulas
    need, with friendly prompts and basic validation, and returns them already
    converted into the metric units the math functions expect
    """
    console.print(Panel.fit(
        "[bold cyan]Treadmill Simulator[/bold cyan]\n"
        "Let's get your stats so the calorie math is personalized to you.",
        border_style="cyan",
    ))

    # FloatPrompt.ask keeps re-asking automatically if the person types something
    # that isn't a valid number, so we don't need to write our own retry loop
    weight_lbs = FloatPrompt.ask("Weight (lbs)")
    height_feet = IntPrompt.ask("Height, feet part")
    height_inches = IntPrompt.ask("Height, remaining inches part")
    age_years = IntPrompt.ask("Age (years)")
    # Prompt.ask with a choices list only accepts one of the listed answers,
    # which keeps the mifflin-st jeor sex input unambiguous
    sex = Prompt.ask("Biological sex", choices=["male", "female"])

    # convert everything into the metric units calories.py works in, right at the
    # boundary between "user input" and "math", so nothing downstream has to
    # think about units again
    weight_kg = pounds_to_kilograms(weight_lbs)
    height_cm = feet_and_inches_to_centimeters(height_feet, height_inches)

    return weight_kg, height_cm, age_years, sex


def animate_workout(segments, weight_kg, height_cm, age_years, sex):
    """
    plays the workout back segment by segment, with a live progress bar and a
    constantly updating line of stats, similar to watching a real treadmill
    console while you exercise, just sped up
    """
    total_minutes = sum(segment.duration_minutes for segment in segments)

    # running totals that grow as we animate through each segment, mirroring
    # exactly what run_workout() computes all at once, just revealed gradually
    elapsed_minutes = 0.0
    distance_so_far = 0.0
    calories_so_far = 0.0

    # a Progress bar tracks fraction of total workout minutes completed so far
    progress = Progress(
        TextColumn("[bold]{task.fields[label]}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
    task_id = progress.add_task("workout", total=total_minutes, label="Workout progress")

    # Live redraws whatever renderable we hand it in place, so the terminal shows
    # a moving picture instead of an ever-growing scroll of printed lines
    with Live(console=console, refresh_per_second=12) as live:
        for segment in segments:
            # the calorie rate is constant within a segment, so we only need to compute it once
            kcal_per_minute = total_kcal_per_minute(
                weight_kg, height_cm, age_years, sex,
                segment.speed_mph, segment.incline_percent,
            )
            # break this segment into small ticks so the bar and stats move smoothly
            # instead of jumping straight from segment start to segment end
            minutes_per_tick = segment.duration_minutes / TICKS_PER_SEGMENT
            seconds_per_tick = (
                minutes_per_tick * ANIMATION_SECONDS_PER_SIMULATED_MINUTE
            )

            for _ in range(TICKS_PER_SEGMENT):
                # advance the running totals by one tick's worth of time
                elapsed_minutes += minutes_per_tick
                distance_so_far += segment.speed_mph * (minutes_per_tick / 60.0)
                calories_so_far += kcal_per_minute * minutes_per_tick

                progress.update(task_id, completed=elapsed_minutes)

                # build the live stats panel shown just below the progress bar
                stats_panel = Panel(
                    f"[bold]Speed:[/bold] {segment.speed_mph:.1f} mph   "
                    f"[bold]Incline:[/bold] {segment.incline_percent:.1f}%   "
                    f"[bold]Distance:[/bold] {distance_so_far:.2f} mi   "
                    f"[bold]Calories:[/bold] {calories_so_far:.1f} kcal",
                    border_style="green",
                    title="Live stats",
                )
                # Group stacks the progress bar and the stats panel into one renderable,
                # so this single live.update() call redraws both in place together,
                # instead of the progress bar and a separately printed line fighting
                # over the same terminal lines
                live.update(Group(progress, stats_panel))

                # this sleep is what actually creates the animation, without it
                # every tick would render and disappear instantly
                time.sleep(max(seconds_per_tick / TICKS_PER_SEGMENT, 0.01))


def print_summary(result):
    """prints the end-of-workout summary card and a segment breakdown table"""
    console.print()
    console.print(Panel.fit(
        f"[bold]Total time:[/bold] {result.total_minutes:.1f} minutes\n"
        f"[bold]Total distance:[/bold] {result.total_distance_miles:.2f} miles\n"
        f"[bold]Average pace:[/bold] {result.average_pace_minutes_per_mile:.2f} min/mile\n"
        f"[bold]Total calories:[/bold] {result.total_calories:.1f} kcal",
        title="Workout complete",
        border_style="magenta",
    ))

    # a table listing each segment's own numbers, so you can see exactly where
    # your calories came from during the workout, not just the final total
    table = Table(title="Segment breakdown")
    table.add_column("Speed (mph)", justify="right")
    table.add_column("Incline (%)", justify="right")
    table.add_column("Duration (min)", justify="right")
    table.add_column("Distance (mi)", justify="right")
    table.add_column("Calories", justify="right")
    table.add_column("kcal/min", justify="right")

    for segment_result in result.segment_results:
        segment = segment_result.segment
        table.add_row(
            f"{segment.speed_mph:.1f}",
            f"{segment.incline_percent:.1f}",
            f"{segment.duration_minutes:.1f}",
            f"{segment_result.distance_miles:.2f}",
            f"{segment_result.calories:.1f}",
            f"{segment_result.kcal_per_minute:.2f}",
        )
    console.print(table)

    # a tiny ascii bar chart of calorie burn rate per segment, so the near-linear
    # relationship between speed/incline and calorie burn is visible at a glance
    console.print("\n[bold]Calorie burn rate by segment:[/bold]")
    max_rate = max(sr.kcal_per_minute for sr in result.segment_results)
    for index, segment_result in enumerate(result.segment_results, start=1):
        # scale each bar to a max width of 40 characters, relative to the highest rate seen
        bar_length = int((segment_result.kcal_per_minute / max_rate) * 40)
        bar = "#" * bar_length
        console.print(
            f"segment {index:>2} [{segment_result.segment.speed_mph:>4.1f} mph, "
            f"{segment_result.segment.incline_percent:>4.1f}% incline]  "
            f"{bar} {segment_result.kcal_per_minute:.2f} kcal/min"
        )


def main():
    """entry point: collects stats, loads the workout, plays it back, prints the summary"""
    # default to the bundled sample workout unless the person passes their own file
    workout_path = sys.argv[1] if len(sys.argv) > 1 else "sample_workout.json"

    weight_kg, height_cm, age_years, sex = collect_user_stats()
    segments = load_workout_plan(workout_path)

    console.print(f"\n[bold]Loaded workout:[/bold] {workout_path} ({len(segments)} segments)\n")
    animate_workout(segments, weight_kg, height_cm, age_years, sex)

    # after the animation, recompute the exact final numbers with run_workout(),
    # rather than trusting the animation's own running totals, so the printed
    # summary is guaranteed to match the real math exactly
    result = run_workout(segments, weight_kg, height_cm, age_years, sex)
    print_summary(result)


if __name__ == "__main__":
    main()
