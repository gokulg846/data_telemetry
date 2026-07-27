import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telemetry_pipeline.config import Settings  # noqa: E402

st.set_page_config(page_title="Factory Pulse", page_icon="⚙️", layout="wide")
st.title("Factory Pulse")
st.caption("Operational health from the latest industrial telemetry pipeline run")


@st.cache_data(ttl=30)
def query(sql: str) -> pd.DataFrame:
    with psycopg.connect(Settings().postgres_dsn) as connection:
        return pd.read_sql_query(sql, connection)


health = query("select * from analytics.mart_machine_health order by risk_score desc")
anomalies = query(
    "select * from analytics.mart_anomaly_events "
    "order by event_ts desc limit 200"
)
reliability = query(
    "select * from analytics.mart_line_reliability order by event_hour, line_id"
)
runs = query("select * from raw.pipeline_runs order by started_at desc limit 10")

critical_count = int((health["latest_status"] == "critical").sum())
warning_count = int((health["latest_status"] == "warning").sum())
latest_run = runs.iloc[0]["status"] if not runs.empty else "unknown"
latest_event = health["latest_event_ts"].max() if not health.empty else "n/a"

one, two, three, four = st.columns(4)
one.metric("Critical machines", critical_count)
two.metric("Warning machines", warning_count)
three.metric("Latest pipeline", latest_run)
four.metric("Latest event", str(latest_event)[:19])

st.subheader("Machine risk and degradation")
st.plotly_chart(
    px.bar(
        health,
        x="machine_id",
        y="risk_score",
        color="latest_status",
        hover_data=["vibration_change_10_events", "temperature_c", "line_id"],
        color_discrete_map={"healthy": "#2ca02c", "warning": "#ffbf00", "critical": "#d62728"},
    ),
    use_container_width=True,
)

left, right = st.columns(2)
with left:
    st.subheader("Hourly line reliability")
    st.plotly_chart(
        px.line(
            reliability,
            x="event_hour",
            y="healthy_event_pct",
            color="line_id",
            markers=True,
            range_y=[0, 100],
        ).add_hline(y=98, line_dash="dash", annotation_text="98% SLO"),
        use_container_width=True,
    )
with right:
    st.subheader("Recent anomaly mix")
    st.plotly_chart(
        px.histogram(anomalies, x="anomaly_type", color="status"),
        use_container_width=True,
    )

st.subheader("Operator triage queue")
st.dataframe(
    anomalies[
        ["event_ts", "machine_id", "line_id", "status", "anomaly_type",
         "temperature_c", "vibration_mm_s", "pressure_bar"]
    ],
    use_container_width=True,
    hide_index=True,
)

with st.expander("Pipeline run history"):
    st.dataframe(runs, use_container_width=True, hide_index=True)
