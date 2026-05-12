import streamlit as st
import pandas as pd
import os
import base64
import time
import random
from datetime import datetime
import cloudinary
import cloudinary.uploader

# --- CONFIGURASI & CSS ---
st.set_page_config(page_title="Sistem Rusak Pabrik", layout="centered", page_icon="🏭")

# Contoh CSS (Silakan sesuaikan jika Anda punya CSS spesifik sebelumnya)
st.markdown("""
    <style>
    .stApp { background-color: #f5f7f9; }
    .stButton>button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- KONSTANTA (Pastikan variabel ini sesuai dengan file Anda) ---
# Jika variabel ini di tempat lain, pastikan di-import. Jika tidak, definisikan di sini:
NAMA_FILE_PDF = "format_ba.pdf"
URL_CONTOH_FOTO_BA = "URL_GAMBAR_ANDA_DISINI"
DATA_DB_PATH = "data_laporan.json"
LOG_DB_PATH = "log_akses.json"
FOTO_FOLDER = "folder_foto_ba"
ADMIN_PASSWORD_ACCESS = "password_anda"

# --- FUNGSI HELPER (Pastikan fungsi ini sudah terdefinisi di file Anda) ---
# (get_json_direct, upload_json, hapus_satu_file, hapus_data_bulanan, migrasi_foto_cloud)
# Saya berasumsi fungsi-fungsi ini sudah ada di skrip Anda sebelumnya.

# --- MAIN APP ---
st.title("🏭 Sistem Rusak Pabrik")
menu = st.radio("Menu:", ["📝 Input Laporan Baru", "🔐 Menu Admin (Rekap)"], horizontal=True)
st.divider()

# --- MENU INPUT LAPORAN ---
if menu == "📝 Input Laporan Baru":
    
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
                st.info("Pastikan foto terlihat jelas, tidak blur, dan mencakup seluruh halaman Berita Acara dan keterangan diisi semua!")

        st.write("") 
        foto = st.file_uploader("Upload Foto BA dibawah, pastikan sesuai dengan contoh diatas!", type=['jpg','png','jpeg'], key=f"f_{key_now}")
        
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
                            "Bulan_Upload": bln, "Kode_Toko": kode, "No_NRB": nrb, "Tanggal_NRB": str(tgl), "Foto": res.get('secure_url')
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
        
        t1, t2 = st.tabs(["📊 Laporan & Filter", "🚀 Migrasi"])
        
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
                        cd.caption(f"Tgl: {row['Tanggal_NRB']}")
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
            st.write("#### 🚀 Migrasi Sistem")
            if st.button("MIGRASI FOTO DI CLOUD"):
                with st.spinner("Sinkronisasi..."):
                    s, p = migrasi_foto_cloud()
                    if s: st.success(p); time.sleep(3); st.rerun()
                    else: st.error(p)
