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
    
    div[data-testid="stForm"] button {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }
    
    .plain-link {
        display: block; text-align: center; margin-top: 15px;
        color: #888888; text-decoration: none; font-size: 0.9em;
        cursor: pointer;
    }
    .plain-link:hover { color: #28a745; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KONFIGURASI PATH ---
OLD_USER_DB = "RusakPabrikApp/user_rusak_pabrik.json"
USER_FOLDER = "RusakPabrikApp/Users"
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_rusak_pabrik.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "icnbr034"  
NAMA_FILE_PDF = "format_ba.pdf"

# --- 4. SYSTEM FUNCTIONS ---

def init_cloudinary():
    if "cloudinary" not in st.secrets:
        st.error("⚠️ Secrets Cloudinary belum dipasang!")
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
        resource_type="raw", public_id=public_id, overwrite=True
    )

def get_json_direct(public_id):
    cloud_name = st.secrets["cloudinary"]["cloud_name"]
    url = f"https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}"
    try:
        resp = requests.get(f"{url}?t={time.time()}")
        if resp.status_code == 200: return resp.json()
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

def get_user_id(username):
    return f"{USER_FOLDER}/{username.strip().lower()}_user_rusak_pabrik"

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

# --- 5. HALAMAN LOGIN ---

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
                    user_data = get_json_direct(get_user_id(u))
                    if user_data and user_data.get('password') == hash_pass(p):
                        st.session_state['user_login'] = u
                        catat_login_activity(u)
                        st.success("Berhasil!"); time.sleep(0.5); st.rerun()
                    else: st.error("Username atau Password Salah!")
            
            st.markdown(f'<a href="https://wa.me/6283114444424?text=Halo%20IC%20Dwi,%20saya%20lupa%20password%20Sistem%20Rusak%20Pabrik" target="_blank" class="plain-link">❓ Lupa Password? Hubungi IC Dwi</a>', unsafe_allow_html=True)
            
        with tab_up:
            with st.form("frm_daftar"):
                nu = st.text_input("Username Baru").strip()
                np = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                    if nu and np:
                        if get_json_direct(get_user_id(nu)): st.error("Username sudah ada!")
                        else:
                            upload_json({"username": nu, "password": hash_pass(np)}, get_user_id(nu))
                            st.success("Akun dibuat! Silakan Login.")
                    else: st.warning("Lengkapi data.")

# --- 6. HALAMAN UTAMA ---

def halaman_utama():
    with st.sidebar:
        st.header("👤 User Panel")
        st.success(f"Login: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"):
            st.session_state['user_login'] = None
            st.rerun()

    st.title("🏭 Sistem Rusak Pabrik")
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin (Rekap)"], horizontal=True)
    st.divider()

    if menu == "📝 Input Laporan Baru":
        with st.expander("📄 Lihat Format BA (PDF)"):
            if os.path.exists(NAMA_FILE_PDF):
                with open(NAMA_FILE_PDF, "rb") as f:
                    pdf_data = f.read()
                st.download_button("📥 Download PDF", pdf_data, "Format_BA.pdf", "application/pdf")
                base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            kode = c1.text_input("Kode Toko (4 Digit)", max_chars=4).upper()
            nrb = c2.text_input("Nomor NRB")
            tgl = st.date_input("Tanggal NRB")
            foto = st.file_uploader("Upload Foto BA", type=['jpg','png','jpeg'])
            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if kode and nrb and foto:
                    with st.spinner("Sedang Mengirim..."):
                        tgl_str = tgl.strftime("%d%m%Y")
                        bln = datetime.now().strftime("%Y-%m")
                        nama_f = f"{kode}_{nrb}_{tgl_str}_{random.randint(100,999)}"
                        res = cloudinary.uploader.upload(foto, public_id=f"{FOTO_FOLDER}/{bln}/{nama_f}", transformation=[{'width': 1000, 'quality': 'auto'}])
                        entri = {
                            "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Bulan_Upload": bln, "User": st.session_state['user_login'],
                            "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": res.get('secure_url')
                        }
                        data_lama = get_json_direct(DATA_DB_PATH) or []
                        data_lama.append(entri)
                        upload_json(data_lama, DATA_DB_PATH)
                        st.success("Laporan Tersimpan!"); time.sleep(1); st.rerun()
                else: st.warning("Mohon lengkapi semua data.")

    elif menu == "🔐 Menu Admin (Rekap)":
        if not st.session_state.get('admin_unlocked'):
            pw = st.text_input("Admin Password", type="password")
            if st.button("Buka Panel"):
                if pw == ADMIN_PASSWORD_ACCESS:
                    st.session_state['admin_unlocked'] = True
                    st.rerun()
                else: st.error("Password Salah!")
        else:
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            tab_data, tab_user, tab_migrasi = st.tabs(["📊 Cek & Hapus Laporan", "👥 Kelola User & Log", "🚀 Migrasi"])

            with tab_data:
                all_data = get_json_direct(DATA_DB_PATH)
                if isinstance(all_data, list) and all_data:
                    df_all = pd.DataFrame(all_data)
                    c1, c2 = st.columns(2)
                    f_toko = c1.text_input("Cari Kode Toko:")
                    f_nrb = c2.text_input("Cari No NRB:")
                    mask = pd.Series([True] * len(df_all))
                    if f_toko: mask &= df_all['Kode_Toko'].str.contains(f_toko.upper(), na=False)
                    if f_nrb: mask &= df_all['No_NRB'].str.contains(f_nrb.upper(), na=False)
                    df_show = df_all[mask].sort_values(by="Waktu_Input", ascending=False)
                    if f_toko or f_nrb:
                        final_df = df_show
                        st.success(f"🔍 Ditemukan {len(final_df)} data.")
                    else:
                        final_df = df_show.head(5)
                        st.info(f"📋 Menampilkan 5 Data Terbaru. Total: {len(df_all)} data.")
                    
                    for idx, row in final_df.iterrows():
                        with st.container(border=True):
                            ci, cd, c_del = st.columns([1, 3, 1])
                            ci.image(row['Foto'], width=150)
                            
                            with cd:
                                st.write(f"**{row['Kode_Toko']} - NRB {row['No_NRB']}**")
                                st.caption(f"Tgl NRB: {row['Tanggal_NRB']} | Upload: {row['Waktu_Input']} | User: {row['User']}")
                                
                                # --- TOMBOL DOWNLOAD FOTO (RESTORED) ---
                                clean_name = f"{row['Kode_Toko']}_{row['No_NRB']}_{row['Tanggal_NRB']}"
                                dl_link = row['Foto'].replace("/upload/", f"/upload/fl_attachment:{clean_name}/")
                                st.markdown(f"[📥 Download Foto]({dl_link})")
                                
                            if c_del.button("🗑️ Hapus", key=f"del_{row['Waktu_Input']}"):
                                if hapus_satu_file(row['Waktu_Input'], row['Foto']):
                                    st.success("Terhapus!"); time.sleep(1); st.rerun()
                    
                    st.divider()
                    st.download_button("📥 Download Rekap Laporan (CSV)", df_show.to_csv(index=False), "Rekap_Laporan_Rusak_Pabrik.csv", "text/csv")
                else: st.info("Belum ada data.")

            with tab_user:
                col_reset, col_log = st.columns([1, 1.5])
                with col_reset:
                    st.write("#### 🛠️ Ganti Password")
                    u_target = st.text_input("Username Target")
                    p_new = st.text_input("Password Baru", type="password")
                    if st.button("Simpan Password Baru"):
                        if u_target and p_new:
                            upload_json({"username": u_target, "password": hash_pass(p_new)}, get_user_id(u_target))
                            st.success("Password Diperbarui!"); time.sleep(1); st.rerun()

                with col_log:
                    st.write("#### 🕵️ Monitoring Akses")
                    log_data = get_json_direct(LOG_DB_PATH)
                    if log_data:
                        log_list = []
                        for tgl, users in log_data.items():
                            for usr, count in users.items():
                                log_list.append({"Tanggal": tgl, "User": usr, "Jumlah Akses": count})
                        
                        df_log = pd.DataFrame(log_list).sort_values(by="Tanggal", ascending=False)
                        st.dataframe(df_log, use_container_width=True, hide_index=True)
                        st.download_button("📥 Download Log Akses (CSV)", df_log.to_csv(index=False), "Log_Akses_User_Rusak_Pabrik.csv", "text/csv")
                        
                        st.write("#### 🕒 10 User Terbaru yang Akses")
                        st.table(df_log.head(10))
                    else: st.info("Belum ada aktivitas log.")

            with tab_migrasi:
                if st.button("JALANKAN MIGRASI"):
                    old_data = get_json_direct(OLD_USER_DB)
                    if old_data:
                        for user, hp in old_data.items():
                            upload_json({"username": user, "password": hp}, get_user_id(user))
                        st.success("Migrasi Berhasil!"); time.sleep(1); st.rerun()

# --- RUN ---
if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
