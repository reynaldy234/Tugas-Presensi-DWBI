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
st.caption("Menggunakan format Bullet Chart untuk KPI Tahunan dan Bulanan.")


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
    
    # 1. Membersihkan kolom numerik (Sales dan Profit) dari koma desimal
    df['Sales'] = df['Sales'].astype(str).str.replace(',', '.', regex=False).astype(float)
    df['Profit'] = df['Profit'].astype(str).str.replace(',', '.', regex=False).astype(float)
    
    # 2. Mengkonversi Order Date ke datetime
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Order Date'], inplace=True)

    return df

df = load_data()

if df.empty:
    st.stop()


# --- 1. PERHITUNGAN KPI TAHUNAN ---
# Target Hipotetis
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


# --- 2. PERHITUNGAN KPI BULANAN DAN TARGET RATA-RATA ---
df_monthly = df.copy()
df_monthly['Order Month'] = df_monthly['Order Date'].dt.to_period('M').astype(str)

monthly_kpi = df_monthly.groupby('Order Month').agg(
    Monthly_Sales=('Sales', 'sum'),
    Monthly_Profit=('Profit', 'sum')
).reset_index()

# Tentukan target bulanan sebagai Rata-Rata Bulanan sepanjang tahun
avg_monthly_sales = monthly_kpi['Monthly_Sales'].mean()
avg_monthly_profit = monthly_kpi['Monthly_Profit'].mean()

monthly_kpi['Sales_Target'] = avg_monthly_sales
monthly_kpi['Profit_Target'] = avg_monthly_profit


# --- FUNGSI PEMBUATAN BULLET CHART DENGAN ALTAIR ---
def create_bullet_chart(data, actual_col, target_col, title):
    # Tentukan lebar range/band (misalnya, 20% di bawah target)
    band_width = data[target_col].max() * 0.8
    
    base = alt.Chart(data).encode(
        y=alt.Y('Order Month', title=None, sort=None)
    ).properties(height=alt.Step(30))

    # 1. Background Range (misalnya, 80% dari target)
    background = base.mark_bar(color='#E6E6E6', height=10).encode(
        x=alt.X(f'{target_col}', title='Nilai ($)', axis=alt.Axis(format='$,.0f'))
    )

    # 2. Target Line (Garis Vertikal)
    target_line = base.mark_tick(
        color='black',
        thickness=2,
        size=15
    ).encode(
        x=alt.X(f'{target_col}'),
        tooltip=[alt.Tooltip(f'{target_col}', title='Target (Rata-Rata)', format='$,.2f')]
    )

    # 3. Actual Bar (Bar Nilai Aktual)
    actual_bar = base.mark_bar(height=10).encode(
        x=alt.X(f'{actual_col}'),
        color=alt.condition(
            alt.datum[actual_col] >= alt.datum[target_col], 
            alt.value('#34A853'), # Hijau jika Tercapai/Diatas Rata-rata
            alt.value('#EA4335')  # Merah jika Tidak Tercapai/Dibawah Rata-rata
        ),
        tooltip=[alt.Tooltip(f'{actual_col}', title='Aktual Bulanan', format='$,.2f')]
    )

    # Gabungkan semua lapisan
    chart = (background + target_line + actual_bar).resolve_scale(
        x='independent'
    ).properties(
        title=title
    )
    return chart


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

# Bagian Bullet Chart Bulanan
st.subheader("🎯 Kinerja Bulanan (Bullet Chart vs. Rata-Rata Bulanan)")
st.caption("Garis hitam vertikal mewakili Rata-Rata Bulanan sepanjang tahun. Bar hijau/merah mewakili Nilai Aktual Bulan tersebut.")

# Pisahkan chart Sales dan Profit menjadi dua kolom
col_sales_chart, col_profit_chart = st.columns(2)

# Chart Revenue Bulanan
sales_bullet_chart = create_bullet_chart(
    monthly_kpi, 'Monthly_Sales', 'Sales_Target', 
    'Revenue Bulanan vs. Rata-Rata'
)
with col_sales_chart:
    st.altair_chart(sales_bullet_chart, use_container_width=True)

# Chart Profit Bulanan
profit_bullet_chart = create_bullet_chart(
    monthly_kpi, 'Monthly_Profit', 'Profit_Target', 
    'Profit Bulanan vs. Rata-Rata'
)
with col_profit_chart:
    st.altair_chart(profit_bullet_chart, use_container_width=True)
