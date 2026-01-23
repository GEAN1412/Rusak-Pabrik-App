import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
import cloudinary.api
import hashlib
import requests
import io
import json
import time
import random
import base64
import os
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Rusak Pabrik IC Bali", 
    layout="wide", 
    page_icon="🏭"
)

# --- 2. CSS & STYLE ---
st.markdown("""
    <style>
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden; display: none !important;}
    footer {visibility: hidden; display: none;}
    .main .block-container {padding-top: 2rem;}
    
    /* Tombol Hijau */
    div[data-testid="stForm"] button {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    
    /* Link Polos */
    .plain-link {
        display: block;
        text-align: center;
        margin-top: 15px;
        color: #888888;
        text-decoration: none;
        font-size: 0.9em;
        cursor: pointer;
    }
    .plain-link:hover { color: #28a745; text-decoration: underline; }

    .delete-confirm {
        background-color: #ffcccc;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid red;
        text-align: center;
        margin-top: 5px;
        color: #8a0000;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KONFIGURASI DATABASE & PATH ---
# Path Lama (Untuk Migrasi)
OLD_USER_DB = "RusakPabrikApp/user_rusak_pabrik.json"

# Path Baru
USER_FOLDER = "RusakPabrikApp/Users"
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_rusak_pabrik.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "icnbr034"  
NAMA_FILE_PDF = "format_ba.pdf"

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

def upload_json(data_obj, public_id):
    json_data = json.dumps(data_obj)
    cloudinary.uploader.upload(
        io.BytesIO(json_data.encode('utf-8')), 
        resource_type="raw", 
        public_id=public_id,
        overwrite=True
    )

def get_json_direct(public_id):
    """Ambil data JSON bypass cache CDN"""
    cloud_name = st.secrets["cloudinary"]["cloud_name"]
    url = f"https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}"
    try:
        resp = requests.get(f"{url}?t={time.time()}")
        if resp.status_code == 200:
            return resp.json()
    except: pass
    return None

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def catat_login_activity(username):
    try:
        log_data = get_json_direct(LOG_DB_PATH) or {}
        now = datetime.utcnow() + timedelta(hours=8)
        tgl = now.strftime("%Y-%m-%d")
        if tgl not in log_data: log_data[tgl] = {}
        log_data[tgl][username] = log_data[tgl].get(username, 0) + 1
        upload_json(log_data, LOG_DB_PATH)
    except: pass

# --- 5. LOGIKA USER (ONE USER ONE FILE) ---

def get_user_id(username):
    return f"{USER_FOLDER}/{username.strip().lower()}_user_rusak_pabrik"

def cek_login(u, p):
    user_data = get_json_direct(get_user_id(u))
    if user_data and user_data.get('password') == hash_pass(p):
        return True
    return False

def simpan_laporan_aman(entri_baru):
    try:
        data_lama = get_json_direct(DATA_DB_PATH)
        if not isinstance(data_lama, list): data_lama = []
        data_lama.append(entri_baru)
        upload_json(data_lama, DATA_DB_PATH)
        return True, "Sukses"
    except Exception as e:
        return False, str(e)

def hapus_satu_file(timestamp_id, url_foto):
    try:
        data_lama = get_json_direct(DATA_DB_PATH)
        if isinstance(data_lama, list):
            data_baru = [d for d in data_lama if d.get('Waktu_Input') != timestamp_id]
            upload_json(data_baru, DATA_DB_PATH)
        if "upload/" in url_foto:
            try:
                public_id = url_foto.split("/upload/")[1].split("/", 1)[1].rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
            except: pass
        return True
    except: return False

# --- 6. HALAMAN LOGIN ---

def halaman_login():
    st.markdown("<h1 style='text-align: center;'>🏭 Pelaporan Rusak Pabrik</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        tab_in, tab_up = st.tabs(["🔐 Login", "📝 Daftar Akun"])
        with tab_in:
            with st.form("frm_login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk Sistem", use_container_width=True):
                    if cek_login(u, p):
                        st.session_state['user_login'] = u
                        catat_login_activity(u)
                        st.success("Berhasil!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Username/Password Salah atau Akun Belum Dimigrasi!")
            st.markdown('<a href="https://wa.me/6283114444424" class="plain-link">❓ Hubungi IC Dwi</a>', unsafe_allow_html=True)
        
        with tab_up:
            with st.form("frm_daftar"):
                nu = st.text_input("Username Baru").strip()
                np = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                    if nu and np:
                        if get_json_direct(get_user_id(nu)):
                            st.error("Username sudah ada!")
                        else:
                            upload_json({"username": nu, "password": hash_pass(np)}, get_user_id(nu))
                            st.success("Akun dibuat! Silakan Login.")
                    else: st.warning("Lengkapi data.")

# --- 7. HALAMAN UTAMA ---

def halaman_utama():
    with st.sidebar:
        st.header("👤 User Panel")
        st.success(f"Login: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"):
            st.session_state['user_login'] = None
            st.rerun()

    st.title("🏭 Sistem Rusak Pabrik")
    menu = st.radio("Menu:", ["📝 Input Laporan", "🔐 Menu Admin"], horizontal=True)
    st.divider()

    if menu == "📝 Input Laporan":
        # Fitur PDF
        with st.expander("📄 Lihat Format BA (PDF)"):
            if os.path.exists(NAMA_FILE_PDF):
                with open(NAMA_FILE_PDF, "rb") as f:
                    pdf_data = f.read()
                st.download_button("📥 Download PDF", pdf_data, "Format_BA.pdf", "application/pdf")
                base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500"></iframe>', unsafe_allow_html=True)

        # Form Input
        with st.container(border=True):
            c1, c2 = st.columns(2)
            kode = c1.text_input("Kode Toko", max_chars=4).upper()
            nrb = c2.text_input("Nomor NRB")
            tgl = st.date_input("Tanggal NRB")
            foto = st.file_uploader("Upload Foto BA", type=['jpg','png','jpeg'])
            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if kode and nrb and foto:
                    with st.spinner("Sedang Mengirim..."):
                        bln = datetime.now().strftime("%Y-%m")
                        nama_f = f"{kode}_{nrb}_{random.randint(100,999)}"
                        res = cloudinary.uploader.upload(foto, public_id=f"{FOTO_FOLDER}/{bln}/{nama_f}", transformation=[{'width': 1000, 'quality': 'auto'}])
                        entri = {
                            "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Bulan_Upload": bln, "User": st.session_state['user_login'],
                            "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": res.get('secure_url')
                        }
                        sukses, msg = simpan_laporan_aman(entri)
                        if sukses: st.success("Laporan Tersimpan!"); time.sleep(1); st.rerun()
                        else: st.error(msg)

    elif menu == "🔐 Menu Admin":
        if not st.session_state.get('admin_unlocked'):
            pw = st.text_input("Admin Password", type="password")
            if st.button("Buka Panel"):
                if pw == ADMIN_PASSWORD_ACCESS:
                    st.session_state['admin_unlocked'] = True
                    st.rerun()
        else:
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            
            t1, t2, t3 = st.tabs(["📊 Data Laporan", "👥 User & Log", "🚀 Migrasi Sistem"])
            
            with t1:
                data = get_json_direct(DATA_DB_PATH)
                if data:
                    df = pd.DataFrame(data).sort_values("Waktu_Input", ascending=False)
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 Download CSV", df.to_csv(index=False), "Rekap.csv", "text/csv")
                else: st.info("Belum ada data.")

            with t2:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("#### Monitoring Log")
                    logs = get_json_direct(LOG_DB_PATH)
                    if logs: st.write(logs)
                with col_b:
                    st.write("#### Ganti Password")
                    u_target = st.text_input("Username yang mau diubah")
                    p_new = st.text_input("Password Baru", type="password")
                    if st.button("Update Password"):
                        upload_json({"username": u_target, "password": hash_pass(p_new)}, get_user_id(u_target))
                        st.success("Berhasil diubah!")

            with t3:
                st.warning("### ⚠️ Fitur Migrasi Akun")
                st.write("Gunakan ini sekali saja untuk memindahkan user dari file JSON lama ke sistem 'Satu User Satu File'.")
                if st.button("MULAI MIGRASI SEKARANG"):
                    old_data = get_json_direct(OLD_USER_DB)
                    if old_data:
                        count = 0
                        for user, h_pass in old_data.items():
                            upload_json({"username": user, "password": h_pass}, get_user_id(user))
                            count += 1
                        st.success(f"✅ Migrasi Selesai! {count} user dipindahkan.")
                    else: st.error("File lama tidak ditemukan.")

# --- RUN ---
if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
