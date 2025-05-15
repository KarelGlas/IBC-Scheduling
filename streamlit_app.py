import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

st.title("IBC Filling Scheduler")

# 1. Inputs
start_date = st.date_input("Schedule Start Date", datetime.today())
days_ahead = 15
end_date = start_date + timedelta(days=days_ahead)

st.subheader("Shift Capacity Configuration")
col1, col2 = st.columns(2)
with col1:
    master = st.number_input("All Shifts (06–22)", value=3, min_value=0, step=1)
with col2:
    daycap = st.number_input("Day (08–16, wkdays)", value=5, min_value=0, step=1)

shift_caps = {
    "Morning (06–14)": master,
    "Afternoon (14–22)": master,
    "Night (22–06)": master,
    "Day (08–16, wkdays)": daycap
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
        cap = caps["Morning (06–14)"] + caps["Afternoon (14–22)"] + caps["Night (22–06)"]
        if d.weekday() < 5:
            cap += caps["Day (08–16, wkdays)"]
        rows.append({"Date": d, "Capacity": cap})
    return pd.DataFrame(rows)

df = gen_schedule(start_date, days_ahead, shift_caps)

if scenario == "How fast to fill X IBCs?":
    target = st.number_input("Enter IBC target:", min_value=16, step=1)
else:
    num_days = st.number_input("Enter number of days:", min_value=1, max_value=days_ahead, step=1)

# 3. Editable per-day capacity – compact layout
st.subheader("Adjust Daily Capacity")
edited = []
cols = st.columns(5)

st.markdown("""
  <style>
    div.stButton > button {
      font-size: 0.8rem !important;
      width: 7ch !important;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  </style>
""", unsafe_allow_html=True)

def zero_callback(idx):
    st.session_state[f"cap_{idx}"] = 0

def plus5_callback(idx):
    st.session_state[f"cap_{idx}"] += 5

def minus5_callback(idx):
    st.session_state[f"cap_{idx}"] = max(0, st.session_state[f"cap_{idx}"] - 5)

for idx, row in df.iterrows():
    key = f"cap_{idx}"
    zero_key = f"zero_{idx}"
    plus5_key = f"plus5_{idx}"
    minus5_key = f"minus5_{idx}"
    if key not in st.session_state:
        st.session_state[key] = int(row["Capacity"])
    with cols[idx % 5]:
        st.markdown(f"**{row['Date'].strftime('%m-%d')}**")
        st.number_input("", min_value=0, step=1, key=key)
        btn0, btn_plus5, btn_minus5 = st.columns(3)
        with btn0:
            st.button("0", key=zero_key, on_click=zero_callback, args=(idx,))
        with btn_plus5:
            st.button("+5", key=plus5_key, on_click=plus5_callback, args=(idx,))
        with btn_minus5:
            st.button("-5", key=minus5_key, on_click=minus5_callback, args=(idx,))
    edited.append(st.session_state[key])

df["Capacity"] = edited

# 4. Scenario outputs
st.subheader("Results")
if scenario == "How fast to fill X IBCs?":
    cum = df["Capacity"].cumsum()
    days_needed = cum[cum >= target].index.min() + 1 if any(cum >= target) else f"Not achievable in {days_ahead} days"
    st.markdown(f"**Days needed:** {days_needed}")
else:
    total = df.head(num_days)["Capacity"].sum()
    st.markdown(f"**Total IBCs in {num_days} days:** {total}")

# 5. Vertical bar chart with tight bars
bar_chart = (
    alt.Chart(df)
    .mark_bar(size=30)
    .encode(
        x=alt.X("Date:T", axis=alt.Axis(title=None, labelAngle=-45)),
        y=alt.Y("Capacity:Q", axis=alt.Axis(title="Capacity")),
        tooltip=["Date:T", "Capacity:Q"]
    )
    .properties(height=300)
)
st.altair_chart(bar_chart, use_container_width=True)
