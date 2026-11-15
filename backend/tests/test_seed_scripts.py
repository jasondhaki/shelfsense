"""Seed pipeline: committed seed files validate; parsers work on small synthetic inputs."""

import datetime as dt

import pytest

from scripts import build_seed_all, build_seed_foodkeeper, snapshot_noaa
from scripts._common import SEED, read_json


def test_committed_seed_files_validate():
    build_seed_all.validate(read_json(SEED / "skus.json")["skus"])


def test_foodkeeper_flatten_record_and_hours():
    doc = {
        "sheets": [
            {
                "name": "Product",
                "data": [
                    [
                        {"ID": 481.0},
                        {"Name": "Strawberries"},
                        {"Name_subtitle": None},
                        {"DOP_Refrigerate_Min": 2.0},
                        {"DOP_Refrigerate_Max": 3.0},
                        {"DOP_Refrigerate_Metric": "Days"},
                    ],
                    [{"ID": 27.0}, {"Name": "Milk"}, {"Refrigerate_Metric": "Package use-by date"}],
                ],
            }
        ]
    }
    rows = build_seed_foodkeeper._rows(doc)
    r = build_seed_foodkeeper.record(rows, 481, "DOP_Refrigerate")
    assert r["sl_nominal_hours"] == 48 and r["from_purchase"]
    milk = build_seed_foodkeeper.record(rows, 27, None)
    assert milk["sl_nominal_hours"] is None and milk["metric"] == "Package use-by date"
    assert build_seed_foodkeeper._to_hours(1, "Weeks") == 168


def test_noaa_summary_counts_only_rainy_hours():
    periods = [
        {
            "startTime": "2026-01-01T10:00:00-05:00",
            "shortForecast": "Sunny",
            "probabilityOfPrecipitation": {"value": 60},
            "relativeHumidity": {"value": 50},
        },
        {
            "startTime": "2026-01-02T10:00:00-05:00",
            "shortForecast": "Rain Showers Likely",
            "probabilityOfPrecipitation": {"value": 70},
            "relativeHumidity": {"value": 90},
        },
    ]
    s = snapshot_noaa.summarise(periods)
    assert s["p_heavy_rain_by_day"][:2] == [0.0, 0.7]
    assert len(s["p_heavy_rain_by_day"]) == 7 and s["relative_humidity_pct"] == 70


def test_favorita_aggregates(tmp_path, monkeypatch):
    pytest.importorskip("pandas")
    from scripts import build_seed_favorita as fav

    (tmp_path / "items.csv").write_text(
        "item_nbr,family,class,perishable\n1,PRODUCE,1,1\n3,GROCERY I,3,0\n"
    )
    lines = ["id,date,store_nbr,item_nbr,unit_sales,onpromotion"]
    for d in range(28):
        day = dt.date(2017, 1, 2) + dt.timedelta(d)  # a Monday
        for item in (1, 3):
            for s in (1, 2):
                u = 10 * (1.5 if day.weekday() >= 5 else 1.0) * (2 if s == 2 else 1)
                lines.append(f"{len(lines)},{day},{s},{item},{u},{s == 2}")
    (tmp_path / "train.csv").write_text("\n".join(lines) + "\n")
    (tmp_path / "sales_profile.json").write_text((SEED / "sales_profile.json").read_text())
    monkeypatch.setattr(fav, "DIR", tmp_path)
    monkeypatch.setattr(fav, "SEED", tmp_path)
    out = fav.build(chunksize=50)
    w = out["PRODUCE"]["dow_weight"]
    assert w[5] / w[0] == pytest.approx(1.5) and sum(w) / 7 == pytest.approx(1)
    assert out["PRODUCE"]["promo_lift"] == pytest.approx(2.0)
    assert "GROCERY I" not in out
    assert read_json(tmp_path / "sales_profile.json")["dow_weight"]["berries"] == w
