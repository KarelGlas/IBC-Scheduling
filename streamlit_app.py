import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# config
days_ahead = 15
shift_order = [
    "Morning (06–14)",
    "Day (08–16, wkdays)",
    "Afternoon (14–22)",
    "Night (22–06)"
]

# 1. UI inputs
st.title("IBC Filling Scheduler")
scenario = st.radio(
    "Scenario:",
    ["How fast to fill X IBCs?", "How many IBCs in X days?"]
)
if scenario == "How fast to fill X IBCs?":
    target = st.number_input("Enter IBC target:", min_value=16, step=1)
else:
    num_days = st.number_input("Enter number of days:", min_value=1, max_value=days_ahead, step=1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Schedule Start Date", datetime.today())
with col2:
    start_shift = st.selectbox(
        "Start filling at:",
        shift_order
    )

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

# adjust first‐day cap based on start_shift
idx0 = shift_order.index(start_shift)
allowed = shift_order[idx0:]
d0 = df.loc[0, "Date"]
cap0 = sum(
    shift_caps[s]
    for s in allowed
    if not (s == "Day (08–16, wkdays)" and d0.weekday() >= 5)
)
df.at[0, "Capacity"] = cap0
cap_key = "cap_0"
if cap_key in st.session_state:
    st.session_state[cap_key] = cap0

# 3. Editable per-day capacity
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
    if key not in st.session_state:
        st.session_state[key] = int(row["Capacity"])
    with cols[idx % 5]:
        st.markdown(f"**{row['Date'].strftime('%A, %m-%d')}**")
        st.number_input("", min_value=0, step=1, key=key)
        b0, b1, b2 = st.columns(3)
        with b0:
            st.button("0", key=f"zero_{idx}", on_click=zero_callback, args=(idx,))
        with b1:
            st.button("+5", key=f"plus5_{idx}", on_click=plus5_callback, args=(idx,))
        with b2:
            st.button("-5", key=f"minus5_{idx}", on_click=minus5_callback, args=(idx,))
    edited.append(st.session_state[key])

df["Capacity"] = edited

# 3b. Compute finish shift
finish = None
if scenario == "How fast to fill X IBCs?":
    remaining = target
    for i, row in df.iterrows():
        d = row["Date"]
        shifts = allowed if i == 0 else shift_order
        for s in shifts:
            if s == "Day (08–16, wkdays)" and d.weekday() >= 5:
                continue
            cap_s = shift_caps[s]
            if remaining <= cap_s:
                finish = (d, s)
                break
            remaining -= cap_s
        if finish:
            break

# 4. Results
st.subheader("Results")
if scenario == "How fast to fill X IBCs?":
    cum = df["Capacity"].cumsum()
    days_needed = cum[cum >= target].index.min() + 1 if any(cum >= target) else f"Not achievable in {days_ahead} days"
    if finish:
        st.markdown(f"**Finish in:** {finish[1]} on {finish[0].strftime('%A, %Y-%m-%d')}")
else:
    total = df.head(num_days)["Capacity"].sum()
    st.markdown(f"**Total IBCs in {num_days} days:** {total}")

# 5. Chart
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
