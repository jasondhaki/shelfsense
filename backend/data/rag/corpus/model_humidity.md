---
source: ShelfSense model (assumed)
title: How humidity speeds spoilage in the simulation
url: docs/SIMULATION_ENGINE.md
sku_ids: []
---
ShelfSense models ambient stress as an environment factor beta_env = 1 + 0.5 × clamp((RH − 50) / 50, 0, 1), so relative humidity above 50 % ages exposed products up to 1.5× faster. Each product's weather_exposure (0–1) scales how much of that stress reaches it: berries, bananas, avocados and tomatoes are fully exposed; spinach 0.8, bread 0.6, chilled salmon and milk 0.2.

During a heavy rainstorm humidity jumps toward 98 % for 12 hours, then eases back over 6 hours. This is a modelling assumption for the demo, not a measured coefficient.
