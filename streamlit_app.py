import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="GTD Intel Dashboard", layout="wide")

@st.cache_data
def load_data():
    master = pd.read_csv('gtd_master_summary.csv')
    orgs = pd.read_csv('gtd_org_summary.csv')
    return master, orgs

try:
    df, org_df = load_data()
except FileNotFoundError:
    st.error("Missing data files. Run the Jupyter script first.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Geography Explorer")
countries = sorted(df['country_txt'].unique())
sel_country = st.sidebar.selectbox("Country", countries)

states = sorted(df[df['country_txt'] == sel_country]['provstate'].unique())
sel_state = st.sidebar.selectbox("State/Province", ["All States"] + states)

if sel_state == "All States":
    city_options = ["All Cities"]
else:
    cities = sorted(df[(df['country_txt'] == sel_country) & (df['provstate'] == sel_state)]['city'].unique())
    city_options = ["All Cities"] + cities
sel_city = st.sidebar.selectbox("City", city_options)

# --- FILTERING LOGIC ---
m_df = df[df['country_txt'] == sel_country]
o_df = org_df[org_df['country_txt'] == sel_country]
label = sel_country

if sel_state != "All States":
    m_df = m_df[m_df['provstate'] == sel_state]
    o_df = o_df[o_df['provstate'] == sel_state]
    label = sel_state
    if sel_city != "All Cities":
        m_df = m_df[m_df['city'] == sel_city]
        o_df = o_df[o_df['city'] == sel_city]
        label = sel_city

# --- UI LAYOUT ---
st.title(f"Terrorism Analysis: {label}")

# Row 1: Top Metrics
k_total = m_df['nkill'].sum()
w_total = m_df['nwound'].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total Fatalities", f"{int(k_total):,}")
col2.metric("Total Wounded", f"{int(w_total):,}")

# Summary Stat: Deadliest Sub-Region
if sel_state == "All States":
    deadliest_name = m_df.groupby('provstate')['nkill'].sum().idxmax()
    deadliest_val = int(m_df.groupby('provstate')['nkill'].sum().max())
    col3.metric("Deadliest State", deadliest_name, f"{deadliest_val} killed")
elif sel_city == "All Cities":
    deadliest_name = m_df.groupby('city')['nkill'].sum().idxmax()
    deadliest_val = int(m_df.groupby('city')['nkill'].sum().max())
    col3.metric("Deadliest City", deadliest_name, f"{deadliest_val} killed")
else:
    col3.metric("Data Level", "City Focus")

st.divider()

# Row 2: Charts
tab1, tab2 = st.tabs(["📊 Trends Over Time", "🏴 Lethal Organizations"])

with tab1:
    trend = m_df.groupby('iyear')['nkill'].sum().reset_index()
    fig_trend = px.area(trend, x='iyear', y='nkill', title=f"Casualty Timeline: {label}",
                        color_discrete_sequence=['#b71c1c'])
    st.plotly_chart(fig_trend, use_container_width=True)

with tab2:
    # This now dynamically updates based on your sidebar!
    top_orgs = o_df.groupby('gname')['nkill'].sum().nlargest(10).reset_index()
    if not top_orgs.empty:
        fig_org = px.bar(top_orgs, x='nkill', y='gname', orientation='h', 
                         title=f"Top Threat Groups in {label}",
                         color='nkill', color_continuous_scale='Reds')
        fig_org.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_org, use_container_width=True)
    else:
        st.info(f"No identified group data for {label}")

st.sidebar.caption("Data aggregated from 1970-2020.")