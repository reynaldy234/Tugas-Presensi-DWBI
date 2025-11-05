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
st.caption("Visualisasi Bullet Chart Penuh: Aktual vs. Target dengan Skema Warna Gradien.")


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

# Nilai Target Tahunan Hipotetis
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

# 2. Skema Warna dan Tier (Shades of Blue/Cyan)
# Monochromatic Tiers (Darker = Better Performance)
PERFORMANCE_TIERS = {
    'Bad': {'range_end_perc': 0.80, 'color': '#add8e630'},    # Light Blue (Transparant)
    'Good': {'range_end_perc': 1.00, 'color': '#87ceeb50'},   # Medium-Light Blue (Transparant)
    'Great': {'range_end_perc': 1.20, 'color': '#4682b470'},  # Medium-Dark Blue (Transparant)
    'Amazing': {'range_end_perc': 100, 'color': '#1e90ff90'}  # Dark Blue (Transparant, set range_end_perc tinggi)
}

# 3. DataFrame Bands (Rentang Kinerja)
bands_list = []
for _, row in kpi_data.iterrows():
    target = row['Target']
    
    current_start = 0
    for tier, data in PERFORMANCE_TIERS.items():
        if tier == 'Amazing':
            end = target * data['range_end_perc'] # Menggunakan 150% sebagai batas atas logis
            if end < row['Actual']: end = row['Actual'] * 1.1 # Pastikan band Amazing mencakup nilai aktual
        else:
            end = target * data['range_end_perc']
        
        bands_list.append({
            'KPI': row['KPI'], 
            'start': current_start, 
            'end': end, 
            'band': tier, 
            'color': data['color']
        })
        current_start = end

df_bands = pd.DataFrame(bands_list)


# --- 3. FUNGSI PEMBUATAN BULLET CHART PENUH (FIXED FOR MONOCHROMATIC & SIZE) ---

def create_annual_bullet_chart(kpi_name, kpi_data, df_bands):
    """
    Membuat grafik Bullet Chart Penuh untuk satu KPI Tahunan (Monochromatic).
    """
    
    # Filter data
    data = kpi_data[kpi_data['KPI'] == kpi_name]
    bands = df_bands[df_bands['KPI'] == kpi_name]
    
    actual_max = data['Actual'].iloc[0]
    target_val = data['Target'].iloc[0]
    format_string = data['Format'].iloc[0]
    
    # Tentukan domain X agar mencakup semua bands dan nilai aktual
    # Batas Maksimum ditetapkan sebagai maksimum dari (Target * 1.5) atau (Aktual * 1.1)
    max_domain = max(target_val * 1.5, actual_max * 1.1)

    # 1. Base Chart
    base = alt.Chart(data).encode(
        y=alt.Y('KPI', title=None)
    )

    # 2. Background Bands (Rentang Kinerja)
    bands_chart = alt.Chart(bands).mark_bar(height=30).encode(
        x=alt.X('start', title=None, axis=alt.Axis(format=format_string)),
        x2='end',
        # Menggunakan warna monokromatik dari data bands
        color=alt.Color('color', scale=None), 
        y=alt.Y('KPI', title=None)
    ).transform_filter(
        # Batasi sumbu x maksimum agar tidak terlalu lebar
        alt.datum.start < max_domain
    )

    # 3. Target Line (Garis Vertikal/Tick)
    target_line = base.mark_tick(
        color='black',
        thickness=3,
        size=50 
    ).encode(
        x=alt.X('Target', title=None),
        tooltip=[alt.Tooltip('Target', title=f'{kpi_name} Target', format=format_string)]
    )

    # 4. Actual Bar (Bar Nilai Aktual) - Monochromatic Darker Shade
    actual_bar = base.mark_bar(height=25, color='#1e90ff').encode( # Warna solid darkest blue
        x=alt.X('Actual', title=None),
        tooltip=[alt.Tooltip('Actual', title=f'{kpi_name} Aktual', format=format_string)]
    )

    # 5. Text Label (Angka di atas bar)
    text_label = base.mark_text(
        align='left',
        baseline='bottom',
        dx=5, # Geser ke kanan agar tidak menutupi bar
        fontWeight='bold',
        fontSize=18
    ).encode(
        x=alt.X('Actual', title=None),
        text=alt.Text('Actual', format=format_string),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan
    return (bands_chart + target_line + actual_bar + text_label).configure_axis(
        grid=False
    ).configure_view(
        strokeOpacity=0
    ).properties(
        title=alt.TitleParams(kpi_name, anchor='start', fontSize=20),
        width=700, # Ukuran chart yang lebih besar
        height=150
    ).interactive()


# --- Tampilan Dashboard ---

st.subheader("Ringkasan Kinerja 3 KPI Utama Tahunan (Aktual vs. Target)")
st.caption("Rentang Kinerja: Warna gradien (Biru Muda ke Biru Tua) menunjukkan Tier Kinerja. Garis hitam adalah Target Tahunan.")

# Buat 3 Grafik Bullet
chart_revenue = create_annual_bullet_chart('Total Revenue', kpi_data, df_bands)
chart_profit = create_annual_bullet_chart('Total Profit', kpi_data, df_bands)
chart_aov = create_annual_bullet_chart('Average Order Value', kpi_data, df_bands)

# Tampilkan dalam 1 kolom agar chart menjadi lebar (Ukuran Besar)
st.altair_chart(chart_revenue, use_container_width=True)
st.altair_chart(chart_profit, use_container_width=True)
st.altair_chart(chart_aov, use_container_width=True)

st.divider()

st.subheader("Tabel Data KPI")
st.dataframe(kpi_data)
