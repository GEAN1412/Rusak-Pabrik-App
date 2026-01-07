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
import os # Wajib ada untuk baca file lokal
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Rusak Pabrik IC Bali", 
    layout="wide", 
    page_icon="🏭"
)

# --- 2. CSS & STYLE ---
hide_st_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden; display: none !important;}
            [data-testid="stDecoration"] {visibility: hidden; display: none !important;}
            footer {visibility: hidden; display: none;}
            .main .block-container {padding-top: 2rem;}
            
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

# --- 3. KONFIGURASI DATABASE ---
USER_DB_PATH = "RusakPabrikApp/users.json"
DATA_DB_PATH = "RusakPabrikApp/data_laporan.json"
LOG_DB_PATH = "RusakPabrikApp/user_activity.json"
FOTO_FOLDER = "RusakPabrikApp/Foto"
ADMIN_PASSWORD_ACCESS = "icnbr034" 

# NAMA FILE PDF LOKAL (Harus sama persis dengan yang diupload ke GitHub)
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

def get_json_fresh(public_id):
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
    json_data = json.dumps(data_obj)
    cloudinary.uploader.upload(
        io.BytesIO(json_data.encode('utf-8')), 
        resource_type="raw", 
        public_id=public_id,
        overwrite=True
    )

def hash_pass(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def catat_login_activity(username):
    try:
        log_data = get_json_fresh(LOG_DB_PATH)
        now = datetime.utcnow() + timedelta(hours=8)
        tanggal_str = now.strftime("%Y-%m-%d")
        if tanggal_str not in log_data: log_data[tanggal_str] = {}
        if username not in log_data[tanggal_str]: log_data[tanggal_str][username] = 0
        log_data[tanggal_str][username] += 1
        upload_json(log_data, LOG_DB_PATH)
    except: pass

def simpan_laporan_aman(entri_baru):
    max_retries = 3
    for i in range(max_retries):
        try:
            data_lama = get_json_fresh(DATA_DB_PATH)
            if not isinstance(data_lama, list): data_lama = []
            data_lama.append(entri_baru)
            upload_json(data_lama, DATA_DB_PATH)
            return True, "Sukses"
        except Exception as e:
            time.sleep(random.uniform(0.5, 2.0))
            if i == max_retries - 1:
                return False, f"Gagal menyimpan: {e}"
    return False, "Unknown Error"

def hapus_satu_file(timestamp_id, url_foto):
    try:
        data_lama = get_json_fresh(DATA_DB_PATH)
        if isinstance(data_lama, list):
            data_baru = [d for d in data_lama if d.get('Waktu_Input') != timestamp_id]
            upload_json(data_baru, DATA_DB_PATH)
        
        if "upload/" in url_foto:
            try:
                parts = url_foto.split("/upload/")
                version_path = parts[1] 
                path_only = "/".join(version_path.split("/")[1:]) 
                public_id = path_only.rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
            except: pass
        return True
    except: return False

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
                    with st.spinner("Cek akun..."):
                        db = get_json_fresh(USER_DB_PATH)
                        ph = hash_pass(p)
                        if u in db and db[u] == ph:
                            st.session_state['user_login'] = u
                            catat_login_activity(u)
                            st.rerun()
                        else: st.error("Username atau Password Salah!")
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
                            if nu in db: st.error("Username sudah dipakai.")
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
        
        # --- PDF DARI GITHUB LOKAL (LEBIH STABIL) ---
        with st.expander("📄 Download / Lihat Format BA Rusak Pabrik (PDF)"):
            # Cek apakah file ada di folder aplikasi (GitHub)
            if os.path.exists(NAMA_FILE_PDF):
                with open(NAMA_FILE_PDF, "rb") as pdf_file:
                    PDFbyte = pdf_file.read()

                # Tombol Download
                st.download_button(
                    label="📥 Download Format BA (PDF)",
                    data=PDFbyte,
                    file_name="Format_BA_Rusak_Pabrik.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                # Preview di Web
                base64_pdf = base64.b64encode(PDFbyte).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ File '{NAMA_FILE_PDF}' belum ditemukan. Harap Admin upload file PDF ke GitHub dengan nama tersebut.")

        st.write("") 
        st.subheader("Formulir Upload")
        
        if 'pesan_sukses' in st.session_state and st.session_state['pesan_sukses']:
            st.success(st.session_state['pesan_sukses'])
            
        if 'form_key' not in st.session_state: st.session_state['form_key'] = 0
        key_now = st.session_state['form_key']
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1: kode = st.text_input("Kode Toko (4 Digit)", max_chars=4, placeholder="CTH: F08C", key=f"kode_{key_now}").upper()
            with c2: nrb = st.text_input("Nomor NRB", placeholder="Nomor Dokumen", key=f"nrb_{key_now}")
            
            tgl = st.date_input("Tanggal NRB", key=f"tgl_{key_now}")
            st.markdown("---")
            foto = st.file_uploader("Upload Foto BA", type=['jpg', 'jpeg', 'png'], key=f"foto_{key_now}")
            st.caption("ℹ️ Foto akan otomatis dikompres oleh sistem agar ringan.")
            
            kirim_btn = st.button("Kirim Laporan", type="primary", use_container_width=True)

        if kirim_btn:
            if 'pesan_sukses' in st.session_state: st.session_state['pesan_sukses'] = None

            if kode and nrb and foto:
                if len(kode) != 4: st.error("Kode Toko harus 4 digit!")
                else:
                    with st.spinner("Mengirim data..."):
                        try:
                            tgl_str = tgl.strftime("%d%m%Y")
                            bln_folder = datetime.now().strftime("%Y-%m")
                            nama_file = f"{kode}_{nrb}_{tgl_str}_{random.randint(100,999)}"
                            path_cloud = f"{FOTO_FOLDER}/{bln_folder}/{nama_file}"
                            
                            res = cloudinary.uploader.upload(foto, resource_type="image", public_id=path_cloud, overwrite=True, transformation=[{'width': 1000, 'crop': 'limit'}, {'quality': 'auto:eco'}])
                            url_foto = res.get('secure_url')
                            
                            entri = {
                                "Waktu_Input": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Bulan_Upload": bln_folder,
                                "User": st.session_state['user_login'],
                                "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": url_foto
                            }
                            
                            sukses, pesan = simpan_laporan_aman(entri)
                            if sukses:
                                st.session_state['pesan_sukses'] = f"✅ Berhasil! Laporan NRB {nrb} (Toko {kode}) telah tersimpan."
                                st.session_state['form_key'] += 1 
                                st.rerun()
                            else: st.error(pesan)
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
            if st.button("🔒 Logout Admin"): st.session_state['admin_unlocked'] = False; st.rerun()
            st.markdown("---")
            
            tab_data, tab_user = st.tabs(["🏭 Cek & Hapus Laporan", "👥 Kelola User & Monitoring"])
            
            with tab_data:
                all_data = get_json_fresh(DATA_DB_PATH)
                if isinstance(all_data, list) and all_data:
                    df_all = pd.DataFrame(all_data)
                    
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1: filter_toko = st.text_input("Cari Kode Toko:")
                    with c2: filter_nrb = st.text_input("Cari No NRB:")
                    with c3: filter_bln = st.text_input("Cari Bulan (YYYY-MM):")
                    
                    mask = pd.Series([True] * len(df_all))
                    if filter_toko: mask &= df_all['Kode_Toko'].str.contains(filter_toko.upper(), na=False)
                    if filter_nrb: mask &= df_all['No_NRB'].str.contains(filter_nrb.upper(), na=False)
                    if filter_bln: mask &= df_all['Bulan_Upload'].str.contains(filter_bln, na=False)
                    
                    df_show = df_all[mask].sort_values(by="Waktu_Input", ascending=False)
                    
                    is_searching = filter_toko or filter_nrb or filter_bln
                    if is_searching:
                        final_df = df_show
                        st.success(f"🔍 Ditemukan {len(final_df)} data.")
                    else:
                        final_df = df_show.head(5) 
                        st.info(f"📋 Menampilkan 5 Data Terbaru. Total: {len(df_all)} data.")

                    st.write("---")
                    
                    for idx, row in final_df.iterrows(): 
                        with st.container(border=True):
                            ci, cd, c_del = st.columns([1, 3, 1])
                            with ci: st.image(row['Foto'], width=150)
                            with cd:
                                st.write(f"**{row['Kode_Toko']} - NRB {row['No_NRB']}**")
                                st.caption(f"Tgl NRB: {row['Tanggal_NRB']} | Upload: {row['Waktu_Input']} | User: {row['User']}")
                                clean_name = f"{row['Kode_Toko']}_{row['No_NRB']}_{row['Tanggal_NRB']}"
                                dl_link = row['Foto'].replace("/upload/", f"/upload/fl_attachment:{clean_name}/")
                                st.markdown(f"[📥 Download Foto]({dl_link})")
                            with c_del:
                                unik_id = f"{idx}_{row['Waktu_Input']}"
                                if st.button(f"🗑️ Hapus", key=f"btn_del_{unik_id}"):
                                    st.session_state[f"confirm_{unik_id}"] = True
                                if st.session_state.get(f"confirm_{unik_id}"):
                                    st.markdown("<div class='delete-confirm'>⚠️ Hapus?</div>", unsafe_allow_html=True)
                                    if st.button("YA", key=f"yes_{unik_id}"):
                                        if hapus_satu_file(row['Waktu_Input'], row['Foto']):
                                            st.success("Terhapus!")
                                            time.sleep(1); st.rerun()
                                    if st.button("BATAL", key=f"no_{unik_id}"):
                                        st.session_state[f"confirm_{unik_id}"] = False; st.rerun()
                    st.markdown("---")
                    csv = df_show.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Rekap Data (CSV)", csv, "Rekap_Rusak_Pabrik.csv", "text/csv", use_container_width=True)
                    
                    with st.expander("🚨 Hapus Data Bulanan (Danger Zone)"):
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
                                time.sleep(2); st.rerun()
                        else: st.write("Tidak ada data.")
                else: st.warning("Belum ada data masuk sama sekali.")

            with tab_user:
                col_reset, col_log = st.columns(2)
                with col_reset:
                    st.markdown("#### 🛠️ Ganti Password User")
                    with st.container(border=True):
                        if st.button("🔄 Refresh List User"): st.rerun()
                        db_users = get_json_fresh(USER_DB_PATH)
                        if db_users:
                            list_user = sorted(list(db_users.keys()))
                            target_user = st.selectbox("Cari Username (Ketik):", list_user, index=None, placeholder="Ketik nama user...", key="sel_user_mgr")
                            new_pass_admin = st.text_input("Password Baru:", type="password", key="adm_new_pass")
                            if st.button("Simpan Password Baru", use_container_width=True):
                                if target_user and new_pass_admin:
                                    db_users[target_user] = hash_pass(new_pass_admin)
                                    upload_json(db_users, USER_DB_PATH)
                                    st.success(f"Password '{target_user}' diubah!")
                                    time.sleep(1); st.rerun()
                                elif not target_user: st.warning("Pilih user dulu.")
                                else: st.warning("Isi password dulu.")
                        else: st.info("Belum ada user.")

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
