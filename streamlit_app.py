"""
Dashboard Analisis Potensi Lokasi Retail
Upload data toko eksisting & kompetitor -> pilih wilayah (tombol) -> lihat titik potensial.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from shapely.geometry import shape, Point
from sklearn.cluster import KMeans

import utils

st.set_page_config(page_title="Analisis Potensi Lokasi Retail", layout="wide")

# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------
for key, default in [
    ("gdf_toko", None), ("gdf_kompetitor", None), ("hasil_analisis", None),
    ("wilayah_terpilih", None), ("nama_wilayah", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.title("ðŸ“ Analisis Potensi Lokasi Retail")

# ---------------------------------------------------------------------------
# SIDEBAR - UPLOAD
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("1. Upload Data")

    file_toko = st.file_uploader("Titik toko eksisting (KML/KMZ)", type=["kml", "kmz"], key="up_toko")
    if file_toko is not None:
        try:
            gdf = utils.baca_kml(file_toko.getvalue(), file_toko.name)
            gdf = gdf[gdf.geometry.notna()].reset_index(drop=True)

            if len(gdf) > 0:
                n_wilayah = min(8, max(1, len(gdf) // 30))
                coords = np.array([(g.y, g.x) for g in gdf.geometry])
                if n_wilayah > 1 and len(gdf) >= n_wilayah:
                    km = KMeans(n_clusters=n_wilayah, random_state=42, n_init=10)
                    gdf["wilayah_id"] = km.fit_predict(coords)
                else:
                    gdf["wilayah_id"] = 0

            st.session_state.gdf_toko = gdf
            st.success(f"{len(gdf)} titik toko terbaca, {gdf['wilayah_id'].nunique()} wilayah terdeteksi")
        except Exception as e:
            st.error(f"Gagal baca file toko: {e}")

    file_kompetitor = st.file_uploader("Titik kompetitor (opsional, KML/KMZ)", type=["kml", "kmz"], key="up_komp")
    if file_kompetitor is not None:
        try:
            gdf_k = utils.baca_kml(file_kompetitor.getvalue(), file_kompetitor.name)
            st.session_state.gdf_kompetitor = gdf_k[gdf_k.geometry.notna()]
            st.success(f"{len(st.session_state.gdf_kompetitor)} titik kompetitor terbaca")
        except Exception as e:
            st.error(f"Gagal baca file kompetitor: {e}")

    st.divider()
    st.header("2. Kolom Target (Omzet)")
    if st.session_state.gdf_toko is not None:
        kolom_tersedia = [c for c in st.session_state.gdf_toko.columns if c not in ("geometry", "wilayah_id")]
        kolom_uang_otomatis = utils.deteksi_kolom_uang(st.session_state.gdf_toko)
        kolom_target = st.selectbox(
            "Kolom omzet/penjualan toko",
            options=kolom_tersedia,
            index=kolom_tersedia.index(kolom_uang_otomatis[0]) if kolom_uang_otomatis else 0,
        )
    else:
        kolom_target = None
        st.info("Upload data toko terlebih dahulu")

    st.divider()
    st.header("3. Parameter")
    radius_var = st.slider("Radius hitung variabel (meter)", 100, 1000, 500, step=50)
    spacing_grid = st.slider("Jarak antar titik grid (meter)", 50, 500, 150, step=50)

# ---------------------------------------------------------------------------
# BARIS TOMBOL WILAYAH (mirip referensi papan kanban)
# ---------------------------------------------------------------------------
if st.session_state.gdf_toko is not None:
    gdf_toko_all = st.session_state.gdf_toko
    daftar_wilayah = sorted(gdf_toko_all["wilayah_id"].unique())

    st.write("**Pilih wilayah:**")
    cols = st.columns(len(daftar_wilayah) + 1)

    for i, wid in enumerate(daftar_wilayah):
        jumlah = (gdf_toko_all["wilayah_id"] == wid).sum()
        nama_default = st.session_state.nama_wilayah.get(wid, f"Wilayah {wid+1}")
        label = f"{nama_default} ({jumlah})"
        with cols[i]:
            if st.button(label, key=f"btn_wilayah_{wid}", use_container_width=True,
                         type="primary" if st.session_state.wilayah_terpilih == wid else "secondary"):
                st.session_state.wilayah_terpilih = wid
                st.session_state.hasil_analisis = None

    with cols[-1]:
        if st.button("Semua wilayah", use_container_width=True,
                     type="primary" if st.session_state.wilayah_terpilih is None else "secondary"):
            st.session_state.wilayah_terpilih = None
            st.session_state.hasil_analisis = None

    with st.expander("âœï¸ Ganti nama wilayah"):
        for wid in daftar_wilayah:
            nama_baru = st.text_input(f"Nama untuk wilayah {wid+1}",
                                       value=st.session_state.nama_wilayah.get(wid, f"Wilayah {wid+1}"),
                                       key=f"nama_input_{wid}")
            st.session_state.nama_wilayah[wid] = nama_baru

    if st.session_state.wilayah_terpilih is not None:
        gdf_toko_scope = gdf_toko_all[gdf_toko_all["wilayah_id"] == st.session_state.wilayah_terpilih]
    else:
        gdf_toko_scope = gdf_toko_all
else:
    gdf_toko_scope = None

st.divider()

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_peta, tab_analisis, tab_hasil = st.tabs(["ðŸ—ºï¸ Peta Toko", "ðŸŽ¯ Analisis Wilayah Baru", "ðŸ“Š Hasil"])

with tab_peta:
    if gdf_toko_scope is None:
        st.info("Upload data toko eksisting di sidebar untuk melihat peta.")
    else:
        center = [gdf_toko_scope.geometry.y.mean(), gdf_toko_scope.geometry.x.mean()]
        m = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

        for _, row in gdf_toko_scope.iterrows():
            popup_text = str(row.get("Name", "Toko"))
            if kolom_target and kolom_target in row:
                popup_text += f"<br>{kolom_target}: {row[kolom_target]}"
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x], radius=4,
                color="crimson", fill=True, fill_opacity=0.7, popup=popup_text,
            ).add_to(m)

        if st.session_state.gdf_kompetitor is not None:
            for _, row in st.session_state.gdf_kompetitor.iterrows():
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x], radius=4,
                    color="blue", fill=True, fill_opacity=0.7,
                    popup=str(row.get("Name", "Kompetitor")),
                ).add_to(m)

        st.caption("ðŸ”´ Toko eksisting  â€¢  ðŸ”µ Kompetitor")
        st_folium(m, width=None, height=550, key="peta_toko")

with tab_analisis:
    if gdf_toko_scope is None or kolom_target is None:
        st.info("Upload data toko & pilih kolom target di sidebar terlebih dahulu.")
    else:
        st.write("Tandai wilayah yang ingin dicek dalam ruang lingkup wilayah terpilih di atas.")
        mode_input = st.radio("Mode input", ["Gambar polygon di peta", "Upload KML batas wilayah", "Klik 1 titik"],
                               horizontal=True)

        polygon_terpilih, titik_terpilih = None, None

        if mode_input == "Upload KML batas wilayah":
            file_boundary = st.file_uploader("Upload KML batas wilayah", type=["kml", "kmz"], key="up_boundary")
            if file_boundary is not None:
                try:
                    gdf_boundary = utils.baca_kml(file_boundary.getvalue(), file_boundary.name)
                    polygon_terpilih = gdf_boundary.geometry.iloc[0]
                    st.success("Batas wilayah terbaca.")
                except Exception as e:
                    st.error(f"Gagal baca file: {e}")
        else:
            center = [gdf_toko_scope.geometry.y.mean(), gdf_toko_scope.geometry.x.mean()]
            m2 = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")
            for _, row in gdf_toko_scope.iterrows():
                folium.CircleMarker(location=[row.geometry.y, row.geometry.x], radius=3,
                                     color="crimson", fill=True, fill_opacity=0.5).add_to(m2)
            if mode_input == "Gambar polygon di peta":
                Draw(export=False,
                     draw_options={"polygon": True, "polyline": False, "rectangle": True,
                                   "circle": False, "marker": False, "circlemarker": False},
                     edit_options={"edit": True}).add_to(m2)

            hasil_peta = st_folium(m2, width=None, height=500, key="peta_input")

            if mode_input == "Gambar polygon di peta" and hasil_peta and hasil_peta.get("last_active_drawing"):
                polygon_terpilih = shape(hasil_peta["last_active_drawing"]["geometry"])
                st.success("Polygon berhasil digambar.")
            elif mode_input == "Klik 1 titik" and hasil_peta and hasil_peta.get("last_clicked"):
                lat, lon = hasil_peta["last_clicked"]["lat"], hasil_peta["last_clicked"]["lng"]
                titik_terpilih = Point(lon, lat)
                st.success(f"Titik dipilih: {lat:.5f}, {lon:.5f}")

        st.divider()
        jalankan = st.button("ðŸš€ Jalankan Analisis", type="primary",
                              disabled=(polygon_terpilih is None and titik_terpilih is None))

        if jalankan:
            with st.spinner("Memproses... (OSM fasum & jalan, model, skoring)"):
                try:
                    gdf_toko_full = st.session_state.gdf_toko.copy()
                    gdf_toko_full = utils.bersihkan_kolom_uang(gdf_toko_full, [kolom_target])
                    gdf_toko_full = gdf_toko_full[gdf_toko_full.geometry.notna()]

                    if titik_terpilih is not None:
                        gdf_grid_wgs = gpd.GeoDataFrame(geometry=[titik_terpilih], crs="EPSG:4326")
                        gdf_grid_utm, epsg = utils.ke_utm(gdf_grid_wgs)
                    else:
                        gdf_grid_wgs, gdf_grid_utm, epsg = utils.generate_grid_dalam_polygon(
                            polygon_terpilih, spacing_m=spacing_grid)

                    if len(gdf_grid_wgs) == 0:
                        st.error("Tidak ada titik grid dihasilkan. Perbesar area atau perkecil jarak grid.")
                        st.stop()

                    minx, miny, maxx, maxy = gdf_grid_wgs.total_bounds
                    pad = 0.1
                    bbox_area = (minx - pad, miny - pad, maxx + pad, maxy + pad)

                    gdf_toko_sekitar = gdf_toko_full.cx[bbox_area[0]:bbox_area[2], bbox_area[1]:bbox_area[3]]
                    if len(gdf_toko_sekitar) < 10:
                        gdf_toko_sekitar = gdf_toko_full

                    minx2, miny2, maxx2, maxy2 = gdf_toko_sekitar.total_bounds
                    bbox_final = (min(bbox_area[0], minx2), min(bbox_area[1], miny2),
                                  max(bbox_area[2], maxx2), max(bbox_area[3], maxy2))

                    gdf_fasum = utils.tarik_osm_bbox(bbox_final)
                    gdf_fasum_utm = gdf_fasum.to_crs(epsg=epsg)

                    gdf_jalan = utils.tarik_osm_jalan_bbox(bbox_final)
                    gdf_jalan_utm = gdf_jalan.to_crs(epsg=epsg)

                    gdf_toko_sekitar_utm = gdf_toko_sekitar.to_crs(epsg=epsg)
                    fitur_fasum_toko = utils.hitung_fasum_per_titik(gdf_toko_sekitar_utm, gdf_fasum_utm, radius_var)
                    fitur_jalan_toko = utils.hitung_kepadatan_jalan_per_titik(gdf_toko_sekitar_utm, gdf_jalan_utm, radius_var)

                    gdf_kompetitor_utm = None
                    if st.session_state.gdf_kompetitor is not None:
                        gdf_kompetitor_utm = st.session_state.gdf_kompetitor.to_crs(epsg=epsg)
                    jarak_komp_toko = utils.jarak_ke_terdekat(gdf_toko_sekitar_utm, gdf_kompetitor_utm)

                    df_latih = gdf_toko_sekitar.reset_index(drop=True).copy()
                    df_latih["jml_fasum"] = fitur_fasum_toko["jml_fasum"].values
                    df_latih["kepadatan_jalan"] = fitur_jalan_toko["kepadatan_jalan_m"].values
                    df_latih["jarak_jalan"] = fitur_jalan_toko["jarak_jalan_m"].values
                    df_latih["jarak_kompetitor"] = jarak_komp_toko

                    feature_cols = ["jml_fasum", "kepadatan_jalan", "jarak_jalan", "jarak_kompetitor"]
                    if gdf_kompetitor_utm is None:
                        feature_cols = ["jml_fasum", "kepadatan_jalan", "jarak_jalan"]
                        df_latih = df_latih.drop(columns=["jarak_kompetitor"])

                    model, info_model, err = utils.latih_model_skoring(df_latih, kolom_target, feature_cols)
                    if err:
                        st.error(err)
                        st.stop()

                    fitur_fasum_grid = utils.hitung_fasum_per_titik(gdf_grid_utm, gdf_fasum_utm, radius_var)
                    fitur_jalan_grid = utils.hitung_kepadatan_jalan_per_titik(gdf_grid_utm, gdf_jalan_utm, radius_var)
                    df_grid = gdf_grid_wgs.reset_index(drop=True).copy()
                    df_grid["jml_fasum"] = fitur_fasum_grid["jml_fasum"].values
                    df_grid["kepadatan_jalan"] = fitur_jalan_grid["kepadatan_jalan_m"].values
                    df_grid["jarak_jalan"] = fitur_jalan_grid["jarak_jalan_m"].values

                    if "jarak_kompetitor" in feature_cols:
                        df_grid["jarak_kompetitor"] = utils.jarak_ke_terdekat(gdf_grid_utm, gdf_kompetitor_utm)

                    df_grid["skor_prediksi"] = utils.prediksi_skor(model, df_grid, feature_cols)

                    st.session_state.hasil_analisis = {
                        "df_grid": df_grid, "info_model": info_model,
                        "n_toko_latih": len(df_latih), "kolom_target": kolom_target,
                    }
                    st.success("Analisis selesai! Lihat hasilnya di tab 'Hasil'.")
                except Exception as e:
                    st.error(f"Terjadi error: {e}")
                    st.exception(e)

with tab_hasil:
    hasil = st.session_state.hasil_analisis
    if hasil is None:
        st.info("Jalankan analisis di tab 'Analisis Wilayah Baru' terlebih dahulu.")
    else:
        df_grid = hasil["df_grid"]
        info_model = hasil["info_model"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Titik dianalisis", len(df_grid))
        col2.metric("Toko data latih", hasil["n_toko_latih"])
        col3.metric("Akurasi model (RÂ²)", f"{info_model['r2']:.2f}")

        pesan_keandalan = {
            "cukup_baik": "âœ… Model cukup baik menjelaskan pola omzet dari variabel lokasi yang tersedia.",
            "lemah": "âš ï¸ Model punya sinyal, tapi masih lemah â€” gunakan hasil ini sebagai referensi kasar, bukan keputusan final.",
            "sangat_lemah": "âš ï¸ **Model sangat lemah.** Variabel lokasi yang tersedia belum cukup menjelaskan omzet toko. Hasil skoring di bawah ini sebaiknya HANYA dipakai sebagai salah satu pertimbangan awal, dikombinasikan dengan survei lapangan dan penilaian bisnis langsung â€” bukan sebagai dasar keputusan tunggal.",
        }
        st.warning(pesan_keandalan.get(info_model["keandalan"], ""))

        st.subheader("Kepentingan Variabel")
        st.bar_chart(info_model["importance"])

        st.subheader("Peta Titik Potensial")
        center = [df_grid.geometry.y.mean(), df_grid.geometry.x.mean()]
        m3 = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")
        skor_min, skor_max = df_grid["skor_prediksi"].min(), df_grid["skor_prediksi"].max()

        def warna_skor(v):
            if skor_max == skor_min:
                return "#2ca25f"
            frac = (v - skor_min) / (skor_max - skor_min)
            return "#2ca25f" if frac > 0.66 else ("#fec44f" if frac > 0.33 else "#de2d26")

        for _, row in df_grid.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x], radius=6,
                color=warna_skor(row["skor_prediksi"]), fill=True, fill_opacity=0.8,
                popup=f"Skor prediksi: {row['skor_prediksi']:,.0f}",
            ).add_to(m3)
        st_folium(m3, width=None, height=550, key="peta_hasil")

        st.subheader("Ranking Titik Terbaik")
        df_tampil = df_grid.copy()
        df_tampil["latitude"] = df_tampil.geometry.y
        df_tampil["longitude"] = df_tampil.geometry.x
        df_tampil = df_tampil.drop(columns=["geometry"]).sort_values("skor_prediksi", ascending=False)
        st.dataframe(df_tampil.head(30), use_container_width=True)

        csv = df_tampil.to_csv(index=False).encode("utf-8")
        st.download_button("â¬‡ï¸ Download semua hasil (CSV)", csv, "hasil_analisis_lokasi.csv", "text/csv")

