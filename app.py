import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
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
DATA_DB_PATH = "RusakPabrikApp/data_laporan_rusak_pabrik.json"
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


# --- 5. HALAMAN UTAMA (APLIKASI) ---
def main():
    init_cloudinary()
    
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
            
            with st.expander("🖼️ Lihat Contoh Foto BA yang Benar (Klik disini)"):
                c_ex_img, c_ex_txt = st.columns([1, 1])
                with c_ex_img:
                    st.image(URL_CONTOH_FOTO_BA, caption="Contoh Upload BA Rusak Pabrik Yang Benar!", use_container_width=True)
                with c_ex_txt:
                    st.info("Pastikan foto terlihat jelas, tidak blur, dan mencakup seluruh halaman Berita Acara dan keterangan diisi semua!.Jika BA ditulis manual pastikan sesuai contoh format BA!")

            st.write("")
            foto = st.file_uploader("Upload Foto BA dibawah, pastikan sesuai dengan contoh diatas!Pastikan Fisik BA, NRB, Fisik Dikirim ke DC!", type=['jpg','png','jpeg'], key=f"f_{key_now}")
            
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
                                "Bulan_Upload": bln, 
                                "User": "Anonim", # Disesuaikan karena login dihilangkan
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
            if st.button("🔒 Logout Admin"): st.session_state['ad
