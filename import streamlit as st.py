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
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# 1. DataFrame Utama untuk Grafik
kpi_data = pd.DataFrame({
    'KPI': ['Total Revenue', 'Total Profit', 'Average Order Value'],
    'Actual': [total_sales, total_profit, average_order_value],
    'Target': [TARGET_SALES, TARGET_PROFIT, TARGET_AOV],
    # Format '$,.0f' untuk integer/uang besar, '$,.2f' untuk desimal
    'Format': ['$,.0f', '$,.0f', '$,.2f'] 
})

# 2. Skema Warna dan Tier
PERFORMANCE_TIERS = [
    {'name': 'Bad (<80%)', 'range_end_perc': 0.80, 'color': '#add8e630'},
    {'name': 'Good (80-100%)', 'range_end_perc': 1.00, 'color': '#87ceeb50'},
    {'name': 'Great (100-120%)', 'range_end_perc': 1.20, 'color': '#4682b470'},
    {'name': 'Amazing (>120%)', 'range_end_perc': 1.50, 'color': '#1e90ff90'}
]

# 3. DataFrame Bands (Rentang Kinerja)
bands_list = []
for _, row in kpi_data.iterrows():
    target = row['Target']
    max_val = max(row['Actual'], target * 1.5) * 1.15
    
    current_start = 0
    for tier in PERFORMANCE_TIERS:
        end = target * tier['range_end_perc']
        if end > max_val: end = max_val 
        
        bands_list.append({
            'KPI': row['KPI'], 
            'start': current_start, 
            'end': end, 
            'band': tier['name'], 
            'color': tier['color']
        })
        current_start = end

df_bands = pd.DataFrame(bands_list)


# --- 2. FUNGSI PEMBUATAN BULLET CHART PENUH (REVISED FOR READABILITY) ---

def create_annual_bullet_chart(kpi_name, kpi_data, df_bands):
    """
    Membuat grafik Bullet Chart Penuh untuk satu KPI Tahunan (Monochromatic).
    Hanya menggunakan satu KPI per chart untuk skala yang benar.
    """
    
    # Filter data
    data = kpi_data[kpi_data['KPI'] == kpi_name]
    bands = df_bands[df_bands['KPI'] == kpi_name]
    format_string = data['Format'].iloc[0]
    
    # Tentukan domain X
    max_domain = bands['end'].max()

    # Common Encoding (Y-axis)
    y_encoding = alt.Y('KPI', title=None)
    
    # X-Scale: Sumbu utama (Actual Bar) dan Sumbu Bands harus berbagi skala X
    x_scale = alt.Scale(domain=[0, max_domain])
    x_axis = alt.Axis(format=format_string, labels=True) # Sumbu X dengan Label

    # 1. Background Bands (Lapisan Range)
    bands_chart = alt.Chart(bands).mark_bar(height=30).encode(
        x=alt.X('start', title=None, axis=None, scale=x_scale), # No Axis Label on 'start'
        x2='end',
        color=alt.Color('color', scale=None),
        y=y_encoding
    )

    # 2. Target Line (Lapisan Target)
    target_line = alt.Chart(data).mark_tick(
        color='black',
        thickness=3,
        size=50 
    ).encode(
        x=alt.X('Target', title=None, axis=None, scale=x_scale), # No Axis Label
        y=y_encoding,
        tooltip=[alt.Tooltip('Target', title='Target Tahunan', format=format_string)]
    )

    # 3. Actual Bar (Lapisan Aktual)
    actual_bar = alt.Chart(data).mark_bar(height=25, color='#1e90ff').encode(
        x=alt.X('Actual', title=None, axis=x_axis, scale=x_scale), # Tampilkan Label pada Sumbu X Bar Aktual
        y=y_encoding,
        tooltip=[alt.Tooltip('Actual', title='Aktual Tahunan', format=format_string)]
    )

    # 4. Text Label (Angka di sebelah kanan bar)
    text_label = alt.Chart(data).mark_text(
        align='left',
        baseline='middle',
        dx=5, 
        fontWeight='bold',
        fontSize=18
    ).encode(
        x=alt.X('Actual', title=None, scale=x_scale),
        y=y_encoding,
        text=alt.Text('Actual', format=format_string),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan
    return (bands_chart + actual_bar + target_line + text_label).configure_view(
        strokeOpacity=0
    ).properties(
        title=alt.TitleParams(kpi_name, anchor='start', fontSize=20),
        width=800, 
        height=150
    )


# --- Tampilan Dashboard ---

st.header("Ringkasan Kinerja 3 KPI Utama Tahunan (Aktual vs. Target)")
st.caption("Rentang Kinerja: Biru Muda ke Biru Tua menunjukkan Tier Kinerja. Garis hitam adalah Target.")

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
st.dataframe(kpi_data)import streamlit as st
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
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

# 1. DataFrame Utama untuk Grafik
kpi_data = pd.DataFrame({
    'KPI': ['Total Revenue', 'Total Profit', 'Average Order Value'],
    'Actual': [total_sales, total_profit, average_order_value],
    'Target': [TARGET_SALES, TARGET_PROFIT, TARGET_AOV],
    # Format '$,.0f' untuk integer/uang besar, '$,.2f' untuk desimal
    'Format': ['$,.0f', '$,.0f', '$,.2f'] 
})

# 2. Skema Warna dan Tier
PERFORMANCE_TIERS = [
    {'name': 'Bad (<80%)', 'range_end_perc': 0.80, 'color': '#add8e630'},
    {'name': 'Good (80-100%)', 'range_end_perc': 1.00, 'color': '#87ceeb50'},
    {'name': 'Great (100-120%)', 'range_end_perc': 1.20, 'color': '#4682b470'},
    {'name': 'Amazing (>120%)', 'range_end_perc': 1.50, 'color': '#1e90ff90'}
]

# 3. DataFrame Bands (Rentang Kinerja)
bands_list = []
for _, row in kpi_data.iterrows():
    target = row['Target']
    max_val = max(row['Actual'], target * 1.5) * 1.15
    
    current_start = 0
    for tier in PERFORMANCE_TIERS:
        end = target * tier['range_end_perc']
        if end > max_val: end = max_val 
        
        bands_list.append({
            'KPI': row['KPI'], 
            'start': current_start, 
            'end': end, 
            'band': tier['name'], 
            'color': tier['color']
        })
        current_start = end

df_bands = pd.DataFrame(bands_list)


# --- 2. FUNGSI PEMBUATAN BULLET CHART PENUH (REVISED FOR READABILITY) ---

def create_annual_bullet_chart(kpi_name, kpi_data, df_bands):
    """
    Membuat grafik Bullet Chart Penuh untuk satu KPI Tahunan (Monochromatic).
    Hanya menggunakan satu KPI per chart untuk skala yang benar.
    """
    
    # Filter data
    data = kpi_data[kpi_data['KPI'] == kpi_name]
    bands = df_bands[df_bands['KPI'] == kpi_name]
    format_string = data['Format'].iloc[0]
    
    # Tentukan domain X
    max_domain = bands['end'].max()

    # Common Encoding (Y-axis)
    y_encoding = alt.Y('KPI', title=None)
    
    # X-Scale: Sumbu utama (Actual Bar) dan Sumbu Bands harus berbagi skala X
    x_scale = alt.Scale(domain=[0, max_domain])
    x_axis = alt.Axis(format=format_string, labels=True) # Sumbu X dengan Label

    # 1. Background Bands (Lapisan Range)
    bands_chart = alt.Chart(bands).mark_bar(height=30).encode(
        x=alt.X('start', title=None, axis=None, scale=x_scale), # No Axis Label on 'start'
        x2='end',
        color=alt.Color('color', scale=None),
        y=y_encoding
    )

    # 2. Target Line (Lapisan Target)
    target_line = alt.Chart(data).mark_tick(
        color='black',
        thickness=3,
        size=50 
    ).encode(
        x=alt.X('Target', title=None, axis=None, scale=x_scale), # No Axis Label
        y=y_encoding,
        tooltip=[alt.Tooltip('Target', title='Target Tahunan', format=format_string)]
    )

    # 3. Actual Bar (Lapisan Aktual)
    actual_bar = alt.Chart(data).mark_bar(height=25, color='#1e90ff').encode(
        x=alt.X('Actual', title=None, axis=x_axis, scale=x_scale), # Tampilkan Label pada Sumbu X Bar Aktual
        y=y_encoding,
        tooltip=[alt.Tooltip('Actual', title='Aktual Tahunan', format=format_string)]
    )

    # 4. Text Label (Angka di sebelah kanan bar)
    text_label = alt.Chart(data).mark_text(
        align='left',
        baseline='middle',
        dx=5, 
        fontWeight='bold',
        fontSize=18
    ).encode(
        x=alt.X('Actual', title=None, scale=x_scale),
        y=y_encoding,
        text=alt.Text('Actual', format=format_string),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan
    return (bands_chart + actual_bar + target_line + text_label).configure_view(
        strokeOpacity=0
    ).properties(
        title=alt.TitleParams(kpi_name, anchor='start', fontSize=20),
        width=800, 
        height=150
    )


# --- Tampilan Dashboard ---

st.header("Ringkasan Kinerja 3 KPI Utama Tahunan (Aktual vs. Target)")
st.caption("Rentang Kinerja: Biru Muda ke Biru Tua menunjukkan Tier Kinerja. Garis hitam adalah Target.")

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
