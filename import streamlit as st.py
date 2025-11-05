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
st.caption("Visualisasi Bullet Chart Penuh dengan Tiers Kinerja (sesuai contoh visual).")


# --- Fungsi Pemuatan dan Pembersihan Data (Cache untuk performa) ---
@st.cache_data
def load_data():
    try:
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

# Nilai Target Tahunan Hipotetis
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

# Nilai Aktual Tahunan
total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# DataFrame Utama untuk Grafik
kpi_data = pd.DataFrame({
    'KPI': ['Total Revenue', 'Total Profit', 'Average Order Value'],
    'Actual': [total_sales, total_profit, average_order_value],
    'Target': [TARGET_SALES, TARGET_PROFIT, TARGET_AOV],
    'Format': ['$,.0f', '$,.0f', '$,.2f']
})

# 2. Skema Warna dan Tier (Diperjelas untuk Visualisasi)
PERFORMANCE_TIERS = [
    # Warna monokromatik biru dari muda ke tua
    {'name': 'Bad (<80%)', 'range_end_perc': 0.80, 'color': '#add8e630'},
    {'name': 'Good (80-100%)', 'range_end_perc': 1.00, 'color': '#87ceeb50'},
    {'name': 'Great (100-120%)', 'range_end_perc': 1.20, 'color': '#4682b470'},
    {'name': 'Amazing (>120%)', 'range_end_perc': 1.50, 'color': '#1e90ff90'} 
]

# 3. DataFrame Bands (Rentang Kinerja)
bands_list = []
for _, row in kpi_data.iterrows():
    target = row['Target']
    max_val = max(row['Actual'], target * 1.5) * 1.1 

    current_start = 0
    for tier in PERFORMANCE_TIERS:
        end = target * tier['range_end_perc']
        if end > max_val: end = max_val # Batasi band agar sesuai dengan skala maksimal
        
        bands_list.append({
            'KPI': row['KPI'], 
            'start': current_start, 
            'end': end, 
            'band': tier['name'], 
            'color': tier['color']
        })
        current_start = end

df_bands = pd.DataFrame(bands_list)


# --- 2. FUNGSI PEMBUATAN BULLET CHART PENUH (Dioptimalkan) ---

def create_annual_bullet_chart(kpi_name, kpi_data, df_bands):
    """Membuat grafik Bullet Chart Penuh untuk satu KPI Tahunan (Monochromatic)."""
    
    # Filter data
    data = kpi_data[kpi_data['KPI'] == kpi_name]
    bands = df_bands[df_bands['KPI'] == kpi_name]
    format_string = data['Format'].iloc[0]
    
    # Tentukan domain X agar mencakup semua bands dan nilai aktual
    max_domain = bands['end'].max()

    # Base Chart
    base = alt.Chart(data).encode(
        y=alt.Y('KPI', title=None)
    )

    # 1. Background Bands (Lapisan Range)
    bands_chart = alt.Chart(bands).mark_bar(height=30).encode(
        x=alt.X('start', title=None, axis=alt.Axis(format=format_string, labelPadding=10), scale=alt.Scale(domain=[0, max_domain])),
        x2='end',
        color=alt.Color('color', scale=None),
        y=alt.Y('KPI', title=None)
    )

    # 2. Target Line (Lapisan Target)
    target_line = base.mark_tick(
        color='black',
        thickness=3,
        size=50 
    ).encode(
        x=alt.X('Target', title=None, axis=None),
        tooltip=[alt.Tooltip('Target', title='Target Tahunan', format=format_string)]
    )

    # 3. Actual Bar (Lapisan Aktual)
    actual_bar = base.mark_bar(height=25, color='#1e90ff').encode( # Warna solid darkest blue
        x=alt.X('Actual', title=None),
        tooltip=[alt.Tooltip('Actual', title='Aktual Tahunan', format=format_string)]
    )

    # 4. Text Label (Menampilkan Nilai Aktual di sebelah kanan bar)
    text_label = base.mark_text(
        align='left',
        baseline='middle',
        dx=5, 
        fontWeight='bold',
        fontSize=18
    ).encode(
        x=alt.X('Actual', title=None),
        text=alt.Text('Actual', format=format_string),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan: Bands + Target + Bar + Label
    return (bands_chart + target_line + actual_bar + text_label).configure_axis(
        grid=False
    ).configure_view(
        strokeOpacity=0
    ).properties(
        title=alt.TitleParams(kpi_name, anchor='start', fontSize=20),
        width=800, 
        height=100
    ).resolve_scale(
        x='independent'
    )


# --- Tampilan Dashboard ---

st.header("Ringkasan Kinerja 3 KPI Utama Tahunan (Aktual vs. Target)")
st.caption("Tier Kinerja: Bad (<80%), Good (80%-100%), Great (100%-120%), Amazing (>120%). Garis hitam adalah Target.")

# Buat 3 Grafik Bullet dan tampilkan secara berurutan dalam satu kolom lebar
st.altair_chart(create_annual_bullet_chart('Total Revenue', kpi_data, df_bands), use_container_width=True)
st.altair_chart(create_annual_bullet_chart('Total Profit', kpi_data, df_bands), use_container_width=True)
st.altair_chart(create_annual_bullet_chart('Average Order Value', kpi_data, df_bands), use_container_width=True)

st.divider()

st.subheader("Tabel Data KPI")
st.dataframe(kpi_data)
