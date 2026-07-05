# Gym Locker Optimizer

Позвольте представить Gym Locker Optimizer — privacy-friendly алгоритм распределения шкафчиков для фитнес-клубов, тренажерных залов, бассейнов и раздевалок. Проект сделал Олег Ремизов, сайт: [remizov.com](https://remizov.com).

Моя идея простая, появилась так как лично сталкивался в двух фитнес-клубах в Москве. Когда посетитель приходит в клуб, система выбирает свободный шкафчик не случайно, а с учетом физической карты раздевалки, текущей занятости и вероятного времени ухода других посетителей. Цель — снизить ситуации, когда людям приходится переодеваться рядом друг с другом.

Алгоритм у меня использует только технические события посещения: check-in, check-out, дату/день недели, номер шкафчика и анонимный идентификатор при необходимости. Имена, телефоны, фото, документы и другие персональные данные не нужны.

Для каждого свободного шкафчика считается оценка:
- насколько далеко он находится от занятых шкафчиков
- есть ли риск пересечения во время переодевания после входа
- есть ли риск пересечения перед ожидаемым уходом
- как шкафчик расположен физически, а не только какой у него номер
- подходит ли он под предпочтения, например верхний/нижний ярус
В проекте есть Python-ядро, CLI, симулятор `random` vs `smart`, тесты и TypeScript-версия для прототипов интерфейса или интеграции в веб-сервис.

ENGLISH TEXT BELOW

---

My privacy-friendly locker assignment for gyms, fitness clubs, swimming pools, and changing rooms.
The project ranks available lockers by physical distance and predicted changing-room overlap. It is meant for clubs where members receive a locker key at check-in and the usual random assignment often puts two people next to each other while they are changing.

## Why this exists
Many gyms already know:
- when a member checks in
- when the same anonymous member checks out
- which lockers are currently occupied
- the physical locker layout

That is enough to make better locker choices without storing names, phone numbers, face data, or other personal details.
The optimizer estimates when current visitors are likely to return to their locker, then picks a free locker that is far away from likely activity. It also returns backup options, so a front desk system can regenerate or let staff choose another suitable key.

## Core idea

Each visit has two high-friction windows:
- arrival window: about 10 minutes after check-in
- departure window: about 15 minutes before predicted check-out
For each available locker, the algorithm scores:

- distance from occupied lockers
- predicted overlap with other visitors' arrival or departure windows
- locker layout geometry, not just locker numbers
- optional tier preference, for example adults may prefer upper lockers when lower lockers are mostly used by kids
- unavailable lockers, maintenance blocks, and reserved areas

The highest score is the recommended locker. The next scores are useful alternatives.

## Layout model

The default layout supports the common odd/even gym pattern:

- odd numbers are upper lockers
- even numbers are lower lockers
- `101` and `103` are adjacent upper lockers
- `101` and `102` are in the same vertical column

For a 530-locker club, that becomes 265 physical columns. You can split those columns into rows with `pairs_per_row`, for example `53` columns per row gives five rows.

## Quick start

Run the Python simulation:

```bash
python3 -m lockerfit simulate --lockers 530 --pairs-per-row 53 --days 7 --visitors-per-day 80
```

Recommend lockers from a small active-session file:

```bash
python3 -m lockerfit recommend --active-json examples/active_sessions.json --lockers 530 --pairs-per-row 53 --top 5
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Example output

```text
strategy   assigned  close_events  close_rate  avg_nearest
random     524       30            0.011       12.29
smart      524       0             0.000       17.59
```

The exact numbers depend on the seed, visitor volume, layout, and visit duration patterns.

For a larger benchmark:

```bash
python3 -m lockerfit simulate --lockers 530 --pairs-per-row 53 --days 21 --visitors-per-day 160
```

## Python API

```python
from datetime import datetime

from lockerfit import (
    AssignmentRequest,
    DurationPredictor,
    LockerAssigner,
    LockerLayout,
)

layout = LockerLayout.odd_even(number_of_lockers=530, pairs_per_row=53)
predictor = DurationPredictor(default_minutes=90)
assigner = LockerAssigner(layout=layout, predictor=predictor)

options = assigner.recommend(
    request=AssignmentRequest(arrived_at=datetime.fromisoformat("2026-07-03T18:05:00")),
    active_sessions=[],
    top_k=5,
)

print(options[0].locker_id)
```

## TypeScript

A dependency-free TypeScript port is included in `typescript/src`. It mirrors the main layout and ranking logic for web demos, kiosk prototypes, or Node services.

```bash
cd typescript
pnpm install
pnpm run build
```

## Data privacy

The optimizer does not require personal data. If a stable visitor identifier is useful for duration prediction, pass a salted hash or internal anonymous ID.

Recommended input:

- anonymous visitor key
- check-in timestamp
- check-out timestamp
- locker ID
- weekday/date

Avoid storing names, phone numbers, documents, photos, or raw access-card numbers in this layer.

## Project status

This is a practical MVP:

- deterministic Python core
- simulation comparing random vs optimized assignment
- simple CLI
- TypeScript implementation for product prototypes
- unit tests for layout, prediction, optimization, and simulation

Useful next steps:

- import real locker maps from CSV
- tune scoring weights with real club data
- add per-zone capacity rules
- model family/kids lockers separately
- publish a small dashboard for simulation results

Some rough implementation notes live in `docs/field-notes.md`.

## License

MIT
