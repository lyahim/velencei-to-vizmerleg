import json
import math
import os
import re
import shutil
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

DB_PATH = "output/vizmerleg.db"
TRACKER_PATH = "import_tracker.md"
KNOWN_ISSUES_PATH = "docs/known-issues.md"
TEMPLATE_DIR = "site/templates"
ASSETS_DIR = "site/assets"
OUT_DIR = "output/site"

DATA_VERSION = datetime.now().strftime("%Y-%m-%d %H:%M")
GITHUB_URL = "https://github.com/lyahim/velencei-to-vizmerleg"

TABLES = [
    "documents", "stations", "station_metadata_history", "monthly_balance",
    "monthly_station_obs", "evaporation_inputs", "daily_obs",
    "daily_station_extremes", "expedition_flows", "annual_climate_summary",
    "historical_monthly", "release_events",
]

TRACKER_STATUSES = {"pending", "done", "verify", "skip", "error", "tbd"}
STATUS_PRIORITY = ["error", "verify", "pending", "tbd", "unknown", "skip", "done"]


def clean(v):
    """NaN/NaT -> None, numpy scalars -> plain python, rounds floats."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v):
            return None
        return round(v, 3)
    if hasattr(v, "item"):
        return clean(v.item())
    return v


def df_records(df):
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


# --- 1. Chart queries -------------------------------------------------

def _vizhaztartas_annual(conn):
    """Spliced annual water-balance series, 1971-2024. tómm throughout.

    1971-1995: historical_monthly vizhaztartas_* (annual, month=0).
    1996-2024: monthly_balance month=0, COALESCE(final, adj, raw).
    """
    hist = pd.read_sql_query(
        """
        SELECT year,
            MAX(CASE WHEN variable='vizhaztartas_csapadek' THEN value END) AS csapadek,
            MAX(CASE WHEN variable='vizhaztartas_vizgyujto' THEN value END) AS hozzafolyas,
            MAX(CASE WHEN variable='vizhaztartas_tarozo' THEN value END) AS tarozo,
            MAX(CASE WHEN variable='vizhaztartas_vizpotlas' THEN value END) AS vizpotlas,
            MAX(CASE WHEN variable='vizhaztartas_parologas' THEN value END) AS parologas,
            MAX(CASE WHEN variable='vizhaztartas_vizkivetel' THEN value END) AS vizkivetel,
            MAX(CASE WHEN variable='vizhaztartas_leeresztes' THEN value END) AS lefolyas,
            MAX(CASE WHEN variable='vizhaztartas_keszletvaltozas' THEN value END) AS keszletvaltozas
        FROM historical_monthly
        WHERE month = 0 AND year BETWEEN 1971 AND 1995
        GROUP BY year ORDER BY year
        """,
        conn,
    )
    modern = pd.read_sql_query(
        """
        SELECT year,
            COALESCE(csapadek, csapadek_adj, csapadek_raw) AS csapadek,
            COALESCE(hozzafolyas, hozzafolyas_adj, hozzafolyas_raw) AS hozzafolyas,
            COALESCE(hozzafolyas_tarozo, hozzafolyas_t_adj, hozzafolyas_t_raw) AS tarozo,
            COALESCE(kulso_vizpotlas, vizpotlas_adj, vizpotlas_raw) AS vizpotlas,
            COALESCE(parologas, parologas_adj, parologas_raw) AS parologas,
            COALESCE(vizkivetel, vizkivetel_adj, vizkivetel_raw) AS vizkivetel,
            COALESCE(lefolyas, lefolyas_adj, lefolyas_raw) AS lefolyas,
            COALESCE(keszletv_mert, keszletv_mert_adj, keszletv_mert_raw) AS keszletvaltozas
        FROM monthly_balance
        WHERE month = 0 AND year BETWEEN 1996 AND 2024
        ORDER BY year
        """,
        conn,
    )
    return pd.concat([hist, modern], ignore_index=True).sort_values("year").reset_index(drop=True)


def chart_1(conn):
    df = _vizhaztartas_annual(conn)
    years = df["year"].astype(int).tolist()
    return {
        "source": "historical_monthly vizhaztartas_* (1971-1995) + monthly_balance (1996-2024, COALESCE(final,adj,raw))",
        "panels": [{
            "key": "main",
            "type": "bar",
            "title": "Éves vízháztartás, 1971-2024",
            "y_label": "tómm",
            "labels": years,
            "datasets": [
                {"label": "Csapadék", "data": clean_list(df["csapadek"]), "group": "inflow"},
                {"label": "Vízgyűjtő hozzáfolyás", "data": clean_list(df["hozzafolyas"]), "group": "inflow"},
                {"label": "Tározói hozzáfolyás", "data": clean_list(df["tarozo"]), "group": "inflow"},
                {"label": "Külső vízpótlás", "data": clean_list(df["vizpotlas"]), "group": "inflow"},
                {"label": "Párolgás", "data": clean_list(-df["parologas"]), "group": "loss"},
                {"label": "Vízkivétel", "data": clean_list(-df["vizkivetel"]), "group": "loss"},
                {"label": "Leeresztés", "data": clean_list(-df["lefolyas"]), "group": "loss"},
                {"label": "Mért készletváltozás", "data": clean_list(df["keszletvaltozas"]), "type": "line", "group": "overlay"},
            ],
        }],
    }


def clean_list(series):
    return [clean(v) for v in series.tolist()]


def chart_2(conn):
    df = _vizhaztartas_annual(conn)
    years = df["year"].astype(int).tolist()
    roll_p = df["parologas"].rolling(10, min_periods=1).mean()
    roll_c = df["csapadek"].rolling(10, min_periods=1).mean()
    return {
        "source": "historical_monthly vizhaztartas_* (1971-1995) + monthly_balance (1996-2024, COALESCE(final,adj,raw))",
        "panels": [{
            "key": "main",
            "type": "line",
            "title": "Párolgás és csapadék, 1971-2024",
            "y_label": "tómm",
            "labels": years,
            "datasets": [
                {"label": "Párolgás", "data": clean_list(df["parologas"])},
                {"label": "Csapadék", "data": clean_list(df["csapadek"])},
                {"label": "Párolgás, 10 éves mozgóátlag", "data": clean_list(roll_p), "dashed": True},
                {"label": "Csapadék, 10 éves mozgóátlag", "data": clean_list(roll_c), "dashed": True},
            ],
        }],
    }


def _daily_obs_valid(conn, station_id):
    """daily_obs rows for a station, value IS NOT NULL, with impossible calendar
    days (Feb 30/31, Apr 31, Jun 31 padding-duplicate rows) dropped.
    See docs/known-issues.md `daily-obs-invalid-calendar-day`.
    """
    df = pd.read_sql_query(
        "SELECT year, month, day, value FROM daily_obs WHERE station_id = ? AND value IS NOT NULL ORDER BY year, month, day",
        conn, params=(station_id,),
    )
    dates = pd.to_datetime(df[["year", "month", "day"]], errors="coerce")
    df = df[dates.notna()].copy()
    df["date"] = dates[dates.notna()]
    return df


def chart_3(conn):
    df = _daily_obs_valid(conn, "agard_vizallas")
    epoch = df["date"].min()
    df["label"] = (df["date"] - epoch).dt.days
    baseline = df[df["year"].between(2002, 2011)]["value"]
    band_low = round(float(baseline.mean() - baseline.std()), 1)
    band_high = round(float(baseline.mean() + baseline.std()), 1)
    below = (
        df[df["value"] < band_low]
        .groupby("year").size().reindex(range(2002, 2025), fill_value=0)
    )
    return {
        "source": "daily_obs station_id='agard_vizallas' (value IS NOT NULL)",
        "panels": [
            {
                "key": "daily",
                "type": "line",
                "title": "Napi vízállás, Agárd, 2002-2024",
                "y_label": "cm",
                "labels": [int(v) for v in df["label"].tolist()],
                "label_epoch": epoch.strftime("%Y-%m-%d"),
                "datasets": [{"label": "Vízállás (cm)", "data": [int(v) if v == int(v) else clean(v) for v in df["value"].tolist()], "point_radius": 0}],
                "band": {"low": band_low, "high": band_high, "label": "2002-2011 átlag ± szórás"},
            },
            {
                "key": "below_band",
                "type": "bar",
                "title": f"Napok száma a {band_low} cm alatt, évente",
                "y_label": "nap",
                "labels": [int(y) for y in below.index.tolist()],
                "datasets": [{"label": "Napok száma", "data": [int(v) for v in below.tolist()]}],
            },
        ],
    }


def chart_4(conn):
    df = _vizhaztartas_annual(conn)
    years = df["year"].tolist()
    x = df["year"].astype(float)
    y = df["hozzafolyas"].astype(float)
    mask = y.notna()
    trend = None
    if mask.sum() >= 2:
        coeffs = list(map(float, np.polyfit(x[mask], y[mask], 1)))
        trend = [round(coeffs[0] * yr + coeffs[1], 1) for yr in x]

    trib = pd.read_sql_query(
        """
        SELECT year, station_id, AVG(value) AS avg_m3s
        FROM monthly_station_obs
        WHERE variable = 'kozepes_m3s' AND month = 0 AND value IS NOT NULL
          AND station_id IN ('csakvar_vizhozam','korakaspuszta_vizhozam','patka_vizhozam',
                              'zamoly_vizhozam','kapolnasnyekvizhozam','kisfalud_vizhozam')
        GROUP BY year, station_id
        ORDER BY year
        """,
        conn,
    )
    trib_years = sorted(trib["year"].unique().tolist())
    station_names = {
        "csakvar_vizhozam": "Csákvár", "korakaspuszta_vizhozam": "Kőrakáspuszta",
        "patka_vizhozam": "Pátka", "zamoly_vizhozam": "Zámoly",
        "kapolnasnyekvizhozam": "Kápolnásnyék", "kisfalud_vizhozam": "Kisfalud-puszta",
    }
    trib_datasets = []
    for sid, label in station_names.items():
        sub = trib[trib["station_id"] == sid].set_index("year")["avg_m3s"]
        trib_datasets.append({"label": label, "data": [clean(sub.get(y)) for y in trib_years]})

    return {
        "source": "historical_monthly/monthly_balance (annual) + monthly_station_obs kozepes_m3s (1994-2024, value IS NOT NULL)",
        "panels": [
            {
                "key": "annual",
                "type": "bar",
                "title": "Vízgyűjtő hozzáfolyás összeomlása, 1971-2024",
                "y_label": "tómm",
                "labels": [int(y) for y in years],
                "datasets": [
                    {"label": "Hozzáfolyás", "data": clean_list(df["hozzafolyas"])},
                    {"label": "Trend", "data": trend, "type": "line", "dashed": True},
                ],
            },
            {
                "key": "tributary",
                "type": "bar",
                "title": "Mellékvízfolyások bontása, 1994-2024",
                "y_label": "m3/s",
                "stacked": True,
                "labels": [int(y) for y in trib_years],
                "datasets": trib_datasets,
            },
        ],
    }


def chart_5(conn):
    hist_precip = pd.read_sql_query(
        """SELECT year, month, value FROM historical_monthly
           WHERE variable='csapadek_mm' AND station_id IS NULL AND year BETWEEN 1971 AND 2000""",
        conn,
    )
    recent_precip = pd.read_sql_query(
        """SELECT year, month, AVG(value) AS value FROM monthly_station_obs
           WHERE variable='csapadek_mm' AND month BETWEEN 1 AND 12 AND value IS NOT NULL
             AND station_id IN ('agard_csapadek','dinnyesi_csapadek','lovasbereny_csapadek','zamoly_csapadek')
           GROUP BY year, month""",
        conn,
    )
    precip = pd.concat([hist_precip, recent_precip], ignore_index=True)
    precip_panel = _anomaly_panel(
        "precip", precip,
        "Csapadék havi anomália (mm), kiválasztott csapadékmérő állomások átlaga vs. 1971-2000 normál", "mm")

    evap = pd.read_sql_query(
        """SELECT year, month, COALESCE(parologas, parologas_adj, parologas_raw) AS value
           FROM monthly_balance WHERE month BETWEEN 1 AND 12""",
        conn,
    )
    evap_panel = _anomaly_panel(
        "evap", evap, "Párolgás havi anomália (tómm) vs. 1994-2000 alapidőszak", "tómm",
        baseline_years=(1994, 2000))

    level = pd.concat([
        pd.read_sql_query(
            """SELECT year, month, value FROM historical_monthly
               WHERE variable='vizallas_cm' AND station_id IS NULL AND year BETWEEN 1971 AND 2000""",
            conn,
        ),
        pd.read_sql_query(
            """SELECT year, month, value FROM monthly_station_obs
               WHERE variable='atlag_cm' AND station_id IS NULL AND month BETWEEN 1 AND 12 AND value IS NOT NULL""",
            conn,
        ),
    ], ignore_index=True)
    level_panel = _anomaly_panel("level", level, "Vízállás havi anomália (cm) vs. 1971-2000 normál", "cm")

    return {
        "source": "historical_monthly + monthly_station_obs (csapadek_mm/atlag_cm) + monthly_balance (parologas, COALESCE)",
        "panels": [precip_panel, evap_panel, level_panel],
    }


def _anomaly_panel(key, df, title, unit, baseline_years=(1971, 2000)):
    df = df.dropna(subset=["value"])
    baseline = df[df["year"].between(*baseline_years)]
    normals = baseline.groupby("month")["value"].mean()
    years = sorted(df["year"].unique().tolist())
    months = list(range(1, 13))
    matrix = []
    for yr in years:
        row = []
        for m in months:
            v = df[(df["year"] == yr) & (df["month"] == m)]["value"]
            if v.empty or m not in normals.index:
                row.append(None)
            else:
                row.append(clean(float(v.iloc[0]) - float(normals[m])))
        matrix.append(row)
    return {
        "key": key, "type": "heatmap", "title": title, "y_label": unit,
        "years": [int(y) for y in years], "months": months, "matrix": matrix,
        "baseline_years": list(baseline_years),
    }


def chart_6(conn):
    hist = pd.read_sql_query(
        """SELECT year, month, value FROM historical_monthly
           WHERE variable='leghom_celsius' AND station_id IS NULL AND year BETWEEN 1930 AND 1995""",
        conn,
    )
    recent = pd.read_sql_query(
        """SELECT year, month, value FROM monthly_station_obs
           WHERE variable='leghomerseklet' AND station_id IS NULL AND month BETWEEN 1 AND 12
             AND value IS NOT NULL AND year >= 1996""",
        conn,
    )
    df = pd.concat([hist, recent], ignore_index=True)
    annual = df.groupby("year")["value"].mean().reset_index().sort_values("year")
    overall_mean = annual["value"].mean()
    years = annual["year"].astype(int).tolist()
    anomalies = (annual["value"] - overall_mean).tolist()
    return {
        "source": "historical_monthly leghom_celsius (1930-1995) + monthly_station_obs leghomerseklet (1996-2024)",
        "panels": [{
            "key": "main",
            "type": "warming_stripes",
            "title": "Éves középhőmérséklet és melegedési csíkok, 1930-2024",
            "y_label": "°C",
            "labels": years,
            "overall_mean": clean(overall_mean),
            "datasets": [
                {"label": "Éves középhőmérséklet", "data": [clean(v) for v in annual["value"].tolist()], "type": "line"},
                {"label": "Eltérés az átlagtól", "data": [clean(v) for v in anomalies], "type": "stripes"},
            ],
        }],
    }


def chart_7(conn):
    hist = pd.read_sql_query(
        """SELECT year, AVG(value) AS value FROM historical_monthly
           WHERE variable='vizhom_celsius' AND station_id IS NULL AND month BETWEEN 1 AND 12
             AND year BETWEEN 1951 AND 1996 GROUP BY year""",
        conn,
    )
    mso = pd.read_sql_query(
        """SELECT year, AVG(value) AS value FROM monthly_station_obs
           WHERE variable='vizhom_celsius' AND station_id IS NULL AND month BETWEEN 1 AND 12
             AND value IS NOT NULL GROUP BY year""",
        conn,
    )
    daily_df = _daily_obs_valid(conn, "agard_vizhomerseklet")
    daily = daily_df.groupby("year")["value"].mean().reset_index()
    temp = {}
    for _, r in hist.iterrows():
        temp[int(r.year)] = r.value
    for _, r in mso.iterrows():
        temp[int(r.year)] = r.value
    for _, r in daily.iterrows():
        temp[int(r.year)] = r.value
    years_t = sorted(temp.keys())

    heat_days = daily_df[daily_df["value"] > 25].groupby("year").size()

    ice = pd.read_sql_query(
        "SELECT year, ice_total_days, ice_max_thickness_cm FROM annual_climate_summary ORDER BY year",
        conn,
    )

    return {
        "source": "historical_monthly vizhom_celsius + monthly_station_obs vizhom_celsius + daily_obs agard_vizhomerseklet + annual_climate_summary",
        "panels": [
            {
                "key": "water_temp",
                "type": "line",
                "title": "Vízhőmérséklet és 25°C feletti napok, 1951-2024",
                "y_label": "°C",
                "labels": [int(y) for y in years_t],
                "datasets": [
                    {"label": "Éves átlag vízhőmérséklet", "data": [clean(temp[y]) for y in years_t]},
                    {"label": "25°C feletti napok (Agárd, 2002-)", "data": [int(heat_days.get(y, 0)) if y in heat_days.index else None for y in years_t], "y_axis": "secondary"},
                ],
            },
            {
                "key": "ice",
                "type": "bar",
                "title": "Jégnapok és maximális jégvastagság, 1994-2024",
                "y_label": "nap / cm",
                "labels": [int(y) for y in ice["year"].tolist()],
                "datasets": [
                    {"label": "Jeges napok száma", "data": clean_list(ice["ice_total_days"])},
                    {"label": "Max. jégvastagság (cm)", "data": clean_list(ice["ice_max_thickness_cm"]), "type": "line", "y_axis": "secondary"},
                ],
            },
        ],
    }


def chart_8(conn):
    df = _vizhaztartas_annual(conn)
    years = df["year"].astype(int).tolist()
    return {
        "source": "historical_monthly vizhaztartas_* (1971-1995) + monthly_balance (1996-2024, COALESCE(final,adj,raw))",
        "panels": [{
            "key": "main",
            "type": "bar",
            "title": "„A tó már nem folyik túl” - leeresztés és vízkivétel, 1971-2024",
            "y_label": "tómm",
            "labels": years,
            "datasets": [
                {"label": "Leeresztés", "data": clean_list(df["lefolyas"])},
                {"label": "Vízkivétel", "data": clean_list(df["vizkivetel"])},
            ],
        }],
    }


def chart_9(conn):
    df = pd.read_sql_query(
        "SELECT year, station_name, is_dry FROM expedition_flows WHERE station_name != 'ismeretlen'",
        conn,
    )
    overall = df.groupby("year")["is_dry"].agg(["sum", "count"]).reset_index()
    overall["share"] = (overall["sum"] / overall["count"] * 100).round(1)
    per_stream = df.groupby(["station_name", "year"])["is_dry"].agg(["sum", "count"]).reset_index()
    per_stream["share"] = (per_stream["sum"] / per_stream["count"] * 100).round(1)
    years = sorted(overall["year"].unique().tolist())
    streams = sorted(df["station_name"].unique().tolist())
    stream_datasets = []
    for s in streams:
        sub = per_stream[per_stream["station_name"] == s].set_index("year")["share"]
        stream_datasets.append({"label": s, "data": [clean(sub.get(y)) for y in years]})
    return {
        "source": "expedition_flows.is_dry, mérési pontonként",
        "panels": [{
            "key": "main",
            "type": "line",
            "title": "Mellékvízfolyások kiszáradása, 2010-2024",
            "y_label": "% száraz mérési pont",
            "labels": [int(y) for y in years],
            "datasets": [{"label": "Összesen", "data": clean_list(overall["share"]), "highlight": True}] + stream_datasets,
        }],
    }


def chart_10(conn):
    lake = pd.read_sql_query(
        """SELECT year, SUM(release_volume_tomm) AS tomm FROM release_events
           WHERE station_id='agard_vizallas' AND release_volume_tomm IS NOT NULL
           GROUP BY year ORDER BY year""",
        conn,
    )
    per_res = pd.read_sql_query(
        """SELECT year, station_id, SUM(release_volume_1e6m3) AS m3 FROM release_events
           WHERE station_id IN ('patkai_tarozo_vizallas','zamolyi_tarozo_vizallas')
             AND release_volume_1e6m3 IS NOT NULL
           GROUP BY year, station_id ORDER BY year""",
        conn,
    )
    res_years = sorted(per_res["year"].unique().tolist())
    names = {"patkai_tarozo_vizallas": "Pátkai-tározó", "zamolyi_tarozo_vizallas": "Zámolyi-tározó"}
    res_datasets = []
    for sid, label in names.items():
        sub = per_res[per_res["station_id"] == sid].set_index("year")["m3"]
        res_datasets.append({"label": label, "data": [clean(sub.get(y)) for y in res_years]})
    return {
        "source": "release_events (agard_vizallas: tómm a tóhoz érkezett vízről; patkai/zamolyi tározó: 1e6 m3 saját leeresztés)",
        "panels": [
            {
                "key": "lake",
                "type": "bar",
                "title": "A tóhoz érkezett tározói vízpótlás, 1993-2025",
                "y_label": "tómm",
                "labels": [int(y) for y in lake["year"].tolist()],
                "datasets": [{"label": "Tározói vízpótlás", "data": clean_list(lake["tomm"])}],
            },
            {
                "key": "reservoirs",
                "type": "bar",
                "title": "Tározónkénti leeresztés, 1993-2025",
                "y_label": "millió m3",
                "stacked": True,
                "labels": [int(y) for y in res_years],
                "datasets": res_datasets,
            },
        ],
    }


def chart_11(conn):
    df = pd.read_sql_query(
        """SELECT year,
               AVG(t_celsius) AS t_celsius, AVG(u_ms) AS u_ms, AVG(e_act_mb) AS e_act_mb,
               SUM(P_mm) AS p_mm
           FROM evaporation_inputs GROUP BY year ORDER BY year""",
        conn,
    )
    years = df["year"].astype(int).tolist()
    return {
        "source": "evaporation_inputs, éves bontásban (t_celsius/u_ms/e_act_mb átlag, P_mm összeg)",
        "panels": [{
            "key": "main",
            "type": "line",
            "title": "Párolgás hajtóerő-bontása",
            "y_label": "vegyes egység, index",
            "labels": years,
            "datasets": [
                {"label": "Hőmérséklet (°C)", "data": clean_list(df["t_celsius"])},
                {"label": "Szélsebesség (m/s)", "data": clean_list(df["u_ms"])},
                {"label": "Tényleges gőznyomás (mb)", "data": clean_list(df["e_act_mb"])},
                {"label": "Számított párolgás (mm)", "data": clean_list(df["p_mm"]), "y_axis": "secondary", "highlight": True},
            ],
        }],
    }


def chart_12(conn):
    df = _vizhaztartas_annual(conn)
    years = df["year"].astype(int).tolist()
    cum = df["keszletvaltozas"].fillna(0).cumsum()
    return {
        "source": "historical_monthly vizhaztartas_keszletvaltozas + monthly_balance keszletv_mert (COALESCE), kumulált összeg",
        "panels": [{
            "key": "main",
            "type": "line",
            "title": "Kumulált készlethiány, 1971 óta",
            "y_label": "tómm, kumulált",
            "labels": years,
            "datasets": [{"label": "Kumulált készletváltozás", "data": clean_list(cum), "fill": True}],
        }],
    }


CHART_FUNCS = {
    "vizhaztartas": chart_1,
    "parolgas_csapadek": chart_2,
    "napi_vizallas": chart_3,
    "hozzafolyas_osszeomlas": chart_4,
    "havi_anomalia": chart_5,
    "melegedesi_csikok": chart_6,
    "homerseklet_jeg": chart_7,
    "nincs_tulfolyas": chart_8,
    "kiszaradas": chart_9,
    "tarozoi_fuggoseg": chart_10,
    "parolgas_hajtoero": chart_11,
    "kumulalt_hiany": chart_12,
}

# known-issues.md's `charts` column carries docs/climate-charts-plan.md's plain numbering (1-12),
# independent of the descriptive chart ids used for data-chart / data/charts/<id>.json.
CHART_PLAN_NUMBER = {
    "vizhaztartas": "1", "parolgas_csapadek": "2", "napi_vizallas": "3",
    "hozzafolyas_osszeomlas": "4", "havi_anomalia": "5", "melegedesi_csikok": "6",
    "homerseklet_jeg": "7", "nincs_tulfolyas": "8", "kiszaradas": "9",
    "tarozoi_fuggoseg": "10", "parolgas_hajtoero": "11", "kumulalt_hiany": "12",
}


# --- 2. Table export ----------------------------------------------------

def export_tables(conn, data_dir):
    tables_dir = os.path.join(data_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)
    for table in TABLES:
        query = f"SELECT * FROM {table}"
        if table == "daily_obs":
            query += " WHERE value IS NOT NULL"
        df = pd.read_sql_query(query, conn)
        payload = {"data_version": DATA_VERSION, "table": table, "rows": df_records(df)}
        with open(os.path.join(tables_dir, f"{table}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)


# --- 3. import_tracker.md parsing ---------------------------------------

def normalize_table_name(cell):
    name = cell.split("(")[0].strip()
    if name in ("", "—", "various", "tbd"):
        return "unknown"
    return name


def parse_tracker(path):
    """Returns list of dicts: {year, table, status, raw}. Defensive: unparseable rows -> table='unknown', status='unknown'.

    Only rows inside a `## YYYY ...` section, under the canonical
    `step | description | db_table | status | rows_in_db | notes` header, are parsed as tracker
    steps. Other sections (era reference, progress summary) use differently-shaped tables and are
    skipped entirely, not misread as step rows.
    """
    rows = []
    year = None
    in_step_table = False
    year_re = re.compile(r"^##\s+(\d{4})\b")
    heading_re = re.compile(r"^#{1,6}\s")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = year_re.match(line)
            if m:
                year = int(m.group(1))
                in_step_table = False
                continue
            if heading_re.match(line):
                year = None
                in_step_table = False
                continue
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if cells[0].lower() == "step" and len(cells) >= 5 and cells[2].lower() == "db_table":
                in_step_table = True
                continue
            if year is None or not in_step_table:
                continue
            try:
                if len(cells) >= 5:
                    step, description, db_table, status, rows_in_db = cells[0], cells[1], cells[2], cells[3], cells[4]
                    table = normalize_table_name(db_table)
                    status = status.lower().strip()
                    if status not in TRACKER_STATUSES:
                        status = "unknown"
                    rows.append({"year": year, "table": table, "status": status, "raw": line})
                else:
                    raise ValueError("too few cells")
            except Exception:
                rows.append({"year": year, "table": "unknown", "status": "unknown", "raw": line})
    return rows


def build_coverage(conn, tracker_rows):
    tables_tracked = sorted({r["table"] for r in tracker_rows if r["table"] != "unknown"})
    years = sorted({r["year"] for r in tracker_rows if r["year"] is not None})

    by_table_year = {}
    for r in tracker_rows:
        if r["year"] is None or r["table"] == "unknown":
            continue
        key = (r["table"], r["year"])
        by_table_year.setdefault(key, []).append(r["status"])

    db_counts = {}
    for table in tables_tracked:
        try:
            df = pd.read_sql_query(f"SELECT year, COUNT(*) AS n FROM {table} GROUP BY year", conn)
            db_counts[table] = dict(zip(df["year"], df["n"]))
        except Exception:
            db_counts[table] = {}

    matrix = {}
    for table in tables_tracked:
        matrix[table] = {}
        for year in years:
            statuses = by_table_year.get((table, year))
            priority_status = None
            if statuses:
                for p in STATUS_PRIORITY:
                    if p in statuses:
                        priority_status = p
                        break
            count = int(db_counts.get(table, {}).get(year, 0) or 0)
            if priority_status in ("error", "verify"):
                cell_status = "unconfirmed"
            elif count > 0:
                cell_status = "present"
            elif priority_status in ("pending", "tbd"):
                cell_status = "pending"
            elif priority_status == "skip":
                cell_status = "skip"
            elif priority_status == "unknown":
                cell_status = "unknown"
            elif priority_status is None:
                cell_status = "absent"
            else:
                cell_status = "unknown"
            matrix[table][str(year)] = {"status": cell_status, "rows_in_db": count}

    return {
        "data_version": DATA_VERSION,
        "years": years,
        "tables": tables_tracked,
        "matrix": matrix,
    }


# --- 4. known-issues.md parsing ------------------------------------------

def parse_known_issues(path):
    """Returns dict: chart_id (str) -> list of {id, severity, display_hu, ref}."""
    by_chart = {}
    in_table = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("| id "):
                in_table = True
                continue
            if not in_table:
                continue
            if not line.startswith("|"):
                if line == "" :
                    continue
                in_table = False
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 8:
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            row_id, scope, years, severity, charts, issue, display_hu, ref = cells[:8]
            row_id = row_id.strip("`")
            if display_hu == "—" or display_hu == "":
                continue
            chart_ids = [c.strip() for c in charts.split(",") if c.strip() and c.strip() != "all"]
            for cid in chart_ids:
                by_chart.setdefault(cid, []).append({
                    "id": row_id, "severity": severity, "display_hu": display_hu, "ref": ref,
                })
    return by_chart


# --- 5. HTML templates ---------------------------------------------------

NAV_ITEMS = [
    ("index.html", "Áttekintés"),
    ("klima.html", "Klíma"),
    ("adattar.html", "Adattár"),
    ("forras.html", "Forrás"),
]


def render_nav(active):
    items = []
    for href, label in NAV_ITEMS:
        active_cls = " active" if href == active else ""
        aria = ' aria-current="page"' if href == active else ""
        items.append(
            f'<li class="nav-item"><a class="nav-link{active_cls}" href="{href}"{aria}>{label}</a></li>'
        )
    return f"""<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="index.html">Velencei-tó vízmérleg</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain"
      aria-controls="navMain" aria-expanded="false" aria-label="Navigáció váltása">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navMain">
      <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
        {''.join(items)}
      </ul>
    </div>
  </div>
</nav>"""


BANNER_HTML = """<div class="alert alert-warning banner-caveat mb-0 rounded-0 text-center" role="alert">
  Az adatok AI-alapú feldolgozással készültek, eltérhetnek a forrástól.
  <a href="forras.html" class="alert-link">Részletek &rarr;</a>
</div>"""


def render_footer(last_processed_year):
    return f"""<footer class="text-center text-muted small py-4 mt-5 border-top">
  Adatállapot: {DATA_VERSION} &middot; adatok {last_processed_year}-ig &middot;
  <a href="forras.html">Forrás és módszertan</a> &middot;
  <a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>
</footer>"""


def render_pages(data_dir, last_processed_year):
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in ["index", "klima", "adattar", "forras"]:
        src = os.path.join(TEMPLATE_DIR, f"{name}.html")
        with open(src, encoding="utf-8") as f:
            html = f.read()
        html = html.replace("{{NAV}}", render_nav(f"{name}.html"))
        html = html.replace("{{BANNER}}", BANNER_HTML)
        html = html.replace("{{FOOTER}}", render_footer(last_processed_year))
        html = html.replace("{{DATA_VERSION}}", DATA_VERSION)
        html = html.replace("{{GENERATED_AT}}", DATA_VERSION)
        assert "{{" not in html, f"Unsubstituted placeholder left in {name}.html"
        assert_relative_paths(html, name)
        with open(os.path.join(OUT_DIR, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(html)


def assert_relative_paths(html, page_name):
    for m in re.finditer(r'''(?:src|href)=["'](/[^/][^"']*)["']''', html):
        raise AssertionError(f"Absolute root-relative path {m.group(1)!r} found in {page_name}.html")
    for m in re.finditer(r'''fetch\(\s*["'](/[^"']*)["']''', html):
        raise AssertionError(f"Absolute root-relative fetch path {m.group(1)!r} found in {page_name}.html")


def copy_assets():
    dst = os.path.join(OUT_DIR, "assets")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(ASSETS_DIR, dst)


# --- 6. Main ---------------------------------------------------------------

def main():
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    data_dir = os.path.join(OUT_DIR, "data")
    charts_dir = os.path.join(data_dir, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    known_issues = parse_known_issues(KNOWN_ISSUES_PATH)

    for chart_id, fn in CHART_FUNCS.items():
        payload = fn(conn)
        payload["chart_id"] = chart_id
        payload["data_version"] = DATA_VERSION
        payload["notes"] = known_issues.get(CHART_PLAN_NUMBER[chart_id], [])
        with open(os.path.join(charts_dir, f"{chart_id}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    export_tables(conn, data_dir)

    tracker_rows = parse_tracker(TRACKER_PATH)
    coverage = build_coverage(conn, tracker_rows)
    with open(os.path.join(data_dir, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False)

    last_processed_year = conn.execute("SELECT MAX(year) FROM documents").fetchone()[0]

    conn.close()

    render_pages(data_dir, last_processed_year)
    copy_assets()

    with open(os.path.join(OUT_DIR, ".nojekyll"), "w") as f:
        pass

    print(f"Site written -> {OUT_DIR} (DATA_VERSION={DATA_VERSION})")


if __name__ == "__main__":
    main()
