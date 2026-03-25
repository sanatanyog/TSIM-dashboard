import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import percentileofscore

# --- UI CONFIGURATION ---
st.set_page_config(page_title="TSIM | Intelligence Dashboard", layout="wide")

# Custom CSS for "Small but Readable" Professional UI
st.markdown("""
    <style>
    /* Global Font Scaling */
    html, body, [class*="css"]  { font-size: 14px; }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #b71c1c; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 13px !important; color: #455a64; }
    .stMetric { 
        border: 1px solid #eceff1; 
        padding: 10px 15px; 
        border-radius: 8px; 
        background-color: #ffffff;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.02);
    }
    
    /* Headers & Text */
    h1 { font-size: 28px !important; font-weight: 800; color: #263238; }
    h3 { font-size: 18px !important; font-weight: 600; margin-top: 10px; }
    .stCaption { font-size: 12px !important; color: #78909c; }
    
    /* Sidebar */
    .css-1d391kg { width: 250px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data
def load_tsim_data():
    try:
        master = pd.read_csv('gtd_master_summary.csv')
        orgs = pd.read_csv('gtd_org_summary.csv')
        return master, orgs
    except Exception as e:
        st.error(f"🚨 Data Load Failure: {e}")
        st.stop()

df, org_df = load_tsim_data()

# --- SIDEBAR SELECTORS ---
st.sidebar.header("📍 Region Selection")
countries = sorted(df['country_txt'].unique())
sel_country = st.sidebar.selectbox("Country", countries, index=countries.index("India") if "India" in countries else 0)

states = sorted(df[df['country_txt'] == sel_country]['provstate'].unique())
sel_state = st.sidebar.selectbox("State / Province", ["All States"] + states)

if sel_state == "All States":
    city_options = ["All Cities"]
else:
    cities = sorted(df[(df['country_txt'] == sel_country) & (df['provstate'] == sel_state)]['city'].unique())
    city_options = ["All Cities"] + cities
sel_city = st.sidebar.selectbox("City", city_options)

# --- LOGIC: DATA SLICING ---
m_df = df[df['country_txt'] == sel_country]
display_label = sel_country

if sel_state != "All States":
    m_df = m_df[m_df['provstate'] == sel_state]
    display_label = sel_state
    if sel_city != "All Cities":
        m_df = m_df[m_df['city'] == sel_city]
        display_label = sel_city

# --- LOGIC: RANKING & GRADING ---
def get_rankings():
    # World Comparison
    world_totals = df.groupby('country_txt')['nkill'].sum().sort_values(ascending=False)
    c_perc = percentileofscore(world_totals, world_totals.get(sel_country, 0))
    c_rank = list(world_totals.index).index(sel_country) + 1
    
    # National Comparison
    nat_totals = df[df['country_txt'] == sel_country].groupby('provstate')['nkill'].sum().sort_values(ascending=False)
    s_perc = percentileofscore(nat_totals, nat_totals.get(sel_state, 0)) if sel_state != "All States" else 0
    s_rank = (list(nat_totals.index).index(sel_state) + 1) if sel_state != "All States" else 0
    
    # Grade logic (A to D)
    grade = "A" if c_perc < 25 else "B" if c_perc < 50 else "C" if c_perc < 85 else "D"
    return c_perc, c_rank, s_perc, s_rank, grade, world_totals, nat_totals

c_perc, c_rank, s_perc, s_rank, grade, w_list, n_list = get_rankings()

# --- HEADER SECTION ---
st.title(f"Detailed Analysis: {display_label}")
st.caption("Aggregated Intelligence Report | Historical Period: 1970 – 2020")

# Metrics Row
col1, col2, col3, col4 = st.columns(4)
total_fatal = m_df['nkill'].sum()
col1.metric("Total Fatalities", f"{int(total_fatal):,}")
col2.metric("Total Injuries", f"{int(m_df['nwound'].sum()):,}")
col3.metric("Daily Avg Deaths", f"{(total_fatal/18628):.4f}")
col4.metric("Risk Grade", f"Level {grade}", help="A=Low Impact, D=High Impact")

st.divider()

# --- TABS SECTION ---
tab1, tab2, tab3 = st.tabs(["📈 Historical Trends", "🔥 Intensity Map", "🏁 Statistical Ranking"])

with tab1:
    l_col, r_col = st.columns([2, 1])
    with l_col:
        yearly = m_df.groupby('iyear')['nkill'].sum().reset_index()
        fig_time = px.area(yearly, x='iyear', y='nkill', title="Casualty Timeline",
                           labels={'iyear': 'Year', 'nkill': 'Fatalities'},
                           color_discrete_sequence=['#b71c1c'])
        fig_time.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_time, use_container_width=True)
    
    with r_col:
        # Organization Filtering
        o_slice = org_df[org_df['country_txt'] == sel_country]
        if sel_state != "All States": o_slice = o_slice[o_slice['provstate'] == sel_state]
        if sel_city != "All Cities": o_slice = o_slice[o_slice['city'] == sel_city]
        
        top_orgs = o_slice.groupby('gname')['nkill'].sum().nlargest(8).reset_index()
        fig_org = px.bar(top_orgs, x='nkill', y='gname', orientation='h', title="Top Groups",
                         labels={'nkill': 'Fatalities', 'gname': 'Group'},
                         color='nkill', color_continuous_scale='Reds')
        fig_org.update_layout(showlegend=False, height=350, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_org, use_container_width=True)

with tab2:
    st.subheader("Regional Intensity Score")
    st.caption("Treemap sizing reflects total fatalities; darker red indicates higher density.")
    path = ['provstate', 'city'] if sel_state == "All States" else ['city']
    fig_heat = px.treemap(df[df['country_txt'] == sel_country] if sel_state == "All States" else m_df,
                          path=path, values='nkill', color='nkill',
                          color_continuous_scale='Reds',
                          labels={'nkill': 'Fatalities', 'provstate': 'State', 'city': 'City'})
    fig_heat.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_heat, use_container_width=True)

with tab3:
    st.subheader("Leaderboard & Peer Comparison")
    
    g1, g2 = st.columns(2)
    with g1:
        fig_g1 = go.Figure(go.Indicator(
            mode = "gauge+number", value = c_perc,
            title = {'text': f"Global Risk Score: {sel_country}", 'font': {'size': 16}},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#b71c1c"},
                     'steps': [{'range': [0, 50], 'color': "#f1f8e9"}, {'range': [90, 100], 'color': "#fbe9e7"}]}))
        fig_g1.update_layout(height=250, margin=dict(t=50, b=20))
        st.plotly_chart(fig_g1, use_container_width=True)
        st.write(f"🌍 **{sel_country}** ranks **#{c_rank}** in total fatalities globally.")

    with g2:
        if sel_state != "All States":
            fig_g2 = go.Figure(go.Indicator(
                mode = "gauge+number", value = s_perc,
                title = {'text': f"National Risk Score: {sel_state}", 'font': {'size': 16}},
                gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#d32f2f"}}))
            fig_g2.update_layout(height=250, margin=dict(t=50, b=20))
            st.plotly_chart(fig_g2, use_container_width=True)
            st.write(f"📍 **{sel_state}** ranks **#{s_rank}** within {sel_country}.")
        else:
            st.info("Select a specific State to view National ranking metrics.")

    st.divider()
    
    # Peer Table
    st.write("### 🤝 Peer Benchmarking")
    l_table, r_table = st.columns(2)
    with l_table:
        st.caption("Top 5 Countries (Global Leaderboard)")
        st.dataframe(w_list.head(5).rename("Total Fatalities"), use_container_width=True)
    with r_table:
        if sel_state != "All States":
            st.caption(f"Top 5 States in {sel_country}")
            st.dataframe(n_list.head(5).rename("Total Fatalities"), use_container_width=True)

    # FOOTNOTE / METHODOLOGY
    with st.expander("📖 Methodology & Ranking Logic"):
        st.markdown("""
        **How these scores are generated:**
        - **Risk Score (0-100):** This is a *Percentile Rank*. A score of 90 means the region has higher recorded fatalities than 90% of its peers.
        - **Safety Grading:** - **Grade A:** Bottom 25% (Lowest relative impact)
            - **Grade B:** 25th - 50th percentile
            - **Grade C:** 50th - 85th percentile (Above average)
            - **Grade D:** Top 15% (Highest relative impact)
        - **Data Source:** Derived from the Global Terrorism Database (GTD) 1970-2020. 
        - **Disclaimer:** This module is for historical statistical analysis only and is not a real-time threat assessment.
        """)

st.sidebar.markdown("---")
st.sidebar.caption("TSIM v2.0 | Developed by Yogesh Singh")