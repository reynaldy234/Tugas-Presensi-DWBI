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
st.caption("Bullet Chart untuk membandingkan Aktual vs. Rata-Rata dengan Rentang Kinerja.")


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
    
    # 1. Membersihkan kolom numerik (Sales dan Profit)
    df['Sales'] = df['Sales'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Profit'] = df['Profit'].astype(str).str.replace(',', '.', regex=False).astype(float)
    
    # 2. Mengkonversi Order Date ke datetime
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Order Date'], inplace=True)

    return df

df = load_data()

if df.empty:
    st.stop()


# --- 1. PERHITUNGAN KPI TAHUNAN (Untuk Metrik Card) ---
TARGET_SALES = 300000.00
TARGET_PROFIT = 25000.00
TARGET_AOV = 450.00

total_sales = df['Sales'].sum()
total_profit = df['Profit'].sum()
num_unique_orders = df['Order ID'].nunique()
average_order_value = total_sales / num_unique_orders

sales_delta = f"{((total_sales / TARGET_SALES) - 1) * 100:.2f}% vs Target"
profit_delta = f"{((total_profit / TARGET_PROFIT) - 1) * 100:.2f}% vs Target"
aov_delta = f"{((average_order_value / TARGET_AOV) - 1) * 100:.2f}% vs Target"


# --- 2. PERHITUNGAN KPI KATEGORIAL DAN TARGET (RATA-RATA) ---

# Agregasi dasar (Category)
kpi_by_category = df.groupby('Category').agg(
    Actual_Sales=('Sales', 'sum'),
    Actual_Profit=('Profit', 'sum')
).reset_index()
# Tambahkan Target (Rata-rata di semua kategori)
kpi_by_category['Target_Sales'] = kpi_by_category['Actual_Sales'].mean()
kpi_by_category['Target_Profit'] = kpi_by_category['Actual_Profit'].mean()

# Agregasi dasar (Region)
kpi_by_region = df.groupby('Region').agg(
    Actual_Sales=('Sales', 'sum'),
    Actual_Profit=('Profit', 'sum')
).reset_index()
# Tambahkan Target (Rata-rata di semua wilayah)
kpi_by_region['Target_Sales'] = kpi_by_region['Actual_Sales'].mean()
kpi_by_region['Target_Profit'] = kpi_by_region['Actual_Profit'].mean()


# --- 3. FUNGSI PEMBUATAN BULLET CHART PENUH ---

def create_full_bullet_chart(data, group_col, actual_col, target_col, title):
    """
    Membuat grafik Bullet Chart Penuh (Actual Bar, Target Tick, dan Range Kinerja).
    """
    
    # Tentukan Rentang Kinerja (Bands) berdasarkan persentase Target
    band_data = []
    target_value = data[target_col].iloc[0] # Ambil nilai target (rata-rata)
    
    # Band 1: Poor (0% - 80% Target)
    band_data.append({group_col: data[group_col].iloc[0], 'start': 0, 'end': target_value * 0.8, 'color': '#EA43351A', 'label': 'Poor'})
    # Band 2: Average (80% - 100% Target)
    band_data.append({group_col: data[group_col].iloc[0], 'start': target_value * 0.8, 'end': target_value * 1.0, 'color': '#FBBC041A', 'label': 'Avg'})
    # Band 3: Good (100% - 120% Target - atau sampai nilai maksimal)
    band_data.append({group_col: data[group_col].iloc[0], 'start': target_value * 1.0, 'end': data[actual_col].max() * 1.15, 'color': '#34A8531A', 'label': 'Good'})

    df_bands = pd.concat([pd.DataFrame([b]) for i in range(len(data)) for b in band_data])
    df_bands[group_col] = np.repeat(data[group_col].values, len(band_data) // len(data))


    # 1. Base Chart
    base = alt.Chart(data).encode(
        y=alt.Y(group_col, sort=alt.EncodingSortField(field=actual_col, order='descending'), title=None)
    ).properties(
        title=title,
        height=alt.Step(40)
    )

    # 2. Background Bands (Rentang Kinerja)
    bands = alt.Chart(df_bands).mark_bar(opacity=0.5, height=20).encode(
        x=alt.X('start', title=None, axis=alt.Axis(format='$,.0f')),
        x2='end',
        color=alt.Color('color', scale=None),
        y=alt.Y(group_col, title=None, sort=alt.EncodingSortField(field=actual_col, order='descending'))
    )

    # 3. Target Line (Garis Vertikal/Tick)
    target_line = base.mark_tick(
        color='black',
        thickness=2,
        size=30
    ).encode(
        x=alt.X(target_col, title=None),
        tooltip=[alt.Tooltip(target_col, title='Target (Rata-Rata)', format='$,.2f')]
    )

    # 4. Actual Bar (Bar Nilai Aktual)
    actual_bar = base.mark_bar(height=15).encode(
        x=alt.X(actual_col, title=None),
        color=alt.condition(
            alt.datum[actual_col] >= alt.datum[target_col], 
            alt.value('#34A853'),
            alt.value('#EA4335')
        ),
        tooltip=[group_col, alt.Tooltip(actual_col, title='Aktual', format='$,.2f')]
    )

    # 5. Text Label (Angka di sebelah kanan bar)
    text_label = base.mark_text(
        align='left',
        baseline='middle',
        dx=5
    ).encode(
        text=alt.Text(actual_col, format='$,.0f'),
        order=alt.Order(actual_col, sort='descending'),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan
    return (bands + target_line + actual_bar + text_label).configure_axis(
        grid=False
    ).configure_view(
        strokeOpacity=0
    ).properties(
        width=300
    )


# --- Tampilan Dashboard ---

# Bagian KPI Cards (Metrik Tahunan)
st.subheader("Ringkasan Kinerja Tahunan (Total 2023)")
# ... (st.metric cards dipertahankan)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Revenue (Penjualan)", value=f"${total_sales:,.2f}", delta=sales_delta, delta_color="normal" if total_sales >= TARGET_SALES else "inverse")
with col2:
    st.metric(label="Total Profit (Keuntungan)", value=f"${total_profit:,.2f}", delta=profit_delta, delta_color="normal" if total_profit >= TARGET_PROFIT else "inverse")
with col3:
    st.metric(label="Average Order Value (AOV)", value=f"${average_order_value:,.2f}", delta=aov_delta, delta_color="normal" if average_order_value >= TARGET_AOV else "inverse")

st.divider()

# Bagian Bullet Chart Kategorial
st.subheader("🎯 Kinerja Kategorial Pertahun (Aktual vs. Rata-Rata)")
st.caption("Background berwarna menunjukkan Rentang Kinerja: Merah (Poor: <80% Avg), Kuning (Avg: 80%-100% Avg), Hijau (Good: >100% Avg). Garis hitam adalah Rata-Rata.")

col_cat_sales, col_cat_profit, col_reg_sales, col_reg_profit = st.columns(4)

# 1. Revenue by Category
chart_cat_sales = create_full_bullet_chart(
    kpi_by_category, 'Category', 'Actual_Sales', 'Target_Sales', 
    'Revenue per Kategori'
)
with col_cat_sales:
    st.altair_chart(chart_cat_sales, use_container_width=True)

# 2. Profit by Category
chart_cat_profit = create_full_bullet_chart(
    kpi_by_category, 'Category', 'Actual_Profit', 'Target_Profit', 
    'Profit per Kategori'
)
with col_cat_profit:
    st.altair_chart(chart_cat_profit, use_container_width=True)

# 3. Revenue by Region
chart_reg_sales = create_full_bullet_chart(
    kpi_by_region, 'Region', 'Actual_Sales', 'Target_Sales', 
    'Revenue per Wilayah'
)
with col_reg_sales:
    st.altair_chart(chart_reg_sales, use_container_width=True)

# 4. Profit by Region
chart_reg_profit = create_full_bullet_chart(
    kpi_by_region, 'Region', 'Actual_Profit', 'Target_Profit', 
    'Profit per Wilayah'
)
with col_reg_profit:
    st.altair_chart(chart_reg_profit, use_container_width=True)
