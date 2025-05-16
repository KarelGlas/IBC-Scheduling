import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# — Restart helper
def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]

# — Callbacks
def zero_cb(i):   st.session_state[f"cap_{i}"] = 0
def plus5_cb(i):  st.session_state[f"cap_{i}"] += 5
def minus5_cb(i): st.session_state[f"cap_{i}"] = max(0, st.session_state[f"cap_{i}"] - 5)

# — Config
days_ahead = 15
shift_order = [
    "Morning (06–14)",
    "Day (08–16, wkdays)",
    "Afternoon (14–22)",
    "Night (22–06)"
]

# 1. Inputs
st.title("IBC Filling Scheduler")
scenario = st.radio("Scenario:", ["How fast to fill X IBCs?", "How many IBCs in X days?"])
if scenario.startswith("How fast"):
    target = st.number_input("Enter IBC target:", min_value=16, step=1)
else:
    num_days = st.number_input("Enter number of days:", min_value=1, max_value=days_ahead, step=1)

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Schedule Start Date", datetime.today())
with c2:
    start_shift = st.selectbox("Start filling at:", shift_order)

# 2. Shift capacities
st.subheader("Shift Capacity Configuration")
c1, c2 = st.columns(2)
with c1:
    master = st.number_input("All Shifts (06–22)", value=3, min_value=0, step=1)
with c2:
    daycap = st.number_input("Day (08–16, wkdays)", value=5, min_value=0, step=1)

shift_caps = {
    "Morning (06–14)": master,
    "Afternoon (14–22)": master,
    "Night (22–06)": master,
    "Day (08–16, wkdays)": daycap
}

# 3. Build schedule
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

# — adjust first-day cap
idx0 = shift_order.index(start_shift)
allowed = shift_order[idx0:]
d0 = df.loc[0, "Date"]
cap0 = sum(
    shift_caps[s]
    for s in allowed
    if not (s == "Day (08–16, wkdays)" and d0.weekday() >= 5)
)

# — init session_state
cfg = (master, daycap, start_shift, start_date)
if st.session_state.get("cfg") != cfg:
    for i, r in df.iterrows():
        st.session_state[f"cap_{i}"] = cap0 if i == 0 else int(r["Capacity"])
    st.session_state["cfg"] = cfg

# 4. Adjust Daily Capacity
st.subheader("Adjust Daily Capacity")
# global CSS for adjust buttons
st.markdown("""
<style>
div.stButton > button {
  font-size: 0.8rem !important;
  width: 7ch !important;
  padding: 0.25rem !important;
}
</style>
""", unsafe_allow_html=True)

edited = []
cols = st.columns(5)
for i, r in df.iterrows():
    with cols[i % 5]:
        st.markdown(f"**{r['Date'].strftime('%A, %m-%d')}**")
        st.number_input("", min_value=0, step=1, key=f"cap_{i}")
        b0, b1, b2 = st.columns(3)
        with b0:
            st.button("0",   key=f"z_{i}", on_click=zero_cb,   args=(i,))
        with b1:
            st.button("+5",  key=f"p_{i}", on_click=plus5_cb,  args=(i,))
        with b2:
            st.button("-5",  key=f"m_{i}", on_click=minus5_cb, args=(i,))
    edited.append(st.session_state[f"cap_{i}"])

df["Capacity"] = edited

# 5. Compute finish (scenario 1), using updated df
finish = None
if scenario.startswith("How fast"):
    rem = target
    # treat each day as a single “shift” with total capacity
    for _, r in df.iterrows():
        if rem <= r["Capacity"]:
            finish = r["Date"]
            break
        rem -= r["Capacity"]

# 6. Results
st.subheader("Results")
if scenario.startswith("How fast"):
    if finish:
        st.markdown(f"**Finish on:** {finish.strftime('%A, %Y-%m-%d')}")
else:
    total = df.head(num_days)["Capacity"].sum()
    st.markdown(f"**Total IBCs in {num_days} days:** {total}")

# 7. Chart
bar = (
    alt.Chart(df)
    .mark_bar(size=30)
    .encode(
        x=alt.X("Date:T", axis=alt.Axis(title=None, labelAngle=-45)),
        y=alt.Y("Capacity:Q", axis=alt.Axis(title="Capacity")),
        tooltip=["Date:T","Capacity:Q"]
    )
    .properties(height=300)
)
st.altair_chart(bar, use_container_width=True)

# 8. Reset button (scoped CSS)
st.button("🔄", on_click=reset_all)
