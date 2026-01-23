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
st.set_page_config(page_title="Sistem Rusak Pabrik IC Bali", layout="wide", page_icon="🏭")

# --- 2. CSS & STYLE ---
st.markdown("""
    <style>
    [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden; display: none !important;}
    footer {visibility: hidden; display: none;}
    .main .block-container {padding-top: 2rem;}
    div[data-testid="stForm"] button { background-color: #28a745 !important; color: white !important; font-weight: bold !important; }
    .plain-link { display: block; text-align: center; margin-top: 15px; color: #888888; text-decoration: none; font-size: 0.9em; cursor: pointer; }
    .plain-link:hover { color: #28a745; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KONFIGURASI PATH ---
USER_FOLDER = "RusakPabrikApp/Users"
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_rusak_pabrik.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
OLD_USER_DB = "RusakPabrikApp/user_rusak_pabrik.json"
ADMIN_PASSWORD_ACCESS = "icnbr034"  
NAMA_FILE_PDF = "format_ba.pdf"

# --- 4. CORE FUNCTIONS ---
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
    try:
        json_data = json.dumps(data_obj)
        cloudinary.uploader.upload(
            io.BytesIO(json_data.encode('utf-8')), 
            resource_type="raw", public_id=public_id, overwrite=True, invalidate=True
        )
        return True
    except: return False

def get_json_direct(public_id):
    cloud_name = st.secrets["cloudinary"]["cloud_name"]
    url = f"https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}"
    try:
        resp = requests.get(f"{url}?t={int(time.time())}", timeout=10)
        if resp.status_code == 200: return resp.json()
    except: pass
    return None

def hash_pass(password): return hashlib.sha256(str.encode(password)).hexdigest()

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
    clean_u = username.strip().replace(" ", "_")
    return f"{USER_FOLDER}/{clean_u}_user_rusak_pabrik"

def hapus_satu_file(timestamp_id, url_foto):
    """Menghapus data di JSON dan file fisik di Cloudinary"""
    try:
        data_lama = get_json_direct(DATA_DB_PATH) or []
        data_baru = [d for d in data_lama if d.get('Waktu_Input') != timestamp_id]
        upload_json(data_baru, DATA_DB_PATH)
        
        if "upload/" in url_foto:
            try:
                # Ambil public_id dengan benar untuk folder root maupun subfolder
                path_after_upload = url_foto.split("/upload/")[1]
                path_without_version = path_after_upload.split("/", 1)[1]
                public_id = path_without_version.rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
            except: pass
        return True
    except: return False

def migrasi_foto_cloud():
    try:
        current_data = get_json_direct(DATA_DB_PATH) or []
        existing_urls = [d.get('Foto') for d in current_data]
        resources = cloudinary.api.resources(type="upload", resource_type="image", max_results=500)
        added_count = 0
        for res in resources.get('resources', []):
            url = res.get('secure_url')
            if url not in existing_urls:
                name_only = res.get('public_id').split('/')[-1]
                parts = name_only.split('_')
                kode = parts[0] if len(parts) > 0 else "MISC"
                nrb = parts[1] if len(parts) > 1 else "NOMOR_NRB"
                tgl_nrb = parts[2] if len(parts) > 2 else "2026-01-01"
                current_data.append({
                    "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Bulan_Upload": datetime.now().strftime("%Y-%m"),
                    "User": "Auto_Migrator", "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": tgl_nrb, "Foto": url
                })
                added_count += 1
        if added_count > 0:
            upload_json(current_data, DATA_DB_PATH)
            return True, f"Berhasil menarik {added_count} foto."
        return True, "Data sudah sinkron."
    except Exception as e: return False, str(e)

# --- 5. HALAMAN LOGIN & DAFTAR ---
def halaman_login():
    st.markdown("<h1 style='text-align: center;'>🏭 Pelaporan Rusak Pabrik</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        tab_in, tab_up = st.tabs(["🔐 Login", "📝 Daftar Akun"])
        with tab_in:
            with st.form("frm_login"):
                u, p = st.text_input("Username").strip(), st.text_input("Password", type="password")
                if st.form_submit_button("Masuk Sistem", use_container_width=True):
                    user_data = get_json_direct(get_user_id(u))
                    if user_data and user_data.get('password') == hash_pass(p):
                        st.session_state['user_login'] = u
                        catat_login_activity(u)
                        st.toast(f"Selamat datang, {u}!", icon="👋")
                        time.sleep(1); st.rerun()
                    else: st.error("Username atau Password Salah!")
            st.markdown(f'<a href="https://wa.me/6283114444424?text=Halo%20IC%20Dwi" target="_blank" class="plain-link">❓ Lupa Password? Hubungi IC Dwi</a>', unsafe_allow_html=True)
        
        with tab_up:
            with st.form("frm_daftar"):
                nu, np = st.text_input("Username Baru").strip(), st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar Sekarang", use_container_width=True):
                    if nu and np:
                        if get_json_direct(get_user_id(nu)): st.error("Username sudah terdaftar!")
                        else:
                            if upload_json({"username": nu, "password": hash_pass(np)}, get_user_id(nu)):
                                st.success("Akun berhasil dibuat! Silakan login.")
                    else: st.warning("Lengkapi data.")

# --- 6. HALAMAN UTAMA ---
def halaman_utama():
    with st.sidebar:
        st.success(f"Login: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"): st.session_state['user_login'] = None; st.rerun()

    st.title("🏭 Sistem Rusak Pabrik")
    menu = st.radio("Menu:", ["📝 Input Laporan", "🔐 Menu Admin"], horizontal=True)
    st.divider()

    if menu == "📝 Input Laporan":
        with st.container(border=True):
            c1, c2 = st.columns(2)
            kode, nrb = c1.text_input("Kode Toko", max_chars=4).upper(), c2.text_input("Nomor NRB")
            tgl, foto = st.date_input("Tanggal NRB"), st.file_uploader("Upload Foto BA", type=['jpg','png','jpeg'])
            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if kode and nrb and foto:
                    with st.spinner("Mengirim..."):
                        tgl_s, bln = tgl.strftime("%d%m%Y"), datetime.now().strftime("%Y-%m")
                        nama_f = f"{kode}_{nrb.replace(' ', '_')}_{tgl_s}_{random.randint(100,999)}"
                        res = cloudinary.uploader.upload(foto, public_id=f"{FOTO_FOLDER}/{bln}/{nama_f}", transformation=[{'width': 1000, 'quality': 'auto'}])
                        entri = {
                            "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Bulan_Upload": bln, "User": st.session_state['user_login'],
                            "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": res.get('secure_url')
                        }
                        data_db = get_json_direct(DATA_DB_PATH) or []
                        data_db.append(entri)
                        if upload_json(data_db, DATA_DB_PATH):
                            st.toast("Upload BA Berhasil!", icon="✅")
                            time.sleep(2); st.rerun()
                else: st.warning("Lengkapi data.")

    elif menu == "🔐 Menu Admin":
        if not st.session_state.get('admin_unlocked'):
            pw = st.text_input("Admin Password", type="password")
            if st.button("Buka Panel"):
                if pw == ADMIN_PASSWORD_ACCESS: st.session_state['admin_unlocked'] = True; st.rerun()
        else:
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            t1, t2, t3 = st.tabs(["📊 Laporan", "👥 User & Log", "🚀 Migrasi"])
            
            with t1:
                all_data = get_json_direct(DATA_DB_PATH)
                if all_data:
                    df = pd.DataFrame(all_data).sort_values(by="Waktu_Input", ascending=False)
                    c1, c2 = st.columns(2)
                    ft, fn = c1.text_input("Cari Kode Toko:"), c2.text_input("Cari No NRB:")
                    if ft: df = df[df['Kode_Toko'].str.contains(ft.upper(), na=False)]
                    if fn: df = df[df['No_NRB'].str.contains(fn, na=False)]
                    
                    # Tampilkan Data
                    for idx, row in df.iterrows():
                        with st.container(border=True):
                            ci, cd, c_del = st.columns([1, 3, 1.2])
                            ci.image(row['Foto'], width=150)
                            cd.write(f"**{row['Kode_Toko']} - NRB {row['No_NRB']}**")
                            cd.caption(f"User: {row['User']} | Tgl: {row['Tanggal_NRB']}")
                            
                            # Fix Syntax Error
                            clean_n = f"{row['Kode_Toko']}_{row['No_NRB']}_{row['Tanggal_NRB']}"
                            dl_link = row['Foto'].replace('/upload/', f'/upload/fl_attachment:{clean_n}/')
                            cd.markdown(f"[📥 Download Foto]({dl_link})")
                            
                            # --- INLINE CONFIRMATION DELETE (FIX DUPLICATE KEY) ---
                            del_key = f"del_confirm_{idx}_{row['Waktu_Input']}"
                            if st.session_state.get(del_key):
                                c_del.warning("Hapus?")
                                if c_del.button("YA", key=f"yes_{idx}", use_container_width=True):
                                    if hapus_satu_file(row['Waktu_Input'], row['Foto']):
                                        st.session_state[del_key] = False
                                        st.toast("Berhasil Dihapus!")
                                        time.sleep(1); st.rerun()
                                if c_del.button("BATAL", key=f"no_{idx}", use_container_width=True):
                                    st.session_state[del_key] = False; st.rerun()
                            else:
                                if c_del.button("🗑️ Hapus", key=f"btn_{idx}", use_container_width=True):
                                    st.session_state[del_key] = True; st.rerun()
                    
                    # --- TOMBOL DOWNLOAD CSV LAPORAN (RESTORED) ---
                    st.divider()
                    st.download_button("📥 Download Rekap Laporan (CSV)", df.to_csv(index=False), "Rekap_Laporan_Rusak_Pabrik.csv", "text/csv", use_container_width=True)
                else: st.info("Tidak ada data.")

            with t2:
                col_reset, col_log = st.columns([1, 1.5])
                with col_reset:
                    st.write("#### 🛠️ Reset Password")
                    u_target, p_new = st.text_input("Username"), st.text_input("Pass Baru", type="password")
                    if st.button("Update Password"):
                        if upload_json({"username": u_target, "password": hash_pass(p_new)}, get_user_id(u_target)):
                            st.success("Berhasil!"); st.rerun()
                with col_log:
                    st.write("#### 🕵️ Monitoring Akses")
                    log_data = get_json_direct(LOG_DB_PATH)
                    if log_data:
                        l_list = [{"Tanggal": t, "User": u, "Akses": c} for t, us in log_data.items() for u, c in us.items()]
                        df_log = pd.DataFrame(l_list).sort_values(by="Tanggal", ascending=False)
                        st.dataframe(df_log, use_container_width=True, hide_index=True)
                        st.download_button("📥 Download Log Akses (CSV)", df_log.to_csv(index=False), "Log_Akses_Rusak_Pabrik.csv", "text/csv", use_container_width=True)

            with t3:
                # Migrasi
                if st.button("MIGRASI USER LAMA"):
                    old = get_json_direct(OLD_USER_DB)
                    if old:
                        for u, h in old.items(): upload_json({"username": u, "password": h}, get_user_id(u))
                        st.success("User Selesai!"); st.rerun()
                st.divider()
                if st.button("MIGRASI FOTO DI CLOUD"):
                    with st.spinner("Sinkronisasi..."):
                        s, p = migrasi_foto_cloud()
                        if s: st.success(p)
                        else: st.error(p)

if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
