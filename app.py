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
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Rusak Pabrik IC Bali", 
    layout="wide", 
    page_icon="🏭"
)

# --- 2. CSS UNTUK HIDE GITHUB & STYLE ---
hide_st_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
            [data-testid="stDecoration"] {visibility: hidden; display: none !important;}
            footer {visibility: hidden; display: none;}
            .main .block-container {padding-top: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. KONFIGURASI DATABASE ---
USER_DB_PATH = "RusakPabrikApp/users.json"
DATA_DB_PATH = "RusakPabrikApp/data_laporan.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity.json" # DB Baru untuk Log Login
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "admin123" 

# --- 4. SYSTEM FUNCTIONS ---
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
    """Ambil data JSON realtime"""
    try:
        resource = cloudinary.api.resource(public_id, resource_type="raw")
        url = resource.get('secure_url')
        if url:
            resp = requests.get(f"{url}?t={int(time.time())}")
            if resp.status_code == 200:
                return resp.json()
        return {} 
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

# --- FUNGSI CATAT LOG LOGIN ---
def catat_login_activity(username):
    try:
        log_data = get_json_fresh(LOG_DB_PATH)
        
        # Waktu Bali (UTC+8)
        now = datetime.utcnow() + timedelta(hours=8)
        tanggal_str = now.strftime("%Y-%m-%d")
        
        if tanggal_str not in log_data:
            log_data[tanggal_str] = {}
        
        if username not in log_data[tanggal_str]:
            log_data[tanggal_str][username] = 0
            
        log_data[tanggal_str][username] += 1
        
        upload_json(log_data, LOG_DB_PATH)
    except: pass

# --- 5. LOGIKA HALAMAN ---

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
                submit_login = st.form_submit_button("Masuk Sistem", use_container_width=True)
                
                if submit_login:
                    with st.spinner("Cek akun..."):
                        db = get_json_fresh(USER_DB_PATH)
                        ph = hash_pass(p)
                        if u in db and db[u] == ph:
                            st.session_state['user_login'] = u
                            catat_login_activity(u) # Catat Log
                            st.rerun()
                        else:
                            st.error("Username atau Password Salah!")
            
            st.markdown("""<a href="https://wa.me/6283114444424?text=Halo%20IC%20Dwi,%20saya%20lupa%20password%20Sistem%20Rusak%20Pabrik" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:8px; border-radius:5px; margin-top:10px;">❓ Lupa Password? Hubungi IC Dwi</button></a>""", unsafe_allow_html=True)
        
        with tab_up:
            with st.form("frm_daftar"):
                st.write("Buat Akun Baru")
                nu = st.text_input("Username Baru (Disarankan Kode Toko)")
                np = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                    if nu and np:
                        with st.spinner("Mendaftarkan..."):
                            db = get_json_fresh(USER_DB_PATH)
                            if nu in db:
                                st.error("Username sudah dipakai.")
                            else:
                                db[nu] = hash_pass(np)
                                upload_json(db, USER_DB_PATH)
                                st.success("Berhasil! Silakan Login.")
                    else: st.warning("Isi data dengan lengkap.")

def halaman_utama():
    with st.sidebar:
        st.header("👤 User Panel")
        st.success(f"Login: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"):
            st.session_state['user_login'] = None
            st.rerun()
        st.markdown("---")
        st.caption("Monitoring IC Bali - Rusak Pabrik System")

    st.title("🏭 Sistem Rusak Pabrik")
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin (Rekap)"], horizontal=True)
    st.divider()

    # --- MENU 1: INPUT LAPORAN ---
    if menu == "📝 Input Laporan Baru":
        st.subheader("Formulir Upload")
        form_placeholder = st.empty()
        with form_placeholder.container():
            with st.container(border=True):
                c1, c2 = st.columns(2)
                with c1: kode = st.text_input("Kode Toko (4 Digit)", max_chars=4, placeholder="CTH: F08C").upper()
                with c2: nrb = st.text_input("Nomor NRB", placeholder="Nomor Dokumen")
                tgl = st.date_input("Tanggal NRB")
                st.markdown("---")
                foto = st.file_uploader("Upload Foto BA", type=['jpg', 'jpeg', 'png'])
                st.caption("ℹ️ Foto akan otomatis dikompres oleh sistem agar ringan.")
                kirim_btn = st.button("Kirim Laporan", type="primary", use_container_width=True)

        if kirim_btn:
            if kode and nrb and foto:
                if len(kode) != 4: st.error("Kode Toko harus 4 digit!")
                else:
                    with st.spinner("Mengirim data..."):
                        try:
                            # 1. Upload Cloudinary
                            tgl_str = tgl.strftime("%d%m%Y")
                            bln_folder = datetime.now().strftime("%Y-%m")
                            nama_file = f"{kode}_{nrb}_{tgl_str}"
                            path_cloud = f"{FOTO_FOLDER}/{bln_folder}/{nama_file}"
                            res = cloudinary.uploader.upload(foto, resource_type="image", public_id=path_cloud, overwrite=True, transformation=[{'width': 1000, 'crop': 'limit'}, {'quality': 'auto:eco'}])
                            url_foto = res.get('secure_url')
                            
                            # 2. Simpan DB
                            data_lama = get_json_fresh(DATA_DB_PATH)
                            if not isinstance(data_lama, list): data_lama = []
                            entri = {
                                "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Bulan_Upload": bln_folder,
                                "User": st.session_state['user_login'],
                                "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": url_foto
                            }
                            data_lama.append(entri)
                            upload_json(data_lama, DATA_DB_PATH)
                            
                            st.success(f"✅ Data Berhasil Disimpan! NRB: {nrb}")
                            time.sleep(3)
                            form_placeholder.empty()
                            time.sleep(7)
                            st.rerun()
                        except Exception as e: st.error(f"Gagal Upload: {e}")
            else: st.warning("Mohon lengkapi semua data.")

    # --- MENU 2: ADMIN PANEL ---
    elif menu == "🔐 Menu Admin (Rekap)":
        st.subheader("Halaman Admin - Pusat Kontrol")
        
        if 'admin_unlocked' not in st.session_state: st.session_state['admin_unlocked'] = False
            
        if not st.session_state['admin_unlocked']:
            pw = st.text_input("Masukkan Password Admin:", type="password")
            if st.button("Buka Admin Panel"):
                if pw == ADMIN_PASSWORD_ACCESS:
                    st.session_state['admin_unlocked'] = True
                    st.rerun()
                else: st.error("Password Salah!")
        else:
            if st.button("🔒 Logout Admin"):
                st.session_state['admin_unlocked'] = False
                st.rerun()
            st.markdown("---")
            
            # --- TAB ADMIN ---
            tab_data, tab_user = st.tabs(["🏭 Cek Data Laporan", "👥 Kelola User & Monitoring"])
            
            # --- TAB 1: DATA LAPORAN ---
            with tab_data:
                all_data = get_json_fresh(DATA_DB_PATH)
                if isinstance(all_data, list) and all_data:
                    df_all = pd.DataFrame(all_data)
                    
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1: filter_toko = st.text_input("Cari Kode Toko:")
                    with c2: filter_nrb = st.text_input("Cari No NRB:")
                    
                    # TOMBOL CARI
                    cari_clicked = st.button("🔍 Cari Data", type="primary", use_container_width=True)
                    
                    # LOGIKA FILTER
                    mask = pd.Series([True] * len(df_all))
                    if filter_toko: mask &= df_all['Kode_Toko'].str.contains(filter_toko.upper(), na=False)
                    if filter_nrb: mask &= df_all['No_NRB'].str.contains(filter_nrb.upper(), na=False)
                    
                    df_show = df_all[mask].sort_values(by="Waktu_Input", ascending=False)
                    
                    st.write("")
                    
                    # KONDISI TAMPILAN
                    if cari_clicked or filter_toko or filter_nrb:
                         st.info(f"Hasil Pencarian: {len(df_show)} data ditemukan.")
                         final_df = df_show
                    else:
                        st.info("Menampilkan 5 Data Terbaru (Gunakan fitur Cari untuk data lama).")
                        final_df = df_show.head(5) # LIMIT 5

                    # LOOPING TAMPILAN GAMBAR
                    for idx, row in final_df.iterrows():
                        with st.expander(f"{row['Kode_Toko']} - {row['No_NRB']} | Tgl: {row['Tanggal_NRB']}"):
                            ci, cd = st.columns([1, 3])
                            with ci: st.image(row['Foto'], caption="Bukti Foto", width=200)
                            with cd:
                                st.write(f"**Penginput:** {row['User']}")
                                st.write(f"**Waktu:** {row['Waktu_Input']}")
                                dl_link = row['Foto'].replace("/upload/", "/upload/fl_attachment/")
                                st.markdown(f"📥 [**DOWNLOAD FOTO ORIGINAL**]({dl_link})")
                    
                    st.divider()
                    # DOWNLOAD EXCEL
                    csv = df_show.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Rekap Data (CSV)", csv, "Rekap_Rusak_Pabrik.csv", "text/csv", use_container_width=True)
                else:
                    st.warning("Belum ada data masuk sama sekali.")

            # --- TAB 2: KELOLA USER ---
            with tab_user:
                col_reset, col_log = st.columns(2)
                
                # BAGIAN KIRI: GANTI PASSWORD USER
                with col_reset:
                    st.markdown("#### 🛠️ Ganti Password User")
                    with st.container(border=True):
                        if st.button("🔄 Refresh List User"): st.rerun()
                        db_users = get_json_fresh(USER_DB_PATH)
                        if db_users:
                            target_user = st.selectbox("Pilih Username:", list(db_users.keys()))
                            new_pass_admin = st.text_input("Password Baru:", type="password", key="adm_new_pass")
                            
                            if st.button("Simpan Password Baru", use_container_width=True):
                                if new_pass_admin:
                                    db_users[target_user] = hash_pass(new_pass_admin)
                                    upload_json(db_users, USER_DB_PATH)
                                    st.success(f"Password '{target_user}' diubah!")
                                    time.sleep(1); st.rerun()
                                else: st.warning("Isi password dulu.")
                        else: st.info("Belum ada user.")

                # BAGIAN KANAN: MONITORING LOGIN & DOWNLOAD
                with col_log:
                    st.markdown("#### 🕵️ Monitoring Akses User")
                    with st.container(border=True):
                        if st.button("🔄 Refresh Log"): st.rerun()
                        log_data = get_json_fresh(LOG_DB_PATH)
                        
                        if log_data:
                            log_list = []
                            for tgl, users in log_data.items():
                                for usr, count in users.items():
                                    log_list.append({"Tanggal": tgl, "User": usr, "Jumlah Akses": count})
                            
                            df_log = pd.DataFrame(log_list)
                            if not df_log.empty:
                                df_log = df_log.sort_values(by="Tanggal", ascending=False)
                                st.dataframe(df_log, use_container_width=True, hide_index=True)
                                
                                # DOWNLOAD LOG CSV
                                csv_log = df_log.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Download Data Log (CSV)", csv_log, "Log_Aktivitas_User.csv", "text/csv", use_container_width=True)
                            else: st.info("Data log kosong.")
                        else: st.info("Belum ada aktivitas.")

# --- RUN APP ---
if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
