import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

st.title("IBC Filling Scheduler")

# 1. Inputs
start_date = st.date_input("Schedule Start Date", datetime.today())
days_ahead = 14
end_date = start_date + timedelta(days=days_ahead)

st.subheader("Shift Capacity Configuration")
shift_defaults = {
    'Morning (06–14)': 3,
    'Afternoon (14–22)': 3,
    'Night (22–06)': 3,
    'Day (08–16, wkdays)': 5
}
shift_caps = {
    s: st.number_input(s, value=v, min_value=0, step=1)
    for s, v in shift_defaults.items()
}

scenario = st.radio(
    "Scenario:",
    ["How fast to fill X IBCs?", "How many IBCs in X days?"]
)

# 2. Generate base schedule
def gen_schedule(start, days, caps):
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        cap = caps['Morning (06–14)'] + caps['Afternoon (14–22)'] + caps['Night (22–06)']
        if d.weekday() < 5:
            cap += caps['Day (08–16, wkdays)']
        rows.append({"Date": d, "Capacity": cap})
    return pd.DataFrame(rows)

df = gen_schedule(start_date, days_ahead, shift_caps)

# 3. Editable per-day capacity – compact layout
st.subheader("Adjust Daily Capacity")
edited = []
cols = st.columns(7)  # Spread across 7 columns per row

for idx, row in df.iterrows():
    with cols[idx % 7]:
        st.markdown(f"**{row['Date'].strftime('%m-%d')}**")
        val = st.number_input(
            label="",
            min_value=0,
            value=int(row["Capacity"]),
            key=f"cap_{idx}",
            step=1
        )
        if st.button("Zero", key=f"zero_{idx}"):
            val = 0
        edited.append(val)
df["Capacity"] = edited

# 4. Scenario outputs
st.subheader("Results")
if scenario == "How fast to fill X IBCs?":
    target = st.number_input("Enter IBC target:", min_value=1, step=1)
    cum = df['Capacity'].cumsum()
    days_needed = cum[cum >= target].index.min() + 1 if any(cum >= target) else " Not achievable in 14 days"
    st.markdown(f"**Days needed:** {days_needed}")
else:
    num_days = st.number_input("Enter number of days:", min_value=1, max_value=days_ahead, step=1)
    total = df.head(num_days)['Capacity'].sum()
    st.markdown(f"**Total IBCs in {num_days} days:** {total}")

# 5. Vertical bar chart with tight bars
bar_chart = (
    alt.Chart(df)
    .mark_bar(size=30)  # Low gap width
    .encode(
        x=alt.X("Date:T", axis=alt.Axis(title=None, labelAngle=-45)),
        y=alt.Y("Capacity:Q", axis=alt.Axis(title="Capacity")),
        tooltip=["Date:T", "Capacity:Q"]
    )
    .properties(height=300)
)
st.altair_chart(bar_chart, use_container_width=True)
