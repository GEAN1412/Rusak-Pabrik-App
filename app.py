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

# --- 2. KONFIGURASI DATABASE CLOUDINARY ---
USER_DB_PATH = "RusakPabrikApp/users.json"
DATA_DB_PATH = "RusakPabrikApp/data_laporan.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_log.json" # DB Baru untuk Log Login
FOTO_FOLDER = "RusakPabrikApp/Foto"

# Password Admin
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

# --- FUNGSI CATAT LOG LOGIN (BARU) ---
def catat_login_user(username):
    try:
        # 1. Ambil Log Lama
        log_data = get_json_fresh(LOG_DB_PATH)
        
        # 2. Update Data
        # Format: {"username": {"total": 10, "last_login": "2024-01-01 10:00"}}
        if username not in log_data:
            log_data[username] = {"total": 0, "last_login": "-"}
            
        log_data[username]["total"] += 1
        
        # Waktu Bali (UTC+8)
        now = datetime.utcnow() + timedelta(hours=8)
        log_data[username]["last_login"] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 3. Simpan
        upload_json(log_data, LOG_DB_PATH)
    except:
        pass # Silent error agar user tidak terganggu

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
                            # CATAT LOGIN DI SINI
                            catat_login_user(u)
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
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin"], horizontal=True)
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
            foto = st.file_uploader("Upload Foto BA", type=['jpg', 'jpeg', 'png'])
            st.caption("ℹ️ Foto akan otomatis dikompres oleh sistem agar ringan.")

            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if kode and nrb and foto:
                    if len(kode) != 4:
                        st.error("Kode Toko harus 4 digit!")
                    else:
                        with st.spinner("Mengirim data ke server..."):
                            # 1. Format Nama File & Path
                            tgl_str = tgl.strftime("%d%m%Y")
                            bln_folder = datetime.now().strftime("%Y-%m")
                            nama_file = f"{kode}_{nrb}_{tgl_str}"
                            path_cloud = f"{FOTO_FOLDER}/{bln_folder}/{nama_file}"
                            
                            # 2. Upload Foto
                            try:
                                res = cloudinary.uploader.upload(
                                    foto, 
                                    resource_type="image", 
                                    public_id=path_cloud, 
                                    overwrite=True,
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
                                
                                st.success("✅ Upload Sukses! Data telah tersimpan.")
                                st.balloons()
                                time.sleep(2)
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Gagal Upload: {e}")
                else:
                    st.warning("Mohon lengkapi semua data.")

    # --- MENU 2: ADMIN PANEL ---
    elif menu == "🔐 Menu Admin":
        st.subheader("Halaman Admin - Pusat Kontrol")
        
        # Cek Password Admin
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
            c_lock, c_space = st.columns([1, 5])
            with c_lock:
                if st.button("🔒 Logout Admin"):
                    st.session_state['admin_unlocked'] = False
                    st.rerun()
            
            st.write("")
            
            # --- TABS ADMIN ---
            tab_data, tab_user = st.tabs(["🏭 Cek Data Laporan", "👥 Kelola User & Password"])
            
            # --- TAB 1: DATA LAPORAN ---
            with tab_data:
                all_data = get_json_fresh(DATA_DB_PATH)
                if isinstance(all_data, list) and all_data:
                    df_all = pd.DataFrame(all_data)
                    
                    # FILTER
                    c1, c2, c3 = st.columns(3)
                    with c1: filter_toko = st.text_input("Cari Kode Toko:")
                    with c2: filter_nrb = st.text_input("Cari No NRB:")
                    with c3: filter_bln = st.text_input("Cari Bulan (YYYY-MM):")
                    
                    mask = pd.Series([True] * len(df_all))
                    if filter_toko: mask &= df_all['Kode_Toko'].str.contains(filter_toko.upper(), na=False)
                    if filter_nrb: mask &= df_all['No_NRB'].str.contains(filter_nrb.upper(), na=False)
                    if filter_bln: mask &= df_all['Bulan_Upload'].str.contains(filter_bln, na=False)
                    
                    df_show = df_all[mask].sort_values(by="Waktu_Input", ascending=False)
                    
                    st.info(f"Menampilkan {len(df_show)} data.")
                    
                    # SHOW DATA
                    for idx, row in df_show.iterrows():
                        with st.expander(f"{row['Kode_Toko']} - {row['No_NRB']} | Tgl: {row['Tanggal_NRB']}"):
                            ci, cd = st.columns([1, 3])
                            with ci:
                                st.image(row['Foto'], caption="Bukti Foto", width=200)
                            with cd:
                                st.write(f"**Penginput:** {row['User']}")
                                st.write(f"**Waktu:** {row['Waktu_Input']}")
                                dl_link = row['Foto'].replace("/upload/", "/upload/fl_attachment/")
                                st.markdown(f"📥 [**DOWNLOAD FOTO**]({dl_link})")
                    
                    st.markdown("---")
                    
                    # DOWNLOAD & HAPUS
                    csv = df_show.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Rekap (CSV)", csv, "Rekap_Rusak.csv", "text/csv", use_container_width=True)
                    
                    with st.expander("🚨 Hapus Data (Danger Zone)"):
                        list_bln = sorted(list(set(df_all['Bulan_Upload'].tolist())))
                        if list_bln:
                            del_target = st.selectbox("Pilih Bulan untuk Dihapus Total:", list_bln)
                            if st.button("🔥 Hapus Permanen Data Bulan Ini"):
                                new_data = [d for d in all_data if d.get('Bulan_Upload') != del_target]
                                upload_json(new_data, DATA_DB_PATH)
                                try:
                                    folder_path = f"{FOTO_FOLDER}/{del_target}/"
                                    cloudinary.api.delete_resources_by_prefix(folder_path)
                                    cloudinary.api.delete_folder(folder_path)
                                except: pass
                                st.success("Data berhasil dihapus!")
                                time.sleep(2)
                                st.rerun()
                else:
                    st.warning("Belum ada data masuk.")

            # --- TAB 2: KELOLA USER ---
            with tab_user:
                col_reset, col_log = st.columns(2)
                
                # BAGIAN KIRI: RESET PASSWORD
                with col_reset:
                    st.markdown("#### 🛠️ Ganti Password User")
                    with st.container(border=True):
                        db_users = get_json_fresh(USER_DB_PATH)
                        if db_users:
                            target_user = st.selectbox("Pilih Username:", list(db_users.keys()))
                            new_pass_admin = st.text_input("Password Baru:", type="password", key="adm_new_pass")
                            
                            if st.button("Simpan Password Baru", use_container_width=True):
                                if new_pass_admin:
                                    db_users[target_user] = hash_pass(new_pass_admin)
                                    upload_json(db_users, USER_DB_PATH)
                                    st.success(f"Password user '{target_user}' berhasil diubah!")
                                else:
                                    st.warning("Password tidak boleh kosong.")
                        else:
                            st.info("Belum ada user terdaftar.")

                # BAGIAN KANAN: LOG AKTIVITAS LOGIN
                with col_log:
                    st.markdown("#### 🕵️ Monitoring Login User")
                    with st.container(border=True):
                        if st.button("🔄 Refresh Log"): st.rerun()
                        
                        log_data = get_json_fresh(LOG_DB_PATH)
                        if log_data:
                            # Convert Log Dict to DataFrame
                            log_list = []
                            for usr, info in log_data.items():
                                log_list.append({
                                    "Username": usr,
                                    "Total Login": info.get("total", 0),
                                    "Terakhir Login": info.get("last_login", "-")
                                })
                            
                            df_log = pd.DataFrame(log_list)
                            # Sort berdasarkan login terakhir
                            df_log = df_log.sort_values(by="Terakhir Login", ascending=False)
                            
                            st.dataframe(df_log, use_container_width=True, hide_index=True)
                        else:
                            st.info("Belum ada aktivitas login.")

# --- RUN APP ---
if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state:
        st.session_state['user_login'] = None
    if st.session_state['user_login'] is None:
        halaman_login()
    else:
        halaman_utama()
