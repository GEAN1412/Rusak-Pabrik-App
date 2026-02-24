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
    div[data-testid="stForm"] button { background-color: #28a745 !important; color: white !important; font-weight: bold !important; }
    .plain-link { display: block; text-align: center; margin-top: 15px; color: #888888; text-decoration: none; font-size: 0.9em; cursor: pointer; }
    .plain-link:hover { color: #28a745; text-decoration: underline; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KONFIGURASI PATH & LINK ---
USER_FOLDER = "RusakPabrikApp/Users"
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity_rusak_pabrik.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "icnbr034"  
NAMA_FILE_PDF = "format_ba.pdf"

# [PENTING] GANTI LINK INI DENGAN LINK FOTO CONTOH DI CLOUDINARY ANDA
URL_CONTOH_FOTO_BA = "https://res.cloudinary.com/ddtgzywhh/image/upload/v1771939732/Format_Upload_BA_Yang_Benar_z6mwxt.jpg" 

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
    try:
        data_lama = get_json_direct(DATA_DB_PATH) or []
        data_baru = [d for d in data_lama if d.get('Waktu_Input') != timestamp_id]
        upload_json(data_baru, DATA_DB_PATH)
        if "upload/" in url_foto:
            try:
                p_id = url_foto.split("/upload/")[1].split("/", 1)[1].rsplit(".", 1)[0]
                cloudinary.uploader.destroy(p_id)
            except: pass
        return True
    except: return False

def hapus_data_bulanan(bulan_target):
    try:
        all_data = get_json_direct(DATA_DB_PATH) or []
        data_tetap = [d for d in all_data if d.get('Bulan_Upload') != bulan_target]
        prefix = f"{FOTO_FOLDER}/{bulan_target}/"
        cloudinary.api.delete_resources_by_prefix(prefix)
        try: cloudinary.api.delete_folder(prefix)
        except: pass
        upload_json(data_tetap, DATA_DB_PATH)
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
                k = parts[0] if len(parts) > 0 else "MISC"
                n = parts[1] if len(parts) > 1 else "NRB"
                t = parts[2] if len(parts) > 2 else "20260101"
                current_data.append({
                    "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Bulan_Upload": datetime.now().strftime("%Y-%m"),
                    "User": "Auto_Migrator", "Kode_Toko": k, "No_NRB": n, "Tanggal_NRB": t, "Foto": url
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
                        st.balloons()
                        st.toast(f"Selamat datang, {u}!", icon="👋")
                        time.sleep(2.5); st.rerun()
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
    menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin (Rekap)"], horizontal=True)
    st.divider()

    # --- MENU INPUT LAPORAN ---
    if menu == "📝 Input Laporan Baru":
        
        # Fitur PDF
        with st.expander("📄 Download / Lihat File PDF Format BA"):
            if os.path.exists(NAMA_FILE_PDF):
                with open(NAMA_FILE_PDF, "rb") as pdf_file:
                    PDFbyte = pdf_file.read()
                st.download_button(label="📥 Download Format BA (PDF)", data=PDFbyte, file_name="Format_BA.pdf", mime="application/pdf", use_container_width=True)
                
                base64_pdf = base64.b64encode(PDFbyte).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.warning("⚠️ File PDF belum diupload ke GitHub.")

        st.write("")
        st.subheader("Formulir Upload")

        # Pesan Sukses Persistent
        if 'pesan_sukses' in st.session_state and st.session_state['pesan_sukses']:
            st.success(st.session_state['pesan_sukses'])
            
        if 'form_key' not in st.session_state: st.session_state['form_key'] = 0
        key_now = st.session_state['form_key']

        with st.container(border=True):
            c1, c2 = st.columns(2)
            kode = c1.text_input("Kode Toko", max_chars=4, key=f"k_{key_now}").upper()
            nrb = c2.text_input("Nomor NRB", key=f"n_{key_now}")
            tgl = st.date_input("Tanggal NRB", key=f"t_{key_now}")
            
            st.markdown("---")
            
            # --- [FITUR BARU] CONTOH FOTO ---
            # Diletakkan di atas tombol upload agar terlihat user
            with st.expander("🖼️ Lihat Contoh Foto BA yang Benar (Klik disini)"):
                c_ex_img, c_ex_txt = st.columns([1, 1])
                with c_ex_img:
                    # Gambar dari Link Cloudinary
                    st.image(URL_CONTOH_FOTO_BA, caption="Contoh Upload BA Rusak Pabrik Yang Benar!", use_container_width=True)
                with c_ex_txt:
                    st.info("Pastikan foto terlihat jelas, tidak blur, dan mencakup seluruh halaman Berita Acara dan keterangan diisi semua!.")

            st.write("") # Spasi
            foto = st.file_uploader("Upload Foto BA", type=['jpg','png','jpeg'], key=f"f_{key_now}")
            
            # Live Preview
            if foto:
                st.info(f"Foto '{foto.name}' siap diupload.")
                with st.expander("Lihat Preview Foto Anda"): st.image(foto, width=200)

            if st.button("Kirim Laporan", type="primary", use_container_width=True):
                st.session_state['pesan_sukses'] = None
                
                if kode and nrb and foto:
                    with st.spinner("Mengirim..."):
                        try:
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
                            upload_json(data_db, DATA_DB_PATH)
                            
                            st.balloons()
                            st.session_state['pesan_sukses'] = f"✅ Berhasil! NRB {nrb} dari {kode} tersimpan."
                            st.session_state['form_key'] += 1
                            time.sleep(3)
                            st.rerun()
                            
                        except Exception as e: st.error(f"Gagal: {e}")
                else: st.warning("Lengkapi data.")

    # --- MENU ADMIN ---
    elif menu == "🔐 Menu Admin (Rekap)":
        if not st.session_state.get('admin_unlocked'):
            pw = st.text_input("Admin Password", type="password")
            if st.button("Buka Panel"):
                if pw == ADMIN_PASSWORD_ACCESS: st.session_state['admin_unlocked'] = True; st.rerun()
        else:
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            t1, t2, t3 = st.tabs(["📊 Laporan & Filter", "👥 User & Log", "🚀 Migrasi"])
            
            with t1:
                all_data = get_json_direct(DATA_DB_PATH)
                if all_data:
                    df = pd.DataFrame(all_data)
                    df['Tanggal_Obj'] = pd.to_datetime(df['Tanggal_NRB'], errors='coerce').dt.date
                    df = df.sort_values(by="Waktu_Input", ascending=False)
                    
                    st.markdown("### 🔍 Filter Data")
                    col_d1, col_d2 = st.columns(2)
                    today = datetime.now().date()
                    start_def = today.replace(day=1)
                    
                    with col_d1: start_date = st.date_input("Dari Tanggal:", value=start_def)
                    with col_d2: end_date = st.date_input("Sampai Tanggal:", value=today)

                    c1, c2 = st.columns(2)
                    ft, fn = c1.text_input("Cari Kode Toko:"), c2.text_input("Cari No NRB:")
                    
                    mask = (df['Tanggal_Obj'] >= start_date) & (df['Tanggal_Obj'] <= end_date)
                    if ft: mask &= df['Kode_Toko'].str.contains(ft.upper(), na=False)
                    if fn: mask &= df['No_NRB'].str.contains(fn, na=False)
                    
                    df_filtered = df[mask]
                    st.info(f"📋 Ditemukan {len(df_filtered)} data (Periode: {start_date} s.d {end_date})")
                    
                    for idx, row in df_filtered.head(5).iterrows():
                        with st.container(border=True):
                            ci, cd, c_del = st.columns([1, 3, 1.2])
                            ci.image(row['Foto'], width=150)
                            cd.write(f"**{row['Kode_Toko']} - NRB {row['No_NRB']}**")
                            cd.caption(f"User: {row['User']} | Tgl: {row['Tanggal_NRB']}")
                            cl_n = f"{row['Kode_Toko']}_{row['No_NRB']}_{row['Tanggal_NRB']}"
                            dl_l = row['Foto'].replace('/upload/', f'/upload/fl_attachment:{cl_n}/')
                            cd.markdown(f"[📥 Download Foto]({dl_l})")
                            
                            k_c = f"del_confirm_{idx}_{row['Waktu_Input']}"
                            if st.session_state.get(k_c):
                                c_del.warning("Hapus?")
                                if c_del.button("YA", key=f"y_{idx}"):
                                    if hapus_satu_file(row['Waktu_Input'], row['Foto']):
                                        st.session_state[k_c] = False; st.success("Terhapus!"); time.sleep(2); st.rerun()
                                if c_del.button("TIDAK", key=f"n_{idx}"):
                                    st.session_state[k_c] = False; st.rerun()
                            else:
                                if c_del.button("🗑️", key=f"b_{idx}"):
                                    st.session_state[k_c] = True; st.rerun()
                    
                    st.divider()
                    fname = f"Rekap_{start_date}_sd_{end_date}.csv"
                    st.download_button(f"📥 Download Rekap CSV ({len(df_filtered)} Data)", df_filtered.drop(columns=['Tanggal_Obj']).to_csv(index=False), fname, "text/csv", use_container_width=True)
                    
                    with st.expander("🚨 Hapus Data Bulanan"):
                        list_bln = sorted(list(set(df['Bulan_Upload'].tolist())), reverse=True)
                        target_bln = st.selectbox("Pilih Bulan Upload:", list_bln)
                        if st.button(f"🔥 Mulai Hapus Bulan {target_bln}"):
                            st.session_state['confirm_bln'] = True
                        
                        if st.session_state.get('confirm_bln'):
                            st.error(f"⚠️ Yakin hapus data bulan {target_bln}?")
                            pass_input = st.text_input("Password:", type="password", key="pass_bulk")
                            if st.button("YA, SAYA YAKIN"):
                                if pass_input == "123456":
                                    if hapus_data_bulanan(target_bln):
                                        st.session_state['confirm_bln'] = False; st.success("Terhapus!"); time.sleep(2); st.rerun()
                                else: st.error("Salah!")
                            if st.button("BATAL"): st.session_state['confirm_bln'] = False; st.rerun()
                else: st.info("Tidak ada data.")

            with t2:
                col_r, col_l = st.columns([1, 1.5])
                with col_r:
                    st.write("#### 🛠️ Reset Password")
                    ut, pn = st.text_input("Username"), st.text_input("Pass Baru", type="password")
                    if st.button("Update Password"):
                        if ut and pn:
                            if get_json_direct(get_user_id(ut)):
                                upload_json({"username": ut, "password": hash_pass(pn)}, get_user_id(ut))
                                st.success("Ubah password sukses"); time.sleep(2); st.rerun()
                            else: st.error("User tidak ditemukan!")
                        else: st.warning("Lengkapi data.")

                with col_l:
                    st.write("#### 🕵️ Monitoring Akses")
                    ld = get_json_direct(LOG_DB_PATH)
                    if ld:
                        l_list = [{"Tanggal": t, "User": u, "Akses": c} for t, us in ld.items() for u, c in us.items()]
                        df_l = pd.DataFrame(l_list).sort_values(by="Tanggal", ascending=False)
                        st.dataframe(df_l, use_container_width=True, hide_index=True)
                        st.download_button("📥 Download Log CSV", df_l.to_csv(index=False), "Log_Akses.csv", "text/csv", use_container_width=True)
                    else: st.info("Belum ada log.")

            with t3:
                st.write("#### 🚀 Migrasi Sistem")
                if st.button("MIGRASI USER LAMA"):
                    old = get_json_direct(OLD_USER_DB)
                    if old:
                        for u, h in old.items(): upload_json({"username": u, "password": h}, get_user_id(u))
                        st.success("Migrasi User Selesai!"); st.rerun()
                st.divider()
                if st.button("MIGRASI FOTO DI CLOUD"):
                    with st.spinner("Sinkronisasi..."):
                        s, p = migrasi_foto_cloud()
                        if s: st.success(p); time.sleep(3); st.rerun()
                        else: st.error(p)

if __name__ == "__main__":
    init_cloudinary()
    if 'user_login' not in st.session_state: st.session_state['user_login'] = None
    if st.session_state['user_login'] is None: halaman_login()
    else: halaman_utama()
