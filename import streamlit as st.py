import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    page_title="Dashboard KPI Penjualan 2023",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("💰 Dashboard Kinerja KPI Penjualan 2023")
st.caption("Bullet chart gaya klasik dengan gradasi abu: perbandingan aktual vs target.")


# --- Fungsi Pemuatan Data ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("sales_2023.csv", delimiter=';', encoding='latin-1')
    except UnicodeDecodeError:
        df = pd.read_csv("sales_2023.csv", delimiter=';', encoding='cp1252')
    except FileNotFoundError:
        st.error("❌ File 'sales_2023.csv' tidak ditemukan.")
        return pd.DataFrame()

    df['Sales'] = df['Sales'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Profit'] = df['Profit'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Order Date'], inplace=True)
    return df


df = load_data()
if df.empty:
    st.stop()

# --- KPI & Target ---
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# Data KPI
kpi_data = pd.DataFrame({
    'KPI': ['Total Revenue', 'Total Profit', 'Average Order Value'],
    'Actual': [total_sales, total_profit, average_order_value],
    'Target': [TARGET_SALES, TARGET_PROFIT, TARGET_AOV],
    'Format': ['$,.0f', '$,.0f', '$,.2f']
})


# --- Fungsi Bullet Chart ---
def create_bullet_chart(kpi_name, df_kpi):
    data = df_kpi[df_kpi['KPI'] == kpi_name].iloc[0]
    actual = data['Actual']
    target = data['Target']
    fmt = data['Format']
    max_val = max(actual, target) * 1.2

    # Data untuk background range (3 gradasi abu)
    bands = pd.DataFrame({
        'start': [0, target * 0.4, target * 0.7],
        'end': [target * 0.4, target * 0.7, target],
        'color': ['#d9d9d9', '#a6a6a6', '#595959']  # abu muda → sedang → tua
    })

    base = alt.Chart(bands).mark_bar(size=40).encode(
        x='start:Q',
        x2='end:Q',
        color=alt.Color('color:N', scale=None)
    )

    # Bar aktual (nilai aktual)
    actual_bar = alt.Chart(pd.DataFrame({'value': [actual]})).mark_bar(
        color='#1f77b4',  # biru klasik
        size=20
    ).encode(
        x='value:Q'
    )

    # Garis target
    target_line = alt.Chart(pd.DataFrame({'target': [target]})).mark_rule(
        color='black',
        strokeWidth=2
    ).encode(
        x='target:Q'
    )

    # Label nilai aktual
    label = alt.Chart(pd.DataFrame({'value': [actual]})).mark_text(
        align='left',
        baseline='middle',
        dx=10,
        fontSize=13,
        fontWeight='bold',
        color='black'
    ).encode(
        x='value:Q',
        text=alt.Text('value:Q', format=fmt)
    )

    chart = (base + actual_bar + target_line + label).properties(
        title=alt.TitleParams(kpi_name, anchor='start', fontSize=16),
        width=800,
        height=80
    ).configure_view(strokeOpacity=0)

    return chart


# --- Tampilkan Dashboard ---
st.header("📊 Bullet Chart KPI Utama 2023")

chart_sales = create_bullet_chart("Total Revenue", kpi_data)
chart_profit = create_bullet_chart("Total Profit", kpi_data)
chart_aov = create_bullet_chart("Average Order Value", kpi_data)

st.altair_chart(chart_sales, use_container_width=True)
st.altair_chart(chart_profit, use_container_width=True)
st.altair_chart(chart_aov, use_container_width=True)

st.divider()
st.subheader("📋 Data KPI")
st.dataframe(kpi_data.style.format({'Actual': '{:,.2f}', 'Target': '{:,.2f}'}))
