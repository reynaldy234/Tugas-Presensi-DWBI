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

st.title("💰 Dashboard Kinerja KPI Penjualan Tahunan (2023)")
st.caption("Analisis Total Revenue, Total Profit, dan Average Order Value (AOV)")


# --- Fungsi Pemuatan dan Pembersihan Data (Cache untuk performa) ---
@st.cache_data
def load_data():
    try:
        # Memuat data, mengatasi delimiter ';' dan encoding untuk karakter non-UTF8
        df = pd.read_csv("sales_2023.csv", delimiter=';', encoding='latin-1')
        
        # 1. Membersihkan kolom numerik (Sales dan Profit) dari koma desimal
        df['Sales'] = df['Sales'].astype(str).str.replace(',', '.', regex=False).astype(float)
        df['Profit'] = df['Profit'].astype(str).str.replace(',', '.', regex=False).astype(float)
        
        # 2. Mengkonversi Order Date ke datetime
        df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
        df.dropna(subset=['Order Date'], inplace=True) # Hapus baris jika tanggal tidak valid

        return df
    except FileNotFoundError:
        st.error("Error: File 'sales_2023.csv' tidak ditemukan. Pastikan file berada di direktori yang sama.")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()


# --- 1. PERHITUNGAN KPI TAHUNAN ---
# Target Hipotetis (untuk perbandingan di st.metric)
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

# Nilai Aktual Tahunan
total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# Menghitung Persentase Pencapaian (untuk st.metric)
sales_delta = f"{((total_sales / TARGET_SALES) - 1) * 100:.2f}% vs Target"
profit_delta = f"{((total_profit / TARGET_PROFIT) - 1) * 100:.2f}% vs Target"
aov_delta = f"{((average_order_value / TARGET_AOV) - 1) * 100:.2f}% vs Target"

# --- 2. PERHITUNGAN KPI BULANAN (untuk Tren) ---
df_monthly = df.copy()
df_monthly['Order Month'] = df_monthly['Order Date'].dt.to_period('M').astype(str)

monthly_kpi = df_monthly.groupby('Order Month').agg(
    Monthly_Sales=('Sales', 'sum'),
    Monthly_Profit=('Profit', 'sum')
).reset_index()


# --- Tampilan Dashboard ---

# Bagian KPI Cards (Metrik Tahunan)
st.subheader("Ringkasan Kinerja Tahunan (Total 2023)")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Revenue (Penjualan)",
        value=f"${total_sales:,.2f}",
        delta=sales_delta,
        delta_color="normal" if total_sales >= TARGET_SALES else "inverse"
    )

with col2:
    st.metric(
        label="Total Profit (Keuntungan)",
        value=f"${total_profit:,.2f}",
        delta=profit_delta,
        delta_color="normal" if total_profit >= TARGET_PROFIT else "inverse"
    )

with col3:
    st.metric(
        label="Average Order Value (AOV)",
        value=f"${average_order_value:,.2f}",
        delta=aov_delta,
        delta_color="normal" if average_order_value >= TARGET_AOV else "inverse"
    )

st.divider()

# Bagian Grafik Tren Bulanan
st.subheader("📈 Tren Penjualan dan Keuntungan Bulanan")

# Mengubah format data untuk Altair (Stacked bar/line)
chart_data = monthly_kpi.melt('Order Month', var_name='Metric', value_name='Value')

# Membuat Line Chart menggunakan Altair
base = alt.Chart(chart_data).encode(
    x=alt.X('Order Month', title='Bulan', sort=None)
)

line_chart = base.mark_line(point=True).encode(
    y=alt.Y('Value', title='Nilai ($)', axis=alt.Axis(format='$,.0f')),
    color=alt.Color('Metric', title="Metrik"),
    tooltip=['Order Month', alt.Tooltip('Value', format='$,.2f', title='Nilai')]
).properties(
    height=400
)

st.altair_chart(line_chart, use_container_width=True)

st.divider()

# Bagian Tabel Data
st.subheader("⊞ Data Mentah Penjualan (5 Baris Pertama)")
st.dataframe(df.head())