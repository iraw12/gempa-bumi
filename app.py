import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================

st.set_page_config(
    page_title="Dashboard Gempa Terkini",
    page_icon="🌋",
    layout="wide"
)

# ==========================================
# JUDUL
# ==========================================

st.title("🌋 Dashboard Gempa Terkini")

st.write(
    "Dashboard ini menampilkan data gempa terkini "
    "yang diperoleh melalui API U.S. Geological Survey (USGS)."
)

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.header("⚙️ Pengaturan Dashboard")

min_mag = st.sidebar.slider(
    "Magnitudo Minimum",
    min_value=0.0,
    max_value=10.0,
    value=2.5,
    step=0.1
)

jumlah_data = st.sidebar.slider(
    "Jumlah Data",
    min_value=20,
    max_value=300,
    value=100,
    step=10
)

# ==========================================
# API USGS
# ==========================================

url = (
    "https://earthquake.usgs.gov/"
    "earthquakes/feed/v1.0/summary/all_day.geojson"
)

# ==========================================
# MENGAMBIL DATA API
# ==========================================

try:

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 "
                          "(Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 "
                          "(KHTML, like Gecko) "
                          "Chrome/154.0 Safari/537.36"
        }
    )

    response.raise_for_status()

    data = response.json()

except requests.exceptions.ConnectionError:

    st.error(
        "❌ Koneksi ke server USGS gagal. "
        "Coba jalankan kembali beberapa saat lagi."
    )

    st.stop()

except requests.exceptions.Timeout:

    st.error(
        "⏳ Server USGS terlalu lama merespons. "
        "Silakan coba refresh."
    )

    st.stop()

except requests.exceptions.RequestException as e:

    st.error(
        f"❌ Terjadi masalah saat mengambil data USGS:\n\n{e}"
    )

    st.stop()

except ValueError:

    st.error(
        "❌ Data yang diterima dari USGS bukan format JSON yang valid."
    )

    st.stop()

# ==========================================
# MEMBUAT DATAFRAME
# ==========================================

rows = []

for gempa in data.get("features", []):

    properties = gempa.get("properties", {})
    geometry = gempa.get("geometry", {})

    coordinates = geometry.get("coordinates", [])

    if len(coordinates) >= 3:

        rows.append({
            "waktu": properties.get("time"),
            "lokasi": properties.get("place"),
            "magnitudo": properties.get("mag"),
            "kedalaman": coordinates[2],
            "latitude": coordinates[1],
            "longitude": coordinates[0]
        })

df = pd.DataFrame(rows)

# ==========================================
# CEK DATA
# ==========================================

if df.empty:

    st.warning(
        "⚠️ Tidak ada data gempa yang diterima dari API USGS."
    )

    st.stop()

# ==========================================
# MEMBERSIHKAN DATA
# ==========================================

df["waktu"] = pd.to_datetime(
    df["waktu"],
    unit="ms",
    errors="coerce"
)

df["magnitudo"] = pd.to_numeric(
    df["magnitudo"],
    errors="coerce"
)

df["kedalaman"] = pd.to_numeric(
    df["kedalaman"],
    errors="coerce"
)

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "waktu",
        "magnitudo",
        "latitude",
        "longitude"
    ]
)

# ==========================================
# FILTER MAGNITUDO
# ==========================================

df = df[
    df["magnitudo"] >= min_mag
].copy()

# ==========================================
# URUTKAN DATA
# ==========================================

df = df.sort_values(
    "waktu",
    ascending=False
).reset_index(drop=True)

# Batasi jumlah data
df = df.head(jumlah_data)

# Untuk grafik dibuat urut dari waktu lama → baru
df = df.sort_values(
    "waktu"
).reset_index(drop=True)

# ==========================================
# ROLLING WINDOW
# ==========================================

df["rolling_magnitudo"] = (
    df["magnitudo"]
    .rolling(
        window=5,
        min_periods=1
    )
    .mean()
)

# ==========================================
# INFORMASI UTAMA
# ==========================================

jumlah_gempa = len(df)

magnitudo_maks = df["magnitudo"].max()

rata_rata = df["magnitudo"].mean()

# ==========================================
# METRIC
# ==========================================

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "🔢 Jumlah Gempa",
        jumlah_gempa
    )

with col2:

    st.metric(
        "📈 Magnitudo Terbesar",
        f"{magnitudo_maks:.2f}"
    )

with col3:

    st.metric(
        "📊 Rata-rata Magnitudo",
        f"{rata_rata:.2f}"
    )

# ==========================================
# GRAFIK
# ==========================================

st.subheader(
    "📈 Pergerakan Magnitudo Gempa"
)

fig = go.Figure()

# ------------------------------------------
# Magnitudo
# ------------------------------------------

fig.add_trace(
    go.Scatter(
        x=df["waktu"],
        y=df["magnitudo"],
        mode="lines+markers",
        name="Magnitudo",
        customdata=df[
            ["lokasi", "kedalaman"]
        ].values,

        hovertemplate=
        "<b>Waktu:</b> %{x}<br>" +
        "<b>Magnitudo:</b> %{y:.2f}<br>" +
        "<b>Kedalaman:</b> %{customdata[1]:.1f} km<br>" +
        "<b>Lokasi:</b> %{customdata[0]}<br>" +
        "<extra></extra>"
    )
)

# ------------------------------------------
# Rolling Mean
# ------------------------------------------

fig.add_trace(
    go.Scatter(
        x=df["waktu"],
        y=df["rolling_magnitudo"],
        mode="lines",
        name="Rolling Mean"
    )
)

# ------------------------------------------
# Gempa ≥ 5
# ------------------------------------------

gempa_besar = df[
    df["magnitudo"] >= 5
]

fig.add_trace(
    go.Scatter(
        x=gempa_besar["waktu"],
        y=gempa_besar["magnitudo"],
        mode="markers",
        name="Magnitudo ≥ 5",

        marker=dict(
            size=10,
            color="red",
            symbol="x"
        )
    )
)

# ------------------------------------------
# Layout
# ------------------------------------------

fig.update_layout(
    template="plotly_dark",
    height=550,
    hovermode="x unified",
    title="Pergerakan Magnitudo Gempa"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ==========================================
# PETA
# ==========================================

st.subheader(
    "🗺️ Lokasi Gempa"
)

map_df = df[
    [
        "latitude",
        "longitude"
    ]
].dropna()

st.map(
    map_df,
    latitude="latitude",
    longitude="longitude"
)

# ==========================================
# TABEL
# ==========================================

st.subheader(
    "📋 Data Gempa"
)

tabel = df[
    [
        "waktu",
        "lokasi",
        "magnitudo",
        "kedalaman",
        "latitude",
        "longitude",
        "rolling_magnitudo"
    ]
].copy()

st.dataframe(
    tabel,
    use_container_width=True
)

# ==========================================
# REFRESH
# ==========================================

st.subheader(
    "🔄 Perbarui Data"
)

if st.button(
    "Ambil Data Terbaru"
):

    st.cache_data.clear()

    st.rerun()

# ==========================================
# SUMBER DATA
# ==========================================

st.caption(
    "Sumber data: U.S. Geological Survey (USGS) "
    "| Data diperoleh melalui GeoJSON API"
)