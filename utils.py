"""
Utilitas untuk analisis potensi lokasi retail.
Mencakup: baca KML, bersihkan data, hitung variabel spasial (fasum, kompetitor),
generate grid, dan model skoring lokasi.
"""

import re
import math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
import fiona
import warnings
import duckdb
warnings.filterwarnings("ignore")

fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"


# ---------------------------------------------------------------------------
# BACA & BERSIHKAN DATA
# ---------------------------------------------------------------------------

def baca_kml(file_bytes, nama_file="upload.kml"):
    """Baca file KML/KMZ yang diupload (dari Streamlit file_uploader) jadi GeoDataFrame."""
    import tempfile, os, zipfile

    suffix = ".kmz" if nama_file.lower().endswith(".kmz") else ".kml"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    if suffix == ".kmz":
        extract_dir = tmp_path + "_extracted"
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(tmp_path, "r") as z:
            z.extractall(extract_dir)
        # cari file .kml di dalam hasil extract
        kml_inner = None
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.lower().endswith(".kml"):
                    kml_inner = os.path.join(root, f)
                    break
        gdf = gpd.read_file(kml_inner, driver="KML")
    else:
        gdf = gpd.read_file(tmp_path, driver="KML")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    return gdf


def bersihkan_rupiah(x):
    """Ubah teks 'Rp 9,016,000' atau '- 2,315,900' jadi angka float."""
    if pd.isna(x):
        return None
    x = str(x)
    negatif = x.strip().startswith("-")
    angka = re.sub(r"[^\d]", "", x)
    if angka == "":
        return None
    hasil = float(angka)
    return -hasil if negatif else hasil


def bersihkan_kolom_uang(gdf, kolom_list):
    """Bersihkan beberapa kolom sekaligus jadi numerik."""
    gdf = gdf.copy()
    for kol in kolom_list:
        if kol in gdf.columns:
            gdf[kol] = gdf[kol].apply(bersihkan_rupiah)
    return gdf


def deteksi_kolom_uang(gdf, kata_kunci=("SPD", "PNL", "RAB", "OMZET", "SALES", "REVENUE")):
    """Cari otomatis kolom yang kemungkinan berisi nilai uang, berdasar nama kolom."""
    hasil = []
    for kol in gdf.columns:
        if any(k.lower() in kol.lower() for k in kata_kunci):
            hasil.append(kol)
    return hasil


# ---------------------------------------------------------------------------
# PROYEKSI & JARAK
# ---------------------------------------------------------------------------

def utm_epsg_otomatis(gdf):
    """Tentukan EPSG UTM yang sesuai berdasarkan centroid data (khusus Indonesia)."""
    centroid = gdf.geometry.unary_union.centroid
    lon, lat = centroid.x, centroid.y
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return 32600 + zone  # UTM North
    else:
        return 32700 + zone  # UTM South


def ke_utm(gdf, epsg=None):
    if epsg is None:
        epsg = utm_epsg_otomatis(gdf)
    return gdf.to_crs(epsg=epsg), epsg


def jarak_ke_terdekat(gdf_asal_utm, gdf_target_utm):
    """Untuk tiap titik di gdf_asal, hitung jarak (meter) ke titik terdekat di gdf_target."""
    if gdf_target_utm is None or len(gdf_target_utm) == 0:
        return np.full(len(gdf_asal_utm), np.nan)
    from scipy.spatial import cKDTree

    target_coords = np.array([(g.x, g.y) for g in gdf_target_utm.geometry])
    asal_coords = np.array([(g.x, g.y) for g in gdf_asal_utm.geometry])
    tree = cKDTree(target_coords)
    dist, _ = tree.query(asal_coords, k=1)
    return dist


# ---------------------------------------------------------------------------
# GRID
# ---------------------------------------------------------------------------

def generate_grid_dalam_polygon(polygon_wgs84, spacing_m=200):
    """Buat grid titik dengan jarak antar titik `spacing_m` meter, hanya yang jatuh di dalam polygon."""
    gdf_poly = gpd.GeoDataFrame(geometry=[polygon_wgs84], crs="EPSG:4326")
    epsg = utm_epsg_otomatis(gdf_poly)
    gdf_poly_utm = gdf_poly.to_crs(epsg=epsg)
    poly_utm = gdf_poly_utm.geometry.iloc[0]

    minx, miny, maxx, maxy = poly_utm.bounds
    xs = np.arange(minx, maxx, spacing_m)
    ys = np.arange(miny, maxy, spacing_m)

    titik = []
    for x in xs:
        for y in ys:
            p = Point(x, y)
            if poly_utm.contains(p):
                titik.append(p)

    gdf_grid_utm = gpd.GeoDataFrame(geometry=titik, crs=f"EPSG:{epsg}")
    gdf_grid_wgs84 = gdf_grid_utm.to_crs(epsg=4326)
    return gdf_grid_wgs84, gdf_grid_utm, epsg


# ---------------------------------------------------------------------------
# OSM - FASUM
# ---------------------------------------------------------------------------

def tarik_osm_bbox(bbox_wsen, tags=None):
    """Tarik data fasum OSM untuk 1 bounding box (west, south, east, north). Format osmnx >=2.x."""
    import osmnx as ox

    if tags is None:
        tags = {"amenity": True, "shop": True}
    west, south, east, north = bbox_wsen
    bbox = (west, south, east, north)
    gdf = ox.features_from_bbox(bbox=bbox, tags=tags)
    gdf = gdf[gdf.geometry.notna()]
    return gdf


def tarik_osm_jalan_bbox(bbox_wsen):
    """Tarik data jaringan jalan OSM untuk 1 bounding box (west, south, east, north)."""
    import osmnx as ox

    tags_jalan = {"highway": ["primary", "secondary", "tertiary", "trunk", "trunk_link",
                               "primary_link", "secondary_link", "residential"]}
    west, south, east, north = bbox_wsen
    gdf = ox.features_from_bbox(bbox=(west, south, east, north), tags=tags_jalan)
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    return gdf


def hitung_kepadatan_jalan_per_titik(gdf_titik_utm, gdf_jalan_utm, radius_m):
    """Untuk tiap titik: jarak ke jalan terdekat (m) dan total panjang jalan dalam radius (m)."""
    if gdf_jalan_utm is None or len(gdf_jalan_utm) == 0:
        base = pd.DataFrame(index=gdf_titik_utm.index)
        base["jarak_jalan_m"] = np.nan
        base["kepadatan_jalan_m"] = 0
        return base

    jalan_sindex = gdf_jalan_utm.sindex
    jarak_list, kepadatan_list = [], []

    for geom in gdf_titik_utm.geometry:
        jarak_list.append(gdf_jalan_utm.geometry.distance(geom).min())
        buffer = geom.buffer(radius_m)
        idx = list(jalan_sindex.query(buffer, predicate="intersects"))
        subset = gdf_jalan_utm.iloc[idx]
        panjang = subset.geometry.intersection(buffer).length.sum() if len(subset) else 0
        kepadatan_list.append(panjang)

    return pd.DataFrame(
        {"jarak_jalan_m": jarak_list, "kepadatan_jalan_m": kepadatan_list},
        index=gdf_titik_utm.index,
    )


def hitung_fasum_per_titik(gdf_titik_utm, gdf_fasum_utm, radius_m):
    """Hitung jumlah fasum dalam radius (meter) untuk tiap titik, pakai spatial join (cepat)."""
    if gdf_fasum_utm is None or len(gdf_fasum_utm) == 0:
        base = pd.DataFrame(index=gdf_titik_utm.index)
        base["jml_fasum"] = 0
        base["jml_convenience"] = 0
        return base

    buffer_geom = gdf_titik_utm.geometry.buffer(radius_m)
    gdf_buffer = gpd.GeoDataFrame(geometry=buffer_geom, crs=gdf_titik_utm.crs)
    gdf_buffer["idx_titik"] = gdf_titik_utm.index

    fasum_sindex = gdf_fasum_utm.sindex  # spatial index untuk mempercepat

    jml_fasum = []
    jml_convenience = []
    has_shop = "shop" in gdf_fasum_utm.columns

    for geom in gdf_buffer.geometry:
        kandidat_idx = list(fasum_sindex.query(geom, predicate="intersects"))
        subset = gdf_fasum_utm.iloc[kandidat_idx]
        jml_fasum.append(len(subset))
        if has_shop:
            jml_convenience.append((subset["shop"] == "convenience").sum())
        else:
            jml_convenience.append(0)

    hasil = pd.DataFrame(
        {"jml_fasum": jml_fasum, "jml_convenience": jml_convenience},
        index=gdf_titik_utm.index,
    )
    return hasil


# ---------------------------------------------------------------------------
# MODEL SKORING
# ---------------------------------------------------------------------------

def latih_model_skoring(df_fitur, target_col, feature_cols):
    """Latih Random Forest sederhana untuk memprediksi target (misal omzet) dari fitur lokasi."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score

    df_valid = df_fitur.dropna(subset=feature_cols + [target_col])
    if len(df_valid) < 10:
        return None, None, "Data valid terlalu sedikit untuk melatih model (minimal 10 baris)."

    X = df_valid[feature_cols]
    y = df_valid[target_col]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    skor_r2 = r2_score(y_test, y_pred)

    importance = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)

    # kategori keandalan model, supaya pengguna tahu batasannya
    if skor_r2 >= 0.4:
        keandalan = "cukup_baik"
    elif skor_r2 >= 0.15:
        keandalan = "lemah"
    else:
        keandalan = "sangat_lemah"

    return model, {"r2": skor_r2, "importance": importance, "keandalan": keandalan}, None


def prediksi_skor(model, df_fitur, feature_cols):
    df_valid = df_fitur.copy()
    df_valid[feature_cols] = df_valid[feature_cols].fillna(0)
    pred = model.predict(df_valid[feature_cols])
    return pred

# -------------------------------------------------------------------
# FUNGSI EKSTRAKSI KEPADATAN GOOGLE OPEN BUILDINGS
# -------------------------------------------------------------------
def hitung_kepadatan_google_buildings(lat, lon, radius_meter=500):
    """
    Menghitung jumlah & total luas footprint bangunan Google Open Buildings
    di sekitar titik koordinat toko (radius dalam meter).
    """
    con = duckdb.connect()
    
    # Query bounding box dari koordinat
    query = f"""
    SELECT id, geometry, area_in_meters
    FROM read_parquet('s3://open-buildings-data/v3/polygons/*.parquet')
    WHERE ST_Within(
        ST_GeomFromText(geometry),
        ST_Buffer(ST_Point({lon}, {lat}), {radius_meter / 111000.0})
    )
    """
    try:
        df_buildings = con.execute(query).df()
        total_bangunan = len(df_buildings)
        total_luas = df_buildings['area_in_meters'].sum() if not df_buildings.empty else 0
        return total_bangunan, total_luas
    except Exception as e:
        return 0, 0
