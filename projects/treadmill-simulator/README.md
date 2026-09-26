# Treadmill Simulator

A terminal program that estimates calorie burn, heart rate, and elevation gain for a single walk or run, using the same kind of formulas real gym equipment runs on.

## Why I built this

I use a treadmill at the gym a lot, and I started noticing that the calorie counter felt almost linear with speed and incline. That got me curious enough to look into the actual formulas behind treadmill calorie estimates and build my own version.

The first version of this played back a whole preset workout plan. I ended up wanting something simpler and more useful instead: enter your stats once, describe one walk or run you're about to do (or just did), and get an instant estimate back, the same way you'd glance at a treadmill console mid-workout.

## What it does

You enter your weight, height, age, and gender once. Then you describe the walk or run itself: speed, incline, and how long it lasts. The program instantly reports three things:

- an estimated calorie range
- an estimated heart rate range
- your elevation gain

## How the three outputs work

**Calories** come from two pieces added together: your personalized resting burn rate (from the Mifflin-St Jeor equation, using your weight, height, age, and gender) plus the extra burn from the exercise itself (from walking/running formulas published by the American College of Sports Medicine, the same body of research most treadmill software is quietly built on). The result is reported as a range, plus or minus 20 calories around the estimate, since real calorie burn depends on things like your exact stride and fitness level that this model can't know.

**Heart rate** is the roughest of the three estimates, and worth being upfront about. It only has your age to work with, so it estimates your max heart rate from age (the Tanaka formula), estimates your fitness level from that (a formula that guesses how much oxygen your body can use at full effort, without ever giving you a fitness test), and then figures out what percentage of your heart rate reserve the workout is likely demanding, based on how much oxygen it costs. It's a real, published chain of formulas, but it's inferring your cardiovascular response rather than measuring it, so treat the range (plus or minus 10 beats per minute) as a loose ballpark, more so than the calorie estimate.

**Elevation gain** isn't really an estimate at all, it's just geometry: a 5 percent incline means you climb 5 feet for every 100 feet you walk forward. Given your speed, incline, and duration, the distance and climb are both exact, so there's no range attached to this one.

## Incline note

Incline here is a percent grade, from 0 to 15, matching how real gym treadmills like Precor's display it. A 5 percent incline means for every 100 feet you walk forward, you also climb 5 feet up.

## Project structure

```
treadmill-simulator/
README.md
calories.py     <- the Mifflin-St Jeor and ACSM formulas behind the calorie estimate
heart_rate.py   <- the age/intensity based formulas behind the heart rate estimate
session.py      <- combines both into the three outputs for one walk/run session
cli.py          <- the interactive terminal program: asks for your stats and session, prints the results
tests.py        <- unit tests checking the formulas against hand-worked numbers
```

## Run it

```bash
pip install rich
python cli.py
```

```bash
python -m unittest tests.py -v
```

## Limitations

This is a set of estimates, not lab measurements. The calorie range is a reasonable ballpark; the heart rate range is a looser one, since it's inferred from age alone rather than anything measured about your actual fitness or cardiovascular response. The ACSM formulas behind the calorie math also have a gap between "fast walk" and "slow jog" where neither equation was really validated, and this program just picks 5 mph as the cutoff point rather than modeling that transition precisely. Treat all of it the way you'd treat the numbers on a gym treadmill console: a useful estimate, not a diagnosis.
