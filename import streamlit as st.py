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
st.caption("Visualisasi Bullet Chart untuk membandingkan kinerja Aktual terhadap Rata-Rata Grup.")


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


# --- 3. FUNGSI PEMBUATAN BULLET CHART HORIZONTAL ---

def create_bullet_chart(data, group_col, actual_col, target_col, title):
    """
    Membuat grafik Bullet Chart Horizontal (Actual Bar vs Target Tick).
    """
    
    # 1. Base Chart
    base = alt.Chart(data).encode(
        y=alt.Y(group_col, sort=alt.EncodingSortField(field=actual_col, order='descending'), title=None),
        x=alt.X(actual_col, title=None, axis=alt.Axis(format='$,.0f'))
    ).properties(
        title=title,
        height=alt.Step(40) # Atur tinggi untuk setiap bar
    )
    
    # 2. Target Line (Garis Vertikal/Tick)
    target_line = base.mark_tick(
        color='black',
        thickness=2,
        size=30 # Ukuran tick
    ).encode(
        x=alt.X(target_col, title=None),
        tooltip=[alt.Tooltip(target_col, title='Target (Rata-Rata)', format='$,.2f')]
    )

    # 3. Actual Bar (Bar Nilai Aktual)
    actual_bar = base.mark_bar(height=15).encode(
        color=alt.condition(
            alt.datum[actual_col] >= alt.datum[target_col], 
            alt.value('#34A853'), # Hijau jika Diatas Target
            alt.value('#EA4335')  # Merah jika Dibawah Target
        ),
        tooltip=[group_col, alt.Tooltip(actual_col, title='Aktual', format='$,.2f')]
    )

    # 4. Text Label (Angka di sebelah kanan bar)
    text_label = base.mark_text(
        align='left',
        baseline='middle',
        dx=5  # Geser sedikit ke kanan dari ujung bar
    ).encode(
        text=alt.Text(actual_col, format='$,.0f'),
        order=alt.Order(actual_col, sort='descending'),
        color=alt.value('black')
    )
    
    # Gabungkan semua lapisan: Target Tick + Actual Bar + Text Label
    return (target_line + actual_bar + text_label).configure_axis(
        grid=False
    ).configure_view(
        strokeOpacity=0
    ).properties(
        width=300
    )


# --- Tampilan Dashboard ---

# Bagian KPI Cards (Metrik Tahunan)
st.subheader("Ringkasan Kinerja Tahunan (Total 2023)")
col1, col2, col3 = st.columns(3)

# ... (st.metric cards dipertahankan)
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

# Bagian Bullet Chart Kategorial
st.subheader("🎯 Kinerja Kategorial Pertahun (Aktual vs. Rata-Rata)")
st.caption("Garis hitam vertikal mewakili Rata-Rata KPI di seluruh Kategori/Wilayah.")

col_cat_sales, col_cat_profit, col_reg_sales, col_reg_profit = st.columns(4)

# 1. Revenue by Category
chart_cat_sales = create_bullet_chart(
    kpi_by_category, 'Category', 'Actual_Sales', 'Target_Sales', 
    'Revenue per Kategori'
)
with col_cat_sales:
    st.altair_chart(chart_cat_sales, use_container_width=True)

# 2. Profit by Category
chart_cat_profit = create_bullet_chart(
    kpi_by_category, 'Category', 'Actual_Profit', 'Target_Profit', 
    'Profit per Kategori'
)
with col_cat_profit:
    st.altair_chart(chart_cat_profit, use_container_width=True)

# 3. Revenue by Region
chart_reg_sales = create_bullet_chart(
    kpi_by_region, 'Region', 'Actual_Sales', 'Target_Sales', 
    'Revenue per Wilayah'
)
with col_reg_sales:
    st.altair_chart(chart_reg_sales, use_container_width=True)

# 4. Profit by Region
chart_reg_profit = create_bullet_chart(
    kpi_by_region, 'Region', 'Actual_Profit', 'Target_Profit', 
    'Profit per Wilayah'
)
with col_reg_profit:
    st.altair_chart(chart_reg_profit, use_container_width=True)
