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

st.title("💰 Dashboard Kinerja 3 KPI Utama Tahunan (2023)")
st.caption("Visualisasi Bullet Chart untuk Revenue, Profit, dan AOV.")


# --- Fungsi Pemuatan dan Pembersihan Data (Cache untuk performa) ---
@st.cache_data
def load_data():
    try:
        # Memuat data dengan encoding fix ('latin-1' atau 'cp1252')
        df = pd.read_csv("sales_2023.csv", delimiter=';', encoding='latin-1')
    except UnicodeDecodeError:
        df = pd.read_csv("sales_2023.csv", delimiter=';', encoding='cp1252')
    except FileNotFoundError:
        st.error("Error: File 'sales_2023.csv' tidak ditemukan. Pastikan file berada di direktori yang sama.")
        return pd.DataFrame()
    
    df['Sales'] = df['Sales'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Profit'] = df['Profit'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Order Date'], inplace=True)

    return df

df = load_data()

if df.empty:
    st.stop()


# --- 1. PERHITUNGAN KPI TAHUNAN DAN PREPARASI DATA GRAFIK ---

# Nilai Target Tahunan
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

# Nilai Aktual Tahunan
total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# 1. DataFrame Utama untuk Grafik
kpi_data = pd.DataFrame({
    'KPI': ['Total Revenue', 'Total Profit', 'Average Order Value'],
    'Actual': [total_sales, total_profit, average_order_value],
    'Target': [TARGET_SALES, TARGET_PROFIT, TARGET_AOV],
    'Format': ['$,.2f', '$,.2f', '$,.2f'] # Format display Altair
})

# 2. DataFrame Bands (Rentang Kinerja)
bands_list = []
for _, row in kpi_data.iterrows():
    target = row['Target']
    
    bands_list.extend([
        {'KPI': row['KPI'], 'start': 0, 'end': target * 0.8, 'band': 'Poor', 'color': '#EA43351A'},
        {'KPI': row['KPI'], 'start': target * 0.8, 'end': target * 1.0, 'band': 'Average', 'color': '#FBBC041A'},
        {'KPI': row['KPI'], 'start': target * 1.0, 'end': target * 1.5, 'band': 'Good', 'color': '#34A8531A'},
    ])

df_bands = pd.DataFrame(bands_list)


# --- 2. FUNGSI PEMBUATAN BULLET CHART PENUH ---

def create_annual_bullet_chart(kpi_name, kpi_data, df_bands):
    """
    Membuat grafik Bullet Chart Penuh untuk satu KPI Tahunan.
    """
    
    # Filter data untuk KPI spesifik
    data = kpi_data[kpi_data['KPI'] == kpi_name]
    bands = df_bands[df_bands['KPI'] == kpi_name]
    
    actual_max = data['Actual'].iloc[0]
    target_val = data['Target'].iloc[0]
    format_string = data['Format'].iloc[0]
    
    # Tentukan domain X agar semua grafik memiliki skala yang berbeda namun logis
    max_domain = max(actual_max, target_val * 1.1) 
    
    # 1. Base Chart
    base = alt.Chart(data).encode(
        y=alt.Y('KPI', title=None)
    )

    # 2. Background Bands (Rentang Kinerja)
    bands_chart = alt.Chart(bands).mark_bar(height=25).encode(
        x=alt.X('start', title=None, axis=alt.Axis(format=format_string, labels=False, ticks=False)),
        x2='end',
        color=alt.Color('color', scale=None),
        y=alt.Y('KPI', title=None)
    )

    # 3. Target Line (Garis Vertikal/Tick)
    target_line = base.mark_tick(
        color='black',
        thickness=3,
        size=40 
    ).encode(
        x=alt.X('Target', title=None, axis=None),
        tooltip=[alt.Tooltip('Target', title=f'{kpi_name} Target', format=format_string)]
    )

    # 4. Actual Bar (Bar Nilai Aktual)
    actual_bar = base.mark_bar(height=20).encode(
        x=alt.X('Actual', title=None),
        color=alt.condition(
            alt.datum.Actual >= alt.datum.Target, 
            alt.value('#34A853'), # Hijau jika Tercapai
            alt.value('#EA4335')  # Merah jika Tidak Tercapai
        ),
        tooltip=[alt.Tooltip('Actual', title=f'{kpi_name} Aktual', format=format_string)]
    )

    # 5. Text Label (Angka di atas bar)
    text_label = base.mark_text(
        align='center',
        baseline='bottom',
        dy=-10,
        fontWeight='bold',
        fontSize=16
    ).encode(
        text=alt.Text('Actual', format=format_string),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan
    chart = (bands_chart + target_line + actual_bar + text_label).configure_axis(
        grid=False
    ).configure_view(
        strokeOpacity=0
    ).properties(
        title=kpi_name,
        width=500,
        height=100
    )
    return chart


# --- Tampilan Dashboard ---

st.subheader("Ringkasan Kinerja 3 KPI Utama Tahunan (Aktual vs. Target)")
st.caption("Rentang Kinerja: Merah (<80% Target), Kuning (80%-100% Target), Hijau (>100% Target). Garis hitam adalah Target Tahunan.")

# Buat 3 Grafik Bullet
chart_revenue = create_annual_bullet_chart('Total Revenue', kpi_data, df_bands)
chart_profit = create_annual_bullet_chart('Total Profit', kpi_data, df_bands)
chart_aov = create_annual_bullet_chart('Average Order Value', kpi_data, df_bands)

# Tampilkan dalam 3 kolom
col1, col2, col3 = st.columns(3)

with col1:
    st.altair_chart(chart_revenue, use_container_width=True)

with col2:
    st.altair_chart(chart_profit, use_container_width=True)

with col3:
    st.altair_chart(chart_aov, use_container_width=True)

st.divider()

st.subheader("Data Mentah KPI")
st.dataframe(kpi_data)
