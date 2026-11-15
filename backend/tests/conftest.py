import os

# No test hits the network: NOAA off before app.config caches settings.
os.environ["NOAA_ENABLED"] = "false"
