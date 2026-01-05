import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
import hashlib
import requests
import io
import json
import time
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Rusak Pabrik IC Bali", 
    layout="wide", 
    page_icon="🏭"
)

# --- 2. KONFIGURASI DATABASE CLOUDINARY ---
# Kita gunakan nama file beda agar tidak bentrok dengan web lama
USER_DB_PATH = "RusakPabrikApp/users.json"
DATA_DB_PATH = "RusakPabrikApp/data_laporan.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"

# Password Khusus untuk masuk Menu Admin (Hardcoded biar simpel)
ADMIN_PASSWORD_ACCESS = "admin123" 

# --- 3. SYSTEM FUNCTIONS (CLOUDINARY) ---
def init_cloudinary():
    if "cloudinary" not in st.secrets:
        st.error("⚠️ Kunci Cloudinary belum dipasang di Secrets!")
        st.stop()
    cloudinary.config(
        cloud_name=st.secrets["cloudinary"]["cloud_name"],
        api_key=st.secrets["cloudinary"]["api_key"],
        api_secret=st.secrets["cloudinary"]["api_secret"],
        secure=True
    )

def get_json_fresh(public_id):
    """Ambil data JSON realtime (bypass cache)"""
    try:
        resource = cloudinary.api.resource(public_id, resource_type="raw")
        url = resource.get('secure_url')
        if url:
            resp = requests.get(f"{url}?t={int(time.time())}")
            if resp.status_code == 200:
                return resp.json()
        return {} # Return kosong jika file belum ada
    except:
        return {}

def upload_json(data_obj, public_id):
    """Simpan data JSON ke Cloud"""
    json_data = json.dumps(data_obj)
    cloudinary.uploader.upload(
        io.BytesIO(json_data.encode('utf-8')), 
        resource_type="raw", 
        public_id=public_id,
        overwrite=True
    )

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 4. LOGIKA UTAMA APLIKASI ---

def halaman_login():
    st.markdown("<h1 style='text-align: center;'>🏭 Pelaporan Rusak Pabrik</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_in, tab_up = st.tabs(["🔐 Login", "📝 Daftar Akun"])
        
        with tab_in:
            with st.form("frm_login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk Sistem", use_container_width=True):
                    with st.spinner("Cek akun..."):
                        db = get_json_fresh(USER_DB_PATH)
                        ph = hash_pass(p)
                        if u in db and db[u] == ph:
                            st.session_state['user_login'] = u
                            st.rerun()
                        else:
                            st.error("Username atau Password Salah!")
        
        with tab_up:
            with st.form("frm_daftar"):
                st.write("Buat Akun Baru")
                nu = st.text_input("Username Baru (Disarankan Kode Toko/Inisial)")
                np = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                    if nu and np:
                        with st.spinner("Mendaftarkan..."):
                            db = get_json_fresh(USER_DB_PATH)
                            if nu in db:
                                st.error("Username sudah dipakai orang lain.")
                            else:
                                db[nu] = hash_pass(np)
                                upload_json(db, USER_DB_PATH)
                                st.success("Berhasil! Silakan Login.")
                    else:
                        st.warning("Data tidak boleh kosong.")

def halaman_utama():
    # Sidebar Info User
    with st.sidebar:
        st.header("👤 User Panel")
        st.success(f"Login: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"):
            st.session_state['user_login'] = None
            st.rerun()
        
        st.markdown("---")
        st.caption("Monitoring IC Bali - Rusak Pabrik System")

    # Header
    st.title("🏭 Sistem Rusak Pabrik")
    
    # Menu Navigasi
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "📂 Riwayat Inputan Saya", "🔐 Menu Admin (Rekap)"], horizontal=True)
    st.divider()

    # --- MENU 1: INPUT LAPORAN ---
    if menu == "📝 Input Laporan Baru":
        st.subheader("Formulir Upload")
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                kode = st.text_input("Kode Toko (4 Digit)", max_chars=4, placeholder="CTH: F08C").upper()
            with c2:
                nrb = st.text_input("Nomor NRB", placeholder="Nomor Dokumen")
            
            tgl = st.date_input("Tanggal NRB")
            
            st.markdown("---")
            foto = st.file_uploader("Upload Foto BA (Max 2MB)", type=['jpg', 'jpeg', 'png'])
            st.caption("ℹ️ Foto otomatis dikompres oleh sistem agar ringan.")

            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if kode and nrb and foto:
                    if len(kode) != 4:
                        st.error("Kode Toko harus 4 digit!")
                    elif foto.size > 2 * 1024 * 1024:
                        st.error("Ukuran foto terlalu besar (>2MB). Harap screenshot dulu.")
                    else:
                        with st.spinner("Mengirim data..."):
                            # 1. Format Nama File & Path
                            tgl_str = tgl.strftime("%d%m%Y")
                            bln_folder = datetime.now().strftime("%Y-%m")
                            nama_file = f"{kode}_{nrb}_{tgl_str}"
                            path_cloud = f"{FOTO_FOLDER}/{bln_folder}/{nama_file}"
                            
                            # 2. Upload Foto
                            try:
                                res = cloudinary.uploader.upload(
                                    foto, resource_type="image", public_id=path_cloud, overwrite=True,
                                    transformation=[{'width': 1000, 'crop': 'limit'}, {'quality': 'auto:eco'}]
                                )
                                url_foto = res.get('secure_url')
                                
                                # 3. Simpan Data
                                data_lama = get_json_fresh(DATA_DB_PATH)
                                if not isinstance(data_lama, list): data_lama = []
                                
                                entri = {
                                    "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Bulan_Upload": bln_folder,
                                    "User": st.session_state['user_login'],
                                    "Kode_Toko": kode,
                                    "No_NRB": nrb,
                                    "Tanggal_NRB": str(tgl),
                                    "Foto": url_foto
                                }
                                data_lama.append(entri)
                                upload_json(data_lama, DATA_DB_PATH)
                                
                                st.success("✅ Laporan Berhasil Terkirim!")
                                time.sleep(1)
                                st.rerun() # Refresh agar form bersih
                            except Exception as e:
                                st.error(f"Gagal Upload: {e}")
                else:
                    st.warning("Mohon lengkapi semua data.")

    # --- MENU 2: RIWAYAT SAYA ---
    elif menu == "📂 Riwayat Inputan Saya":
        st.subheader("Riwayat Upload Anda")
        
        all_data = get_json_fresh(DATA_DB_PATH)
        if isinstance(all_data, list) and all_data:
            # Filter hanya data milik user yang login
            my_data = [d for d in all_data if d.get('User') == st.session_state['user_login']]
            
            if my_data:
                df = pd.DataFrame(my_data)
                # Sort dari yang terbaru
                df = df.sort_values(by="Waktu_Input", ascending=False)
                
                # Tampilkan Tabel
                st.dataframe(
                    df[['Waktu_Input', 'Kode_Toko', 'No_NRB', 'Tanggal_NRB', 'Foto']],
                    column_config={"Foto": st.column_config.LinkColumn("Lihat Bukti")},
                    use_container_width=True
                )
            else:
                st.info("Anda belum pernah melakukan input data.")
        else:
            st.info("Belum ada data di sistem.")

    # --- MENU 3: ADMIN PANEL (PROTECTED) ---
    elif menu == "🔐 Menu Admin (Rekap)":
        st.subheader("Halaman Admin - Krosecek Data")
        
        # Cek apakah sudah masukkan password admin sesi ini
        if 'admin_unlocked' not in st.session_state:
            st.session_state['admin_unlocked'] = False
            
        if not st.session_state['admin_unlocked']:
            pw = st.text_input("Masukkan Password Admin:", type="password")
            if st.button("Buka Admin Panel"):
                if pw == ADMIN_PASSWORD_ACCESS:
                    st.session_state['admin_unlocked'] = True
                    st.rerun()
                else:
                    st.error("Password Salah!")
        else:
            if st.button("🔒 Kunci Kembali"):
                st.session_state['admin_unlocked'] = False
                st.rerun()
            
            st.markdown("---")
            
            # --- DASHBOARD ADMIN ---
            all_data = get_json_fresh(DATA_DB_PATH)
            
            if isinstance(all_data, list) and all_data:
                df_all = pd.DataFrame(all_data)
                
                # 1. FILTERING
                c1, c2, c3 = st.columns(3)
                with c1: filter_toko = st.text_input("Cari Kode Toko:")
                with c2: filter_nrb = st.text_input("Cari No NRB:")
                with c3: filter_bln = st.text_input("Cari Bulan (YYYY-MM):")
                
                # Apply Filter
                mask = pd.Series([True] * len(df_all))
                if filter_toko: mask &= df_all['Kode_Toko'].str.contains(filter_toko.upper(), na=False)
                if filter_nrb: mask &= df_all['No_NRB'].str.contains(filter_nrb.upper(), na=False)
                if filter_bln: mask &= df_all['Bulan_Upload'].str.contains(filter_bln, na=False)
                
                df_show = df_all[mask].sort_values(by="Waktu_Input", ascending=False)
                
                st.info(f"Menampilkan {len(df_show)} data.")
                
                # 2. TAMPILAN GAMBAR + DOWNLOAD
                for idx, row in df_show.iterrows():
                    with st.expander(f"{row['Kode_Toko']} - {row['No_NRB']} ({row['Tanggal_NRB']})"):
                        ci, cd = st.columns([1, 3])
                        with ci:
                            st.image(row['Foto'], caption="Bukti Foto", width=200)
                        with cd:
                            st.write(f"**Penginput:** {row['User']}")
                            st.write(f"**Waktu:** {row['Waktu_Input']}")
                            # Link Download Langsung
                            dl_link = row['Foto'].replace("/upload/", "/upload/fl_attachment/")
                            st.markdown(f"📥 [**DOWNLOAD FOTO**]({dl_link})")
                
                st.markdown("---")
                
                # 3. DOWNLOAD EXCEL
                csv = df_show.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Rekap Data (CSV)", 
                    csv, 
                    "Rekap_Rusak_Pabrik.csv", 
                    "text/csv", 
                    use_container_width=True
                )
                
                # 4. HAPUS DATA BULANAN
                with st.expander("🚨 Danger Zone (Hapus Data)"):
                    list_bln = sorted(list(set(df_all['Bulan_Upload'].tolist())))
                    del_target = st.selectbox("Pilih Bulan untuk Dihapus Total:", list_bln)
                    if st.button("🔥 Hapus Permanen Data Bulan Ini"):
                        # Logika hapus (Filter data yg TIDAK sama dengan target)
                        new_data = [d for d in all_data if d.get('Bulan_Upload') != del_target]
                        upload_json(new_data, DATA_DB_PATH)
                        
                        # Hapus di Cloudinary (Optional, tapi bagus biar bersih)
                        try:
                            cloudinary.api.delete_resources_by_prefix(f"{FOTO_FOLDER}/{del_target}/")
                            cloudinary.api.delete_folder(f"{FOTO_FOLDER}/{del_target}/")
                        except: pass
                        
                        st.success("Data berhasil dihapus!")
                        time.sleep(2)
                        st.rerun()

            else:
                st.warning("Belum ada data masuk sama sekali.")

# --- RUN APP ---
if __name__ == "__main__":
    init_cloudinary()
    
    # State Login
    if 'user_login' not in st.session_state:
        st.session_state['user_login'] = None
        
    if st.session_state['user_login'] is None:
        halaman_login()
    else:
        halaman_utama()
