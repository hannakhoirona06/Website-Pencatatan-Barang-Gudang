# ==================================================
# APLIKASI GUDANG QR - FINAL (BARCODE PER BARANG + EDIT/HAPUS)
# ==================================================
import streamlit as st
import pandas as pd
import qrcode
import cv2
import os
import numpy as np
import zipfile
from PIL import Image
from datetime import datetime


# ---------------- KONFIG ----------------
DATA_DIR = "data"
QR_DIR = "qr"
BARANG_CSV = os.path.join(DATA_DIR, "barang.csv")
TRANS_CSV = os.path.join(DATA_DIR, "transaksi.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

# ---------------- INIT ----------------
def init_files():
    if not os.path.exists(BARANG_CSV):
        pd.DataFrame(columns=["id","nama","harga","stok"]).to_csv(BARANG_CSV, index=False)
    if not os.path.exists(TRANS_CSV):
        pd.DataFrame(columns=["waktu","id","nama","qty","harga","subtotal","kode_trx"]).to_csv(TRANS_CSV, index=False)

def load_barang():
    return pd.read_csv(BARANG_CSV)

def save_barang(df):
    df.to_csv(BARANG_CSV, index=False)

def load_transaksi():
    return pd.read_csv(TRANS_CSV)

def save_transaksi(df):
    df.to_csv(TRANS_CSV, index=False)

def gen_id():
    return "BRG" + datetime.now().strftime("%Y%m%d%H%M%S")

def gen_qr(kode):
    img = qrcode.make(kode)
    path = os.path.join(QR_DIR, f"{kode}.png")
    img.save(path)
    return path

def ensure_qr_exists(kode):
    path = os.path.join(QR_DIR, f"{kode}.png")
    if not os.path.exists(path):
        gen_qr(kode)
    return path

def decode_qr(img_file):
    img = Image.open(img_file).convert("RGB")
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data if data else None


# ---------------- CART ----------------
def init_cart():
    if "cart" not in st.session_state:
        st.session_state.cart = []

def add_cart(item):
    for c in st.session_state.cart:
        if c["id"] == item["id"]:
            c["qty"] += item["qty"]
            c["subtotal"] = c["qty"] * c["harga"]
            return
    st.session_state.cart.append(item)

def clear_cart():
    st.session_state.cart = []


# ---------------- APP ----------------
st.set_page_config("Gudang QR Final", layout="centered")
init_files()
init_cart()

menu = st.sidebar.radio(
    "Menu",
    ["Input Barang", "Scan & Transaksi", "Manajemen Data", "Laporan"]
)

# ==================================================
# MENU 1 – INPUT BARANG
# ==================================================
if menu == "Input Barang":
    st.title("➕ Input Data Barang")

    df = load_barang()

    nama = st.text_input("Nama Barang")
    harga = st.number_input("Harga", min_value=0, step=1000)
    stok = st.number_input("Stok", min_value=0, step=1)

    if st.button("Simpan Barang"):
        if nama.strip() == "":
            st.warning("Nama wajib diisi")
        else:
            kode = gen_id()
            df = pd.concat([df, pd.DataFrame([{
                "id": kode,
                "nama": nama,
                "harga": int(harga),
                "stok": int(stok)
            }])], ignore_index=True)

            save_barang(df)
            qr_path = ensure_qr_exists(kode)

            st.success("Barang berhasil disimpan")
            st.image(qr_path, width=200)

            with open(qr_path, "rb") as f:
                st.download_button("⬇ Download Barcode Barang Ini", f, file_name=f"{kode}.png")

    st.dataframe(df, use_container_width=True)

# ==================================================
# MENU 2 – SCAN & TRANSAKSI
# ==================================================
elif menu == "Scan & Transaksi":
    st.title("🧾 Scan QR & Transaksi")

    img = st.camera_input("Scan QR Barang")

    if img:
        kode = decode_qr(img)
        if kode:
            df = load_barang()
            row = df[df["id"] == kode]

            if row.empty:
                st.error("Barang tidak ditemukan")
            else:
                b = row.iloc[0]
                st.success(f"""
                **Nama:** {b['nama']}  
                **Harga:** Rp {int(b['harga'])}  
                **Stok:** {int(b['stok'])}
                """)

                qty = st.number_input("Qty", min_value=1, max_value=int(b["stok"]), step=1)

                if st.button("Tambah ke Keranjang"):
                    add_cart({
                        "id": b["id"],
                        "nama": b["nama"],
                        "qty": int(qty),
                        "harga": int(b["harga"]),
                        "subtotal": int(qty) * int(b["harga"])
                    })
                    st.rerun()

    if st.session_state.cart:
        st.subheader("🛒 Keranjang Belanja")
        dfc = pd.DataFrame(st.session_state.cart)
        total = int(dfc["subtotal"].sum())

        st.table(dfc)
        st.write(f"**TOTAL: Rp {total}**")

        if st.button("💳 Proses Transaksi"):
            kode_trx = "TRX" + datetime.now().strftime("%Y%m%d%H%M%S")
            waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            df_trans = load_transaksi()
            df_barang = load_barang()

            for item in st.session_state.cart:
                df_trans = pd.concat([df_trans, pd.DataFrame([{
                    "waktu": waktu,
                    "id": item["id"],
                    "nama": item["nama"],
                    "qty": item["qty"],
                    "harga": item["harga"],
                    "subtotal": item["subtotal"],
                    "kode_trx": kode_trx
                }])], ignore_index=True)

                idx = df_barang[df_barang["id"] == item["id"]].index[0]
                df_barang.at[idx, "stok"] -= item["qty"]

            save_transaksi(df_trans)
            save_barang(df_barang)
            clear_cart()

            st.success("Transaksi berhasil")

# ==================================================
# MENU 3 – MANAJEMEN DATA + BARCODE + EDIT + HAPUS
# ==================================================
elif menu == "Manajemen Data":
    st.title("⚙️ Manajemen Data Barang")

    df = load_barang()
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        st.subheader("✏️ Edit / Hapus Barang")
        pilih = st.selectbox("Pilih Barang", df["id"])
        row = df[df["id"] == pilih].iloc[0]

        nama = st.text_input("Nama", row["nama"])
        harga = st.number_input("Harga", value=int(row["harga"]), step=1000)
        stok = st.number_input("Stok", value=int(row["stok"]), step=1)

        colu1, colu2 = st.columns(2)

        with colu1:
            if st.button("💾 Update Data"):
                df.loc[df["id"] == pilih, ["nama","harga","stok"]] = [
                    nama, int(harga), int(stok)
                ]
                save_barang(df)
                st.success("Data diperbarui")
                st.rerun()

        with colu2:
            if st.button("🗑 Hapus Data"):
                df = df[df["id"] != pilih]
                save_barang(df)

                qr_file = os.path.join(QR_DIR, f"{pilih}.png")
                if os.path.exists(qr_file):
                    os.remove(qr_file)

                st.success("Data berhasil dihapus")
                st.rerun()

    st.markdown("### 📌 Daftar Barcode Barang (langsung download)")
    for _, row in df.iterrows():
        kode = row["id"]
        nama = row["nama"]

        qr_path = ensure_qr_exists(kode)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{nama}** — {kode}")
            st.image(qr_path, width=250)
        with col2:
            with open(qr_path, "rb") as f:
                st.download_button("⬇ Download", f, file_name=f"{kode}.png", key=kode)

    if st.button("⬇ Download Semua Barcode (ZIP)"):
        zip_path = "barcode_all.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            for f in os.listdir(QR_DIR):
                z.write(os.path.join(QR_DIR, f), f)

        with open(zip_path, "rb") as f:
            st.download_button("Download ZIP", f, file_name="barcode_all.zip")


# ==================================================
# MENU 4 – LAPORAN
# ==================================================
elif menu == "Laporan":
    st.title("📊 Laporan Transaksi")
    df = load_transaksi()
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        st.download_button("⬇ Download CSV Transaksi",
                           df.to_csv(index=False),
                           "transaksi.csv",
                           "text/csv")
