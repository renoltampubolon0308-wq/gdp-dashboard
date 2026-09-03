import tempfile
import os
import geopandas as gpd

def baca_kml(uploaded_file):
    """
    Membaca file KML/KMZ yang diunggah via Streamlit.
    """
    if uploaded_file is None:
        return None
        
    # Ambil bytes data dengan benar
    if hasattr(uploaded_file, "getvalue"):
        file_bytes = uploaded_file.getvalue()
    elif hasattr(uploaded_file, "read"):
        file_bytes = uploaded_file.read()
    else:
        file_bytes = uploaded_file

    # Dapatkan ekstensi file (.kml atau .kmz)
    suffix = ".kml"
    if hasattr(uploaded_file, "name") and uploaded_file.name.lower().endswith(".kmz"):
        suffix = ".kmz"

    # Tulis ke file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # BACA KML/KMZ DENGAN GEOPANDAS
        gdf = gpd.read_file(tmp_path, driver='KML')
        return gdf
    except Exception as e:
        # Jika gagal, coba baca tanpa spesifikasi driver
        try:
            gdf = gpd.read_file(tmp_path)
            return gdf
        except Exception as err:
            st.error(f"Gagal membaca KML: {err}")
            return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
