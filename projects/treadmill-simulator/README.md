  # Treadmill Simulator

A terminal program that replays a treadmill workout and estimates your calorie burn, using the same kind of formulas real gym equipment runs on.

## Why I built this

I use a treadmill at the gym a lot, and I started noticing that the calorie counter felt almost linear with speed and incline. Bump the speed up a bit and the calories per minute went up by a predictable amount every time. I wanted to figure out if that was really true, and if so, why, so I looked into the actual formulas behind treadmill calorie estimates and built my own version of one.

It turns out most consoles don't ask for your weight, height, age, or gender at all. They just assume a generic body (something like 155 pounds) and run the math against that. So the number on the screen is really an estimate for an average stranger, not you. I wanted my version to actually use your real stats, since that's the part that makes the biggest difference to accuracy.

## What it does

You enter your weight, height, age, and gender once at the start. Then it loads a workout plan (a list of segments like "5 minutes at 3 mph" or "10 minutes at 4 mph with a 4 percent incline") and plays it back with a live animated progress bar and stats, sped up so a 30 minute workout takes a few seconds to watch. At the end you get a summary card with your total time, distance, pace, and calories, plus a segment by segment breakdown and a little bar chart so you can see the calorie burn rate climb with speed and incline, the exact pattern that got me curious in the first place.

## How the calorie math works

Calorie burn during exercise comes from two pieces added together.

The first piece is your resting burn rate, meaning roughly how many calories your body burns just existing, before you even step on the treadmill. I calculate this with the Mifflin-St Jeor equation, which is the standard formula fitness apps and dietitians use today. It takes your weight, height, age, and gender and gives you a personalized number, instead of guessing.

The second piece is the extra burn from the exercise itself. For that I use the walking and running formulas published by the American College of Sports Medicine (ACSM), the same body of research most treadmill software is quietly built on. These formulas take your speed, your incline, and your weight, and output how much extra oxygen your body is using compared to sitting still. More oxygen used means more calories burned, using a standard conversion rate. Below about 5 mph it uses the walking formula, above that it switches to the running formula, since running and walking burn calories differently even at the same speed.

Add the resting piece and the exercise piece together, multiply by how many minutes you spent at that speed and incline, and that's your calorie count for that segment. Do that for every segment and add them up, and that's the whole engine behind this project.

## Incline note

Incline here is a percent grade, from 0 to 15, matching how real gym treadmills like Precor's display it. A 5 percent incline means for every 100 feet you walk forward, you also climb 5 feet up.

## Project structure

```
treadmill-simulator/
README.md
calories.py          <- the Mifflin-St Jeor and ACSM formulas, pure math, no terminal code
workout.py           <- loads a workout plan and adds up time, distance, and calories segment by segment
cli.py                <- the interactive terminal program: asks for your stats, animates the workout, prints the summary
sample_workout.json    <- an example workout plan you can run or copy to make your own
tests.py                <- unit tests checking the formulas against hand-worked numbers
```

## Run it

```bash
pip install rich
python cli.py sample_workout.json
```

Leave off the filename and it uses the bundled sample workout. Want your own workout? Copy `sample_workout.json` and edit the list of segments.

```bash
python -m unittest tests.py -v
```

## Limitations

This is an estimate, not a lab measurement. Real calorie burn depends on things this model doesn't know about, like your fitness level, your exact stride, and how efficiently your body moves. The ACSM formulas also have a gap between "fast walk" and "slow jog" where neither equation was really validated, and I just picked 5 mph as the cutoff point rather than trying to model that transition precisely. Treat the numbers as a reasonable ballpark, the same way you should treat the numbers on the gym treadmill itself.
