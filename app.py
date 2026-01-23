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

# --- 2. CSS & STYLE (Sesuai Asli) ---
hide_st_style = """
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
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. KONFIGURASI DATABASE (Updated Names) ---
USER_DB_PATH = "RusakPabrikApp/users_rusak_pabrik.json"
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_rusak_pabrik.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "icnbr034"  
NAMA_FILE_PDF = "format_ba_rusak_pabrik.pdf"

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

def get_json_fresh(public_id, retries=3):
    for i in range(retries):
        try:
            resource = cloudinary.api.resource(public_id, resource_type="raw")
            url = resource.get('secure_url')
            if url:
                url_fresh = f"{url}?t={int(time.time())}_{random.randint(1,99999)}"
                resp = requests.get(url_fresh, timeout=10)
                if resp.status_code == 200: return resp.json()
                elif resp.status_code == 404: return {}
        except:
            time.sleep(1)
            continue
    return None

def upload_json(data_obj, public_id):
    if data_obj is None: return 
    json_data = json.dumps(data_obj)
    cloudinary.uploader.upload(
        io.BytesIO(json_data.encode('utf-8')), 
        resource_type="raw", 
        public_id=public_id,
        overwrite=True,
        invalidate=True
    )

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def catat_login_activity(username):
    try:
        log_data = get_json_fresh(LOG_DB_PATH)
        if log_data is None: return
        now = datetime.utcnow() + timedelta(hours=8)
        tanggal_str = now.strftime("%Y-%m-%d")
        if not isinstance(log_data, dict): log_data = {}
        if tanggal_str not in log_data: log_data[tanggal_str] = {}
        if username not in log_data[tanggal_str]: log_data[tanggal_str][username] = 0
        log_data[tanggal_str][username] += 1
        upload_json(log_data, LOG_DB_PATH)
    except: pass

# --- MERGE LOGIC (Kunci Keamanan Data) ---
def simpan_laporan_aman(entri_baru):
    max_retries = 5
    for i in range(max_retries):
        try:
            data_lama = get_json_fresh(DATA_DB_PATH)
            if data_lama is None:
                time.sleep(random.uniform(0.5, 1.5))
                continue
            if not isinstance(data_lama, list): data_lama = []
            
            # ATOMIC APPEND: Gabungkan data cloud terbaru dengan input user
            data_lama.append(entri_baru)
            upload_json(data_lama, DATA_DB_PATH)
            return True, "Sukses"
        except Exception as e:
            time.sleep(random.uniform(0.5, 2.0))
            if i == max_retries - 1: return False, f"Gagal simpan: {e}"
    return False, "Server sibuk."

def hapus_satu_file(timestamp_id, url_foto):
    try:
        data_lama = get_json_fresh(DATA_DB_PATH)
        if data_lama is None: return False
        if isinstance(data_lama, list):
            data_baru = [d for d in data_lama if d.get('Waktu_Input') != timestamp_id]
            upload_json(data_baru, DATA_DB_PATH)
        if "upload/" in url_foto:
            try:
                public_id = url_foto.split("/upload/")[1].split("/")[1].rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
            except: pass
        return True
    except: return False

def hapus_data_bulan_tertentu(bulan_target):
    try:
        prefix_folder = f"{FOTO_FOLDER}/{bulan_target}/"
        cloudinary.api.delete_resources_by_prefix(prefix_folder, resource_type="image")
        try: cloudinary.api.delete_folder(prefix_folder)
        except: pass 
        data_lama = get_json_fresh(DATA_DB_PATH)
        if data_lama is None: return False, "Gagal konek."
        if isinstance(data_lama, list):
            data_baru = [d for d in data_lama if d.get('Bulan_Upload') != bulan_target]
            upload_json(data_baru, DATA_DB_PATH)
        return True, f"Data bulan {bulan_target} terhapus."
    except Exception as e: return False, str(e)

# --- 5. LOGIKA HALAMAN ---
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
                    db_cloud = get_json_fresh(USER_DB_PATH)
                    if db_cloud and u in db_cloud and db_cloud[u] == hash_pass(p):
                        st.session_state['user_login'] = u
                        catat_login_activity(u)
                        st.success("Login Berhasil!")
                        time.sleep(0.5); st.rerun()
                    else: st.error("Salah Username/Password!")
            st.markdown(f'<a href="https://wa.me/6283114444424" class="plain-link">❓ Lupa Password? Hubungi Admin</a>', unsafe_allow_html=True)
        with tab_up:
            with st.form("frm_daftar"):
                nu = st.text_input("Username Baru (Kode Toko)")
                np = st.text_input("Password Baru", type="password")
                if st.form_submit_button("Daftar", use_container_width=True):
                    db = get_json_fresh(USER_DB_PATH)
                    if db is not None:
                        if nu in db: st.error("User sudah ada.")
                        else:
                            db[nu] = hash_pass(np)
                            upload_json(db, USER_DB_PATH)
                            st.session_state['user_login'] = nu
                            catat_login_activity(nu); st.rerun()

def halaman_utama():
    with st.sidebar:
        st.header("👤 User Panel")
        st.success(f"User: **{st.session_state['user_login']}**")
        if st.button("🚪 Logout"):
            st.session_state['user_login'] = None; st.rerun()
        st.caption("Monitoring IC Bali")

    st.title("🏭 Sistem Rusak Pabrik")
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin (Rekap)"], horizontal=True)
    st.divider()

    if menu == "📝 Input Laporan Baru":
        with st.expander("📄 Lihat Format BA Rusak Pabrik (PDF)"):
            if os.path.exists(NAMA_FILE_PDF):
                with open(NAMA_FILE_PDF, "rb") as f:
                    PDFbyte = f.read()
                st.download_button("📥 Download PDF", PDFbyte, NAMA_FILE_PDF, "application/pdf", use_container_width=True)
                base64_pdf = base64.b64encode(PDFbyte).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>', unsafe_allow_html=True)

        if 'pesan_sukses' in st.session_state: st.success(st.session_state['pesan_sukses'])
        if 'form_key' not in st.session_state: st.session_state['form_key'] = 0
        
        with st.container(border=True):
            k = st.text_input("Kode Toko", max_chars=4, key=f"k_{st.session_state['form_key']}").upper()
            n = st.text_input("Nomor NRB", key=f"n_{st.session_state['form_key']}")
            t = st.date_input("Tanggal NRB", key=f"t_{st.session_state['form_key']}")
            f = st.file_uploader("Upload Foto", type=['jpg','png','jpeg'], key=f"f_{st.session_state['form_key']}")
            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                if k and n and f:
                    with st.spinner("Mengirim..."):
                        t_s = t.strftime("%d%m%Y")
                        bln = datetime.now().strftime("%Y-%m")
                        path = f"{FOTO_FOLDER}/{bln}/{k}_{n}_{t_s}_{random.randint(100,999)}"
                        res = cloudinary.uploader.upload(f, public_id=path, transformation=[{'width':1000,'crop':'limit'},{'quality':'auto:eco'}])
                        entri = {"Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Bulan_Upload": bln, "User": st.session_state['user_login'], "Kode_Toko": k, "No_NRB": n, "Tanggal_NRB": str(t), "Foto": res.get('secure_url')}
                        ok, msg = simpan_laporan_aman(entri)
                        if ok: 
                            st.session_state['pesan_sukses'] = f"✅ Sukses NRB {n}"; st.session_state['form_key'] += 1; st.rerun()
                        else: st.error(msg)
                else: st.warning("Data tidak lengkap!")

    elif menu == "🔐 Menu Admin (Rekap)":
        if not st.session_state.get('admin_unlocked'):
            pw = st.text_input("Password Admin:", type="password")
            if st.button("Masuk Admin"):
                if pw == ADMIN_PASSWORD_ACCESS: st.session_state['admin_unlocked'] = True; st.rerun()
                else: st.error("Salah!")
        else:
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            t1, t2 = st.tabs(["🏭 Laporan", "👥 User & Log"])
            with t1:
                all_d = get_json_fresh(DATA_DB_PATH)
                if isinstance(all_d, list) and all_d:
                    df = pd.DataFrame(all_d)
                    c_a, c_b = st.columns(2)
                    f_k = c_a.text_input("Filter Toko:")
                    f_n = c_b.text_input("Filter NRB:")
                    mask = pd.Series([True]*len(df))
                    if f_k: mask &= df['Kode_Toko'].str.contains(f_k.upper())
                    if f_n: mask &= df['No_NRB'].str.contains(f_n)
                    df_res = df[mask].sort_values(by="Waktu_Input", ascending=False)
                    st.dataframe(df_res, use_container_width=True)
                    
                    # FITUR HAPUS PER BARIS (Sama seperti asli kamu)
                    for idx, row in df_res.head(10).iterrows():
                        with st.expander(f"Kelola: {row['Kode_Toko']} - {row['No_NRB']}"):
                            st.image(row['Foto'], width=200)
                            if st.button(f"Hapus Permanen", key=f"del_{idx}"):
                                if hapus_satu_file(row['Waktu_Input'], row['Foto']):
                                    st.success("Terhapus!"); time.sleep(1); st.rerun()
                    
                    csv = df_res.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Rekap Rusak Pabrik (CSV)", csv, "Rekap_Rusak_Pabrik.csv", "text/csv")
                else: st.info("Kosong.")
            with t2:
                # BAGIAN MONITORING AKSES (Seperti asli)
                log_d = get_json_fresh(LOG_DB_PATH)
                if log_d:
                    l_list = [{"Tanggal": t, "User": u, "Akses": c} for t, usrs in log_d.items() for u, c in usrs.items()]
                    st.table(pd.DataFrame(l_list).sort_values(by="Tanggal", ascending=False))

if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
