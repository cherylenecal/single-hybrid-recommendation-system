import streamlit as st
import pandas as pd
import numpy as np
# import sqlite3
from datetime import datetime
# import json
import uuid
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import altair as alt
from streamlit_scroll_to_top import scroll_to_here
import mysql.connector


class DatabaseManager:
    def __init__(self):
        self.db_config = st.secrets["mysql"]
        self.init_db()

    # 1. BIKIN KONEKSI
    def get_connection(self):
        return mysql.connector.connect(
            host=self.db_config["host"],
            user=self.db_config["user"],
            password=self.db_config["password"],
            database=self.db_config["database"],
            port=self.db_config["port"]
        )
    
    # 2. BIKIN TABEL (Jalan otomatis saat pertama kali)
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        

        # 2. Buat Tabel Baru (Menggunakan single quote ''' agar aman)
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS mst_tbl(
            user_id VARCHAR(50) PRIMARY KEY,
            created_at DATETIME,
            name VARCHAR(100),
            kategori VARCHAR(100),
            role_desc TEXT,
            umur INT,
            gender VARCHAR(50),
            domisili VARCHAR(100),

            `INN-CE1` INT, `SE-M1` INT, `NACH-FF2` INT, `LOC-I1` INT,
            `SE-P2` INT, `INN-O2` INT, `SE-IP1` INT, `NACH-HS1` INT,
            `SE-IF1` INT, `LOC-E2` INT, `SE-S1` INT, `INN-W1` INT,
            `NACH-HS2` INT, `SE-IF2` INT, `INN-CE2` INT, `LOC-E1` INT,
            `SE-M2` INT, `SE-S2` INT, `LOC-I2` INT, `INN-W2` INT,
            `SE-P1` INT, `INN-O1` INT, `SE-IP2` INT, `NACH-FF1` INT,

            `CON-2` INT, `OPE-3` INT, `NEU-1` INT, `AGR-2` INT,
            `EXT-2` INT, `CON-1` INT, `OPE-1` INT, `AGR-1` INT,
            `NEU-3` INT, `EXT-3` INT, `OPE-2` INT, `AGR-3` INT,
            `NEU-2` INT, `CON-3` INT, `EXT-1` INT,
            
            rec_single TEXT,
            rec_hybrid TEXT,
            top3_sector_single TEXT,
            top3_sector_hybrid TEXT,
            rate_single INT,
            chosen_s_list TEXT,
            feedback_single TEXT,
            rate_hybrid INT,
            chosen_h_list TEXT,
            feedback_hybrid TEXT
        )
        '''
        
        try:
            cursor.execute(create_table_query)
            conn.commit()
        except mysql.connector.Error as e:
            # INI AKAN MUNCUL DI LAYAR JIKA ERROR
            st.error("🚨 TERJADI ERROR SAAT MEMBUAT DATABASE!")
            st.error(f"Pesan Error SQL: {e}")
            st.code(create_table_query, language="sql") # Tampilkan query biar kelihatan salahnya
            st.stop() # Hentikan program agar tidak crash lebih parah
        finally:
            conn.close()

    # 3. FUNGSI SIMPAN DATA USER
    def save_user_profile(self, profile_dict):
        print("--- [DEBUG] 1. Membuka Koneksi... ---")
        conn = self.get_connection()
        print("--- [DEBUG] Connected ---")
        cursor = conn.cursor()

        new_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Query dasar untuk membuat user baru
        query = """
            INSERT INTO mst_tbl (user_id, created_at, name, kategori, role_desc, umur, gender, domisili)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            new_id, 
            timestamp, 
            profile_dict.get('name'), 
            profile_dict.get('role'), 
            profile_dict.get('role_desc'), 
            profile_dict.get('age'), 
            profile_dict.get('gender'), 
            profile_dict.get('domicile')
        )
        
        try:
            print("--- [DEBUG] 2. Eksekusi Query INSERT... ---")
            cursor.execute(query, values)
            print("--- [DEBUG] 3. Melakukan COMMIT... ---")
            conn.commit()
            print("--- [DEBUG] 4. Selesai & Return ID ---")
            return new_id # PENTING: Kembalikan ID agar bisa disimpan di session_state
        except mysql.connector.Error as e:
            print(f"Error Save Profile: {e}")
            raise e
        finally:
            print("--- [DEBUG] 5. Menutup Koneksi (Closing)... ---")
            conn.close()
    
    # B. FUNGSI UPDATE JAWABAN (DINAMIS)
    # Dipanggil di akhir Part 1 DAN di akhir Part 2
    def update_user_answers(self, user_id, answers_dict):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Jika tidak ada jawaban (kosong), skip saja
        if not answers_dict:
            return

        # Teknik Dynamic Query untuk UPDATE
        # Kita ingin menyusun: UPDATE mst_tbl SET "INN-CE1" = ?, "SE-M1" = ? WHERE user_id = ?
        
        set_clauses = []
        values = []
        
        for key, val in answers_dict.items():
            set_clauses.append(f'`{key}` = %s') # Pakai tanda kutip dua untuk nama kolom
            values.append(val)
            
        # Tambahkan user_id di urutan terakhir untuk WHERE clause
        values.append(user_id) 
        
        query_str = f"""
            UPDATE mst_tbl 
            SET {', '.join(set_clauses)}
            WHERE user_id = %s
        """
        
        try:
            cursor.execute(query_str, values)
            conn.commit()
            print(f"✅ Berhasil update data untuk User ID: {user_id}")
        except mysql.connector.Error as e:
            print(f"❌ Error Update: {e}\nQuery: {query_str}")
            raise e
        finally:
            conn.close()

    # 4. FUNGSI LIHAT DATA (Untuk Admin/Kamu ngecek)
    def view_all_users(self):
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM users ORDER BY id DESC", conn)
        conn.close()
        return df
    
    

# ==========================================
# 1. DATA REFERENSI (DAFTAR KOTA/KAB)
# ==========================================
# Daftar lengkap kota & kabupaten di Indonesia
domisili_input = [
    # ACEH
    "Kabupaten Aceh Barat", "Kabupaten Aceh Barat Daya", "Kabupaten Aceh Besar",
    "Kabupaten Aceh Jaya", "Kabupaten Aceh Selatan", "Kabupaten Aceh Singkil",
    "Kabupaten Aceh Tamiang", "Kabupaten Aceh Tengah", "Kabupaten Aceh Tenggara",
    "Kabupaten Aceh Timur", "Kabupaten Aceh Utara", "Kabupaten Bener Meriah",
    "Kabupaten Bireuen", "Kabupaten Gayo Lues", "Kabupaten Nagan Raya",
    "Kabupaten Pidie", "Kabupaten Pidie Jaya", "Kabupaten Simeulue",
    "Kota Banda Aceh", "Kota Langsa", "Kota Lhokseumawe", "Kota Sabang",
    "Kota Subulussalam",
    # SUMATERA UTARA
    "Kabupaten Asahan", "Kabupaten Batubara", "Kabupaten Dairi", "Kabupaten Deli Serdang",
    "Kabupaten Humbang Hasundutan", "Kabupaten Karo", "Kabupaten Labuhanbatu",
    "Kabupaten Labuhanbatu Selatan", "Kabupaten Labuhanbatu Utara", "Kabupaten Langkat",
    "Kabupaten Mandailing Natal", "Kabupaten Nias", "Kabupaten Nias Barat",
    "Kabupaten Nias Selatan", "Kabupaten Nias Utara", "Kabupaten Padang Lawas",
    "Kabupaten Padang Lawas Utara", "Kabupaten Pakpak Bharat", "Kabupaten Samosir",
    "Kabupaten Serdang Bedagai", "Kabupaten Simalungun", "Kabupaten Tapanuli Selatan",
    "Kabupaten Tapanuli Tengah", "Kabupaten Tapanuli Utara", "Kabupaten Toba",
    "Kota Binjai", "Kota Gunungsitoli", "Kota Medan", "Kota Padangsidimpuan",
    "Kota Pematangsiantar", "Kota Sibolga", "Kota Tanjungbalai", "Kota Tebing Tinggi",
    # SUMATERA BARAT
    "Kabupaten Agam", "Kabupaten Dharmasraya", "Kabupaten Kepulauan Mentawai",
    "Kabupaten Lima Puluh Kota", "Kabupaten Padang Pariaman", "Kabupaten Pasaman",
    "Kabupaten Pasaman Barat", "Kabupaten Pesisir Selatan", "Kabupaten Sijunjung",
    "Kabupaten Solok", "Kabupaten Solok Selatan", "Kabupaten Tanah Datar",
    "Kota Bukittinggi", "Kota Padang", "Kota Padangpanjang", "Kota Pariaman",
    "Kota Payakumbuh", "Kota Sawahlunto", "Kota Solok",
    # RIAU
    "Kabupaten Bengkalis", "Kabupaten Indragiri Hilir", "Kabupaten Indragiri Hulu",
    "Kabupaten Kampar", "Kabupaten Kepulauan Meranti", "Kabupaten Kuantan Singingi",
    "Kabupaten Pelalawan", "Kabupaten Rokan Hilir", "Kabupaten Rokan Hulu",
    "Kabupaten Siak", "Kota Dumai", "Kota Pekanbaru",
    # JAMBI
    "Kabupaten Batanghari", "Kabupaten Bungo", "Kabupaten Kerinci",
    "Kabupaten Merangin", "Kabupaten Muaro Jambi", "Kabupaten Sarolangun",
    "Kabupaten Tanjung Jabung Barat", "Kabupaten Tanjung Jabung Timur",
    "Kabupaten Tebo", "Kota Jambi", "Kota Sungai Penuh",
    # SUMATERA SELATAN
    "Kabupaten Banyuasin", "Kabupaten Empat Lawang", "Kabupaten Lahat",
    "Kabupaten Muara Enim", "Kabupaten Musi Banyuasin", "Kabupaten Musi Rawas",
    "Kabupaten Musi Rawas Utara", "Kabupaten Ogan Ilir", "Kabupaten Ogan Komering Ilir",
    "Kabupaten Ogan Komering Ulu", "Kabupaten Ogan Komering Ulu Selatan",
    "Kabupaten Ogan Komering Ulu Timur", "Kota Lubuklinggau", "Kota Pagar Alam",
    "Kota Palembang", "Kota Prabumulih",
    # BENGKULU
    "Kabupaten Bengkulu Selatan", "Kabupaten Bengkulu Tengah", "Kabupaten Bengkulu Utara",
    "Kabupaten Kaur", "Kabupaten Kepahiang", "Kabupaten Lebong",
    "Kabupaten Mukomuko", "Kabupaten Rejang Lebong", "Kabupaten Seluma",
    "Kota Bengkulu",
    # LAMPUNG
    "Kabupaten Lampung Barat", "Kabupaten Lampung Selatan", "Kabupaten Lampung Tengah",
    "Kabupaten Lampung Timur", "Kabupaten Lampung Utara", "Kabupaten Mesuji",
    "Kabupaten Pesawaran", "Kabupaten Pesisir Barat", "Kabupaten Pringsewu",
    "Kabupaten Tanggamus", "Kabupaten Tulang Bawang", "Kabupaten Tulang Bawang Barat",
    "Kabupaten Way Kanan", "Kota Bandar Lampung", "Kota Metro",
    # KEP. BANGKA BELITUNG
    "Kabupaten Bangka", "Kabupaten Bangka Barat", "Kabupaten Bangka Selatan",
    "Kabupaten Bangka Tengah", "Kabupaten Belitung", "Kabupaten Belitung Timur",
    "Kota Pangkalpinang",
    # KEP. RIAU
    "Kabupaten Bintan", "Kabupaten Karimun", "Kabupaten Kepulauan Anambas",
    "Kabupaten Lingga", "Kabupaten Natuna", "Kota Batam", "Kota Tanjungpinang",
    # DKI JAKARTA
    "Kota Jakarta Barat", "Kota Jakarta Pusat", "Kota Jakarta Selatan",
    "Kota Jakarta Timur", "Kota Jakarta Utara", "Kabupaten Kepulauan Seribu",
    # JAWA BARAT
    "Kabupaten Bandung", "Kabupaten Bandung Barat", "Kabupaten Bekasi",
    "Kabupaten Bogor", "Kabupaten Ciamis", "Kabupaten Cianjur", "Kabupaten Cirebon",
    "Kabupaten Garut", "Kabupaten Indramayu", "Kabupaten Karawang",
    "Kabupaten Kuningan", "Kabupaten Majalengka", "Kabupaten Pangandaran",
    "Kabupaten Purwakarta", "Kabupaten Subang", "Kabupaten Sukabumi",
    "Kabupaten Sumedang", "Kabupaten Tasikmalaya", "Kota Bandung", "Kota Banjar",
    "Kota Bekasi", "Kota Bogor", "Kota Cimahi", "Kota Cirebon", "Kota Depok",
    "Kota Sukabumi", "Kota Tasikmalaya",
    # JAWA TENGAH
    "Kabupaten Banjarnegara", "Kabupaten Banyumas", "Kabupaten Batang",
    "Kabupaten Blora", "Kabupaten Boyolali", "Kabupaten Brebes", "Kabupaten Cilacap",
    "Kabupaten Demak", "Kabupaten Grobogan", "Kabupaten Jepara",
    "Kabupaten Karanganyar", "Kabupaten Kebumen", "Kabupaten Kendal",
    "Kabupaten Klaten", "Kabupaten Kudus", "Kabupaten Magelang",
    "Kabupaten Pati", "Kabupaten Pekalongan", "Kabupaten Pemalang",
    "Kabupaten Purbalingga", "Kabupaten Purworejo", "Kabupaten Rembang",
    "Kabupaten Semarang", "Kabupaten Sragen", "Kabupaten Sukoharjo",
    "Kabupaten Tegal", "Kabupaten Temanggung", "Kabupaten Wonogiri",
    "Kabupaten Wonosobo", "Kota Magelang", "Kota Pekalongan", "Kota Salatiga",
    "Kota Semarang", "Kota Surakarta", "Kota Tegal",
    # DI YOGYAKARTA
    "Kabupaten Bantul", "Kabupaten Gunungkidul", "Kabupaten Kulon Progo",
    "Kabupaten Sleman", "Kota Yogyakarta",
    # JAWA TIMUR
    "Kabupaten Bangkalan", "Kabupaten Banyuwangi", "Kabupaten Blitar",
    "Kabupaten Bojonegoro", "Kabupaten Bondowoso", "Kabupaten Gresik",
    "Kabupaten Jember", "Kabupaten Jombang", "Kabupaten Kediri",
    "Kabupaten Lamongan", "Kabupaten Lumajang", "Kabupaten Madiun",
    "Kabupaten Magetan", "Kabupaten Malang", "Kabupaten Mojokerto",
    "Kabupaten Nganjuk", "Kabupaten Ngawi", "Kabupaten Pacitan",
    "Kabupaten Pamekasan", "Kabupaten Pasuruan", "Kabupaten Ponorogo",
    "Kabupaten Probolinggo", "Kabupaten Sampang", "Kabupaten Sidoarjo",
    "Kabupaten Situbondo", "Kabupaten Sumenep", "Kabupaten Trenggalek",
    "Kabupaten Tuban", "Kabupaten Tulungagung", "Kota Batu", "Kota Blitar",
    "Kota Kediri", "Kota Madiun", "Kota Malang", "Kota Mojokerto",
    "Kota Pasuruan", "Kota Probolinggo", "Kota Surabaya",
    # BANTEN
    "Kabupaten Lebak", "Kabupaten Pandeglang",
    "Kabupaten Serang", "Kabupaten Tangerang",
    "Kota Cilegon", "Kota Serang", "Kota Tangerang",
    "Kota Tangerang Selatan",
    # BALI
    "Kabupaten Badung", "Kabupaten Bangli", "Kabupaten Buleleng",
    "Kabupaten Gianyar", "Kabupaten Jembrana", "Kabupaten Karangasem",
    "Kabupaten Klungkung", "Kabupaten Tabanan", "Kota Denpasar",
    # NUSA TENGGARA BARAT
    "Kabupaten Bima", "Kabupaten Dompu", "Kabupaten Lombok Barat",
    "Kabupaten Lombok Tengah", "Kabupaten Lombok Timur", "Kabupaten Lombok Utara",
    "Kabupaten Sumbawa", "Kabupaten Sumbawa Barat", "Kota Bima", "Kota Mataram",
    # NUSA TENGGARA TIMUR
    "Kabupaten Alor", "Kabupaten Belu", "Kabupaten Ende", "Kabupaten Flores Timur",
    "Kabupaten Kupang", "Kabupaten Lembata", "Kabupaten Malaka", "Kabupaten Manggarai",
    "Kabupaten Manggarai Barat", "Kabupaten Manggarai Timur", "Kabupaten Ngada",
    "Kabupaten Nagekeo", "Kabupaten Rote Ndao", "Kabupaten Sabu Raijua",
    "Kabupaten Sikka", "Kabupaten Sumba Barat", "Kabupaten Sumba Barat Daya",
    "Kabupaten Sumba Tengah", "Kabupaten Sumba Timur", "Kabupaten Timor Tengah Selatan",
    "Kabupaten Timor Tengah Utara", "Kota Kupang",
    # KALIMANTAN BARAT
    "Kabupaten Bengkayang", "Kabupaten Kapuas Hulu", "Kabupaten Kayong Utara",
    "Kabupaten Ketapang", "Kabupaten Kubu Raya", "Kabupaten Landak",
    "Kabupaten Melawi", "Kabupaten Mempawah", "Kabupaten Sambas",
    "Kabupaten Sanggau", "Kabupaten Sekadau", "Kabupaten Sintang",
    "Kota Pontianak", "Kota Singkawang",
    # KALIMANTAN TENGAH
    "Kabupaten Barito Selatan", "Kabupaten Barito Timur", "Kabupaten Barito Utara",
    "Kabupaten Gunung Mas", "Kabupaten Kapuas", "Kabupaten Katingan",
    "Kabupaten Kotawaringin Barat", "Kabupaten Kotawaringin Timur",
    "Kabupaten Lamandau", "Kabupaten Murung Raya", "Kabupaten Pulang Pisau",
    "Kabupaten Seruyan", "Kabupaten Sukamara", "Kota Palangka Raya",
    # KALIMANTAN SELATAN
    "Kabupaten Balangan", "Kabupaten Banjar", "Kabupaten Barito Kuala",
    "Kabupaten Hulu Sungai Selatan", "Kabupaten Hulu Sungai Tengah",
    "Kabupaten Hulu Sungai Utara", "Kabupaten Kotabaru", "Kabupaten Tabalong",
    "Kabupaten Tanah Bumbu", "Kabupaten Tanah Laut", "Kabupaten Tapin",
    "Kota Banjarbaru", "Kota Banjarmasin",
    # KALIMANTAN TIMUR
    "Kabupaten Berau", "Kabupaten Kutai Barat", "Kabupaten Kutai Kartanegara",
    "Kabupaten Kutai Timur", "Kabupaten Mahakam Ulu", "Kabupaten Paser",
    "Kabupaten Penajam Paser Utara", "Kota Balikpapan", "Kota Bontang",
    "Kota Samarinda",
    # KALIMANTAN UTARA
    "Kabupaten Bulungan", "Kabupaten Malinau", "Kabupaten Nunukan",
    "Kabupaten Tana Tidung", "Kota Tarakan",
    # SULAWESI UTARA
    "Kabupaten Bolaang Mongondow", "Kabupaten Bolaang Mongondow Selatan",
    "Kabupaten Bolaang Mongondow Timur", "Kabupaten Bolaang Mongondow Utara",
    "Kabupaten Kepulauan Sangihe", "Kabupaten Kepulauan Siau Tagulandang Biaro",
    "Kabupaten Kepulauan Talaud", "Kabupaten Minahasa", "Kabupaten Minahasa Selatan",
    "Kabupaten Minahasa Tenggara", "Kabupaten Minahasa Utara",
    "Kota Bitung", "Kota Kotamobagu", "Kota Manado", "Kota Tomohon",
    # SULAWESI TENGAH
    "Kabupaten Banggai", "Kabupaten Banggai Kepulauan", "Kabupaten Banggai Laut",
    "Kabupaten Buol", "Kabupaten Donggala", "Kabupaten Morowali",
    "Kabupaten Morowali Utara", "Kabupaten Parigi Moutong", "Kabupaten Poso",
    "Kabupaten Sigi", "Kabupaten Tojo Una-Una", "Kabupaten Tolitoli",
    "Kota Palu",
    # SULAWESI SELATAN
    "Kabupaten Bantaeng", "Kabupaten Barru", "Kabupaten Bone", "Kabupaten Bulukumba",
    "Kabupaten Enrekang", "Kabupaten Gowa", "Kabupaten Jeneponto",
    "Kabupaten Kepulauan Selayar", "Kabupaten Luwu", "Kabupaten Luwu Timur",
    "Kabupaten Luwu Utara", "Kabupaten Maros", "Kabupaten Pangkajene Kepulauan",
    "Kabupaten Pinrang", "Kabupaten Sidenreng Rappang", "Kabupaten Sinjai",
    "Kabupaten Soppeng", "Kabupaten Takalar", "Kabupaten Tana Toraja",
    "Kabupaten Toraja Utara", "Kota Makassar", "Kota Palopo", "Kota Parepare",
    # SULAWESI TENGGARA
    "Kabupaten Bombana", "Kabupaten Buton", "Kabupaten Buton Selatan",
    "Kabupaten Buton Tengah", "Kabupaten Buton Utara", "Kabupaten Kolaka",
    "Kabupaten Kolaka Timur", "Kabupaten Kolaka Utara", "Kabupaten Konawe",
    "Kabupaten Konawe Kepulauan", "Kabupaten Konawe Selatan",
    "Kabupaten Konawe Utara", "Kabupaten Muna", "Kabupaten Muna Barat",
    "Kabupaten Wakatobi", "Kota Baubau", "Kota Kendari",
    # GORONTALO
    "Kabupaten Boalemo", "Kabupaten Bone Bolango", "Kabupaten Gorontalo",
    "Kabupaten Gorontalo Utara", "Kabupaten Pohuwato", "Kota Gorontalo",
    # SULAWESI BARAT
    "Kabupaten Majene", "Kabupaten Mamasa", "Kabupaten Mamuju",
    "Kabupaten Mamuju Tengah", "Kabupaten Pasangkayu", "Kabupaten Polewali Mandar",
    # MALUKU
    "Kabupaten Buru", "Kabupaten Buru Selatan", "Kabupaten Kepulauan Aru",
    "Kabupaten Maluku Barat Daya", "Kabupaten Maluku Tengah",
    "Kabupaten Maluku Tenggara", "Kabupaten Seram Bagian Barat",
    "Kabupaten Seram Bagian Timur", "Kota Ambon", "Kota Tual",
    # MALUKU UTARA
    "Kabupaten Halmahera Barat", "Kabupaten Halmahera Tengah",
    "Kabupaten Halmahera Timur", "Kabupaten Halmahera Selatan",
    "Kabupaten Halmahera Utara", "Kabupaten Kepulauan Sula",
    "Kabupaten Pulau Morotai", "Kabupaten Pulau Taliabu",
    "Kota Ternate", "Kota Tidore Kepulauan",
    # PAPUA (lama)
    "Kabupaten Asmat", "Kabupaten Biak Numfor", "Kabupaten Boven Digoel",
    "Kabupaten Deiyai", "Kabupaten Dogiyai", "Kabupaten Intan Jaya",
    "Kabupaten Jayapura", "Kabupaten Jayawijaya", "Kabupaten Keerom",
    "Kabupaten Lanny Jaya", "Kabupaten Mamberamo Raya", "Kabupaten Mamberamo Tengah",
    "Kabupaten Mappi", "Kabupaten Merauke", "Kabupaten Mimika",
    "Kabupaten Nabire", "Kabupaten Nduga", "Kabupaten Paniai",
    "Kabupaten Pegunungan Bintang", "Kabupaten Puncak", "Kabupaten Puncak Jaya",
    "Kabupaten Sarmi", "Kabupaten Supiori", "Kabupaten Tolikara",
    "Kabupaten Waropen", "Kota Jayapura",
    # PAPUA TENGAH
    "Kabupaten Puncak", "Kabupaten Paniai", "Kabupaten Dogiyai", "Kabupaten Deiyai",
    "Kabupaten Nabire", "Kabupaten Mimika",
    # PAPUA PEGUNUNGAN
    "Kabupaten Jayawijaya", "Kabupaten Lanny Jaya", "Kabupaten Mamberamo Tengah",
    "Kabupaten Nduga", "Kabupaten Tolikara", "Kabupaten Yahukimo",
    "Kabupaten Yalimo", "Kabupaten Pegunungan Bintang",
    # PAPUA SELATAN
    "Kabupaten Merauke", "Kabupaten Mappi", "Kabupaten Asmat",
    "Kabupaten Boven Digoel",
    # PAPUA BARAT
    "Kabupaten Fakfak", "Kabupaten Kaimana", "Kabupaten Manokwari",
    "Kabupaten Manokwari Selatan", "Kabupaten Pegunungan Arfak",
    "Kabupaten Teluk Bintuni", "Kabupaten Teluk Wondama",
    "Kota Sorong",
    # PAPUA BARAT DAYA (baru)
    "Kabupaten Sorong", "Kabupaten Sorong Selatan", "Kabupaten Tambrauw",
    "Kabupaten Maybrat", "Kabupaten Raja Ampat", "Kota Sorong",
    # lainnya
    "Lainnya (Input Manual)"
]

# ==========================================
# 2. FUNGSI TAMPILAN PROFILE
# ==========================================

def render_cover_page():
    # --- STYLE CSS UNTUK TAMPILAN COVER ---
    st.markdown("""
    <style>
    /* Mengatur font dan warna latar belakang seluruh halaman */
    .stApp {
        background-color: #F8F9F1;
    }
    
    .cover-container {
        text-align: left;
        padding: 100px 10% 20px 10%;
    }
    
    .main-title {
        color: #0A0A44;
        font-size: 36px;
        font-weight: 800;
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
    }
    
    .description {
        color: #2D4A44;
        font-size: 24px;
        line-height: 1.4;
        margin-bottom: 30px;
        font-family: 'Inter', sans-serif;
    }
    
    .hint-text {
        color: #4A4A4A;
        font-size: 14px;
        margin-bottom: 5px;
    }
    
    .cta-text {
        color: #4A4A4A;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 30px;
    }

    /* Styling Tombol Start */
    div.stButton > button {
        background-color: #03043D !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 40px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #1A1A5E !important;
        transform: scale(1.05);
    }

    /* Styling Link di Bawah */
    .footer-link {
        color: #0A0A44;
        font-size: 13px;
        text-decoration: underline;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- KONTEN HALAMAN ---
    st.markdown('<div class="cover-container">', unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-title">Discover Your Ideal Business Type!</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <p class="description">
    Identifikasi sektor bisnis yang sesuai dengan profil Anda melalui analisis antara 
    <b>Big Five Personality Traits</b> dan <b> Karakteristik Psikologis Wirausaha</b>. <br><br>
    Sistem ini memetakan karakteristik psikologis dan kepribadian Anda 
    untuk menghasilkan rekomendasi sektor bisnis yang relevan secara objektif.
    </p>
    """, unsafe_allow_html=True)

    # --- INFORMASI TUJUAN PENELITIAN & FEEDBACK ---
    st.markdown("""
    <div class="info-box">
        <b>🔬 Metodologi Pengujian:</b><br>
        Platform ini membandingkan akurasi dari dua metode sistem rekomendasi yang berbeda. 
        Partisipasi Anda diharapkan untuk memberikan <b>evaluasi komparatif</b> pada akhir sesi 
        guna menentukan efektivitas dari masing-masing metode yang diuji.
    </div>
    """, unsafe_allow_html=True)

    # TOMBOL START
    if st.button("Start"):
        st.session_state['halaman_sekarang'] = "profil"
        st.rerun()
    
    # LINK BAWAH
    st.markdown('<p class="footer-link">Already have business? go to homepage</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    

def render_profile():
    # --- STYLE CSS UNTUK TAMPILAN COVER ---
    st.markdown("""
    <style>
        /* 1. Background Halaman */
        .stApp {
            background-color: #F8F9F1;
        }

        /* 2. Styling Input (Text, Number, Selectbox) agar LEBIH KELIHATAN */
        /* Mengubah background input menjadi putih & tambah border */
        div[data-baseweb="input"] > div, 
        div[data-baseweb="select"] > div, 
        div[data-baseweb="base-input"] {
            background-color: #FFFFFF !important;
            border: 1px solid #C0C0C0 !important; /* Border abu-abu agar tegas */
            border-radius: 8px !important;
            color: #0A0A44 !important; /* Warna teks input */
        }

        /* 3. Styling Tombol (Konsisten dengan sebelumnya) */
        div.stButton > button {
            background-color: #03043D !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 10px 24px !important; /* Padding disesuaikan agar rapi */
            border: none !important;
            transition: 0.3s;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        }
        
        div.stButton > button:hover {
            background-color: #1A1A5E !important;
            transform: translateY(-2px); /* Efek naik sedikit saat hover */
        }

        /* 4. Progress Bar Styling (Opsional, biar matching) */
        div[data-testid="stProgress"] > div > div {
            background-color: #03043D !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.header("👤 Profil Pengguna")

    st.write("**Nama**")
    name = st.text_input(
        "Masukkan Nama Anda",
        help="Ketik nama Anda di sini."
    )

    st.divider()

    
    # 1. KATEGORI (Dropdown)
    st.write("**Kategori**")
    st.caption("Mohon pilih kategori yang paling menggambarkan peran Anda dalam aktivitas ekonomi atau profesional saat ini:")
    role = st.selectbox(
        "Pilih Kategori", # Label tersembunyi/kecil karena sudah ada di write/caption
        options=["Calon Wirausahawan", "Pelaku UMKM", "Pelajar/Mahasiswa", "Profesional"],
        label_visibility="collapsed" # Menyembunyikan label default agar lebih rapi
    )

    if role == "Calon Wirausahawan":
        role_desc = st.text_input(
            "Wirausaha apa yang sedang direncanakan?", 
            placeholder="Nama wirausaha...",
            help="Ketik nama wirausaha Anda di sini."
        )
    elif role == "Pelaku UMKM":
        role_desc = st.text_input(
            "UMKM apa yang sedang dijalankan?", 
            placeholder="Nama UMKM...",
            help="Ketik nama UMKM Anda di sini."
        )
    elif role == "Pelajar/Mahasiswa":
        role_desc = st.text_input(
            "Jurusan apa yang sedang dijalani?", 
            placeholder="Nama jurusan...",
            help="Ketik nama jurusan Anda di sini."
        )
    else:
        role_desc = st.text_input(
            "Saat ini sedang berperan sebagai apa?", 
            placeholder="Nama profesi...",
            help="Ketik profesi Anda di sini."
        )
    st.divider()

    # 2. UMUR (Number Input)
    st.write("**Usia**")
    age = st.number_input(
        "Masukkan Usia Anda",
        min_value=1, 
        max_value=99, 
        value=18,
        label_visibility="collapsed"
    )
    st.divider()

    # 3. GENDER (Dropdown)
    st.write("**Jenis Kelamin**")
    gender = st.selectbox(
        "Pilih Gender",
        options=["Laki-laki", "Perempuan"],
        label_visibility="collapsed"
    )
    st.divider()

    # 4. DOMISILI (Combobox / Selectbox with Search)
    st.write("**Domisili**")
    st.caption("Ketik nama kota/kabupaten untuk mencari:")
    
    # Di Streamlit, st.selectbox secara default sudah bisa di-search (seperti Combobox)
    domicile_selection = st.selectbox(
        "Pilih Domisili",
        options=domisili_input,
        index=None, # Kosongkan default agar user memilih
        placeholder="Cari Kota/Kabupaten...",
        label_visibility="collapsed"
    )
    final_domicile = domicile_selection # Default value

    if domicile_selection == "Lainnya (Input Manual)":
        final_domicile = st.text_input(
            "Masukkan Nama Kota/Kabupaten Anda", 
            placeholder="Contoh: Kabupaten Puncak Jaya",
            help="Ketik nama kota atau kabupaten Anda secara manual di sini."
        )
    st.divider()

    # --- BAGIAN TOMBOL NEXT ---
    # Menggunakan st.button biasa (bukan form_submit karena ini bukan di dalam st.form)
    if st.button("Lanjut ke Kuesioner ➡️", type="primary"):
        
        # 1. Validasi Input (Cek apakah domisili kosong?)
        
        if not name:
            st.error("⚠️ Mohon lengkapi nama Anda terlebih dahulu.")
        elif not role:
            st.error("⚠️ Mohon lengkapi peran Anda terlebih dahulu.")
        elif not role_desc:
            st.error("⚠️ Mohon lengkapi deskripsi peran Anda terlebih dahulu.")
        elif not age:
            st.error("⚠️ Mohon lengkapi usia Anda terlebih dahulu.")
        elif not gender:
            st.error("⚠️ Mohon lengkapi gender Anda terlebih dahulu.")
        elif not final_domicile:
            st.error("⚠️ Mohon lengkapi domisili Anda terlebih dahulu.")
        else:
            try:
                # 2. Simpan Data ke Memory (Session State)
                profil_data = {
                    "name": name,
                    "role": role,
                    "role_desc": role_desc,
                    "age": age,
                    "gender": gender,
                    "domicile": final_domicile
                }

                st.session_state['temp_profile'] = profil_data
                # 2. PANGGIL DATABASE MANAGER
                # 3. Panggil Database Manager
                if 'db' not in st.session_state:
                    st.session_state['db'] = DatabaseManager()

                db = st.session_state['db']

                # DEBUG: Print ke terminal (Lihat di VS Code / CMD Anda saat klik)
                print(f"Sedang menyimpan profil: {profil_data}")

                # --- OPERAN 1: Menerima ID dari Database ---
                id_baru = db.save_user_profile(profil_data)
                
                # --- OPERAN 2: Menyimpan ID ke "Tas" (Session State) ---
                st.session_state['current_user_id'] = id_baru 
                
                st.success("Profil tersimpan! Lanjut...")
                st.session_state['halaman_sekarang'] = "part_1"
                st.rerun()
            
            except Exception as e:
                st.error(f"Gagal menyimpan: {e}")
                
            # 4. Refresh Halaman
            st.rerun()
    

def likert_item(question_text, key_name, default_value=3):
    """
    Komponen Likert Scale Responsif:
    - Desktop: Label di samping kiri-kanan.
    - Mobile: Label pindah ke atas (kiri & kanan) agar tidak hilang & muat.
    """
    
    st.markdown("""
    <style>
    /* 1. CONTAINER UTAMA (STREAMLIT RADIO) */
    div.row-widget.stRadio {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }

    /* 2. GROUP TOMBOL (FLEX CONTAINER) */
    div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important; /* Jangan 170%, ini bikin scroll. Pakai 100% */
        position: relative !important; /* Penting untuk posisi absolute di Mobile */
        gap: 15px !important;
    }

    /* 3. DESKTOP: LABEL KIRI (DEFAULT) */
    div[role="radiogroup"]::before {
        content: "Sangat Tidak Setuju";
        font-size: 14px !important;
        color: #666;
        font-weight: 500;
        text-align: right;
        width: 130px !important; /* Lebar fix agar seimbang */
        margin-right: 15px !important;
        line-height: 1.2;
        display: block;
    }

    /* 4. DESKTOP: LABEL KANAN (DEFAULT) */
    div[role="radiogroup"]::after {
        content: "Sangat Setuju";
        font-size: 14px !important;
        color: #666;
        font-weight: 500;
        text-align: left;
        width: 130px !important; /* Lebar fix sama dengan kiri */
        margin-left: 15px !important;
        line-height: 1.2;
        display: block;
    }

    /* 5. ITEM TOMBOL (1-5) */
    div[role="radiogroup"] > label {
        display: flex !important;
        flex-direction: column-reverse !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        width: 40px !important;
        cursor: pointer !important;
        z-index: 2; /* Pastikan tombol di atas label jika overlap */
    }

    /* 6. ANGKA DI ATAS BULATAN */
    div[role="radiogroup"] > label > div[data-testid="stMarkdownContainer"] > p {
        font-size: 18px !important;
        font-weight: bold !important;
        color: #333 !important;
        margin-bottom: 8px !important;
        text-align: center !important;
    }

    /* 7. BULATAN RADIO */
    div[role="radiogroup"] > label > div:first-child {
        transform: scale(1.5) !important;
        margin-top: 0px !important;
    }

    /* ========================================= */
    /* 8. MEDIA QUERY KHUSUS HP (Max Width 600px) */
    /* ========================================= */
    @media (max-width: 600px) {
        
        /* Ubah layout container: Beri ruang di atas untuk label */
        div[role="radiogroup"] {
            gap: 8px !important; /* Perkecil jarak antar tombol biar muat */
            padding-top: 40px !important; /* Ruang kosong di atas tombol untuk teks */
            align-items: flex-end !important; /* Tombol rapat bawah */
        }

        /* LABEL KIRI: Pindah ke Pojok Kiri Atas */
        div[role="radiogroup"]::before {
            display: block !important; /* Tetap tampilkan */
            position: absolute !important; /* Lepas dari aliran flex */
            top: 0 !important;
            left: 0 !important;
            width: 50% !important; /* Setengah layar */
            text-align: left !important; /* Rata kiri */
            margin: 0 !important;
            font-size: 12px !important; /* Kecilkan sedikit font */
        }

        /* LABEL KANAN: Pindah ke Pojok Kanan Atas */
        div[role="radiogroup"]::after {
            display: block !important; /* Tetap tampilkan */
            position: absolute !important;
            top: 0 !important;
            right: 0 !important;
            width: 50% !important; /* Setengah layar */
            text-align: right !important; /* Rata kanan */
            margin: 0 !important;
            font-size: 12px !important;
        }
        
        /* Perkecil sedikit area klik tombol agar muat 5 biji */
        div[role="radiogroup"] > label {
            width: 30px !important; 
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. TAMPILKAN PERTANYAAN (Center)
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
            <h3 style="font-weight: 600;">{question_text}</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 3. WIDGET RADIO BUTTON
    # Konversi nilai 1-5 menjadi index 0-4
    idx = default_value - 1
    
    selected_value = st.radio(
        label="Likert Scale",
        options=[1, 2, 3, 4, 5],
        index=idx,
        key=key_name,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    return selected_value

questions_A = {
    "INN-CE1": "Saya tertantang oleh ketidakpastian dan masalah yang belum terpecahkan.",
    "SE-M1":   "Saya percaya diri dapat melakukan networking, yaitu membangun hubungan dan bertukar informasi yang bermanfaat dengan berbagai pihak untuk mendukung kegiatan atau proyek saya.",
    "NACH-FF2": "Jika saya tidak langsung mengerti sebuah masalah, saya mulai merasa cemas.",
    "LOC-I1":   "Jika saya bekerja dengan sungguh-sungguh, saya bisa mencapai hasil yang saya inginkan.",
    "SE-P2":    "Saya percaya diri dapat memperkirakan jumlah modal awal dan modal kerja yang diperlukan.",
    "INN-O2":   "Saya terbuka untuk menggunakan cara baru meskipun belum umum dipraktikkan orang lain.",
    "SE-IP1":   "Saya percaya diri dapat memotivasi dan mendorong anggota tim agar semangat dalam bekerja.",
    "NACH-HS1": "Saya termotivasi untuk segera bertindak ketika menghadapi tantangan yang bisa saya selesaikan.",
    "SE-IF1":   "Saya percaya diri dapat mengorganisir dan memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan.",
    "LOC-E2":   "Saya percaya bahwa hasil kerja saya banyak dipengaruhi oleh keadaan atau orang lain, bukan sepenuhnya oleh usaha saya.",
    "SE-S1":    "Saya percaya diri dapat mengidentifikasi kebutuhan atau peluang baru yang bisa diwujudkan menjadi solusi.",
    "INN-W1":   "Saya bersedia untuk mencoba cara baru meskipun berbeda dari kebiasaan saya sebelumnya.",
    "NACH-HS2": "Saya menikmati situasi di mana saya bisa menggunakan dan mengembangkan kemampuan saya.",
    "SE-IF2":   "Saya percaya diri dapat mengelola aset atau sumber daya keuangan secara efektif dalam usaha, proyek, atau kegiatan saya.",
    "INN-CE2":  "Saya sering mengimprovisasi metode untuk memecahkan masalah.",
    "LOC-E1":   "Saya merasa keberhasilan dalam pekerjaan banyak ditentukan oleh faktor di luar kendali saya.",
    "SE-M2":    "Saya percaya diri dapat meyakinkan orang lain untuk memahami, mendukung, dan ikut berkomitmen pada visi serta rencana yang saya buat.",
    "SE-S2":    "Saya percaya diri dapat merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar.",
    "LOC-I2":   "Saya percaya bahwa hasil pekerjaan saya bergantung pada usaha dan cara saya bekerja.",
    "INN-W2":   "Saya merasa antusias ketika harus beradaptasi dengan situasi baru.",
    "SE-P1":    "Saya percaya diri dapat menyusun rencana bisnis, termasuk memperkirakan permintaan pasar dan strategi pemasaran.",
    "INN-O1":   "Saya menikmati mencoba ide-ide baru.",
    "SE-IP2":   "Saya percaya diri dapat memilih orang yang tepat untuk bekerja sama dan membantu mereka mengembangkan kemampuan yang dibutuhkan.",
    "NACH-FF1": "Saya takut gagal dalam situasi agak sulit, ketika banyak hal bergantung pada saya."
}

KEYS_ENTRE = [
    'INN-CE1', 'SE-M1', 'NACH-FF2', 'LOC-I1', 'SE-P2', 'INN-O2', 
    'SE-IP1', 'NACH-HS1', 'SE-IF1', 'LOC-E2', 'SE-S1', 'INN-W1', 
    'NACH-HS2', 'SE-IF2', 'INN-CE2', 'LOC-E1', 'SE-M2', 'SE-S2', 
    'LOC-I2', 'INN-W2', 'SE-P1', 'INN-O1', 'SE-IP2', 'NACH-FF1'
]


domain_cols = {
    "innovativeness":  ["INN-CE1", "INN-O2", "INN-W1", "INN-CE2", "INN-W2", "INN-O1"],
    "self_efficacy":   ["SE-M1", "SE-P2", "SE-IP1", "SE-IF1", "SE-S1", "SE-IF2", "SE-M2", "SE-S2", "SE-P1", "SE-IP2"],
    "need_achievement": ["NACH-FF2", "NACH-HS1", "NACH-HS2", "NACH-FF1"],
    "loc_internal":  ["LOC-I1", "LOC-I2"],
    "loc_external": ["LOC-E1", "LOC-E2"]
}



questions_B = {
    "CON-2": "Saya adalah seseorang yang cenderung malas (atau agak malas).",
    "OPE-3": "Saya adalah seseorang yang memiliki imajinasi yang jelas/hidup dan penuh fantasi.",
    "NEU-1": "Saya adalah seseorang yang sering khawatir.",
    "AGR-2": "Saya adalah seseorang yang mudah memaafkan (atau bisa memaafkan).",
    "EXT-2": "Saya adalah seseorang yang bisa keluar sendiri dan bersosialisasi (atau mudah bergaul).",
    "CON-1": "Saya adalah seseorang yang bekerja secara teliti (atau menyeluruh).",
    "OPE-1": "Saya adalah seseorang yang orisinil dan membawa ide-ide baru.",
    "AGR-1": "Saya adalah seseorang yang kadang-kadang agak kasar kepada orang lain.",
    "NEU-3": "Saya adalah seseorang yang santai dan dapat mengatasi stres dengan baik.",
    "EXT-3": "Saya adalah seseorang yang pendiam (atau tertutup).",
    "OPE-2": "Saya adalah seseorang yang menghargai pengalaman artistik.",
    "AGR-3": "Saya adalah seseorang yang penuh perhatian dan baik hati terhadap orang lain.",
    "NEU-2": "Saya adalah seseorang yang mudah gugup.",
    "CON-3": "Saya adalah seseorang yang menyelesaikan tugas secara efektif dan efisien.",
    "EXT-1": "Saya adalah seseorang yang komunikatif dan banyak bicara (atau cerewet)."
}

# Membuat list keys agar urutan soal konsisten
KEYS_BIG5 = list(questions_B.keys())



def render_part_1():
    # --- STYLE CSS UNTUK TAMPILAN COVER ---
    st.markdown("""
    <style>
    /* 1. SETUP DASAR */
    .stApp {
        background-color: #F8F9F1;
    }
    
    /* 2. CONTAINER COVER */
    .cover-container {
        text-align: left;
        /* Desktop: Padding besar agar lega */
        padding: 100px 10% 20px 10%; 
    }
    
    /* 3. TYPOGRAPHY (DESKTOP) */
    .main-title {
        color: #0A0A44;
        font-size: 36px; /* Besar di Desktop */
        font-weight: 800;
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
        line-height: 1.2;
    }
    
    .description {
        color: #2D4A44;
        font-size: 24px; /* Besar di Desktop */
        line-height: 1.5;
        margin-bottom: 30px;
        font-family: 'Inter', sans-serif;
    }
    
    .hint-text {
        color: #4A4A4A;
        font-size: 14px;
        margin-bottom: 5px;
    }
    
    .cta-text {
        color: #4A4A4A;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 30px;
    }

    /* 4. STYLING TOMBOL */
    div.stButton > button {
        background-color: #03043D !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 40px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: 0.3s;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    
    div.stButton > button:hover {
        background-color: #1A1A5E !important;
        transform: scale(1.05);
    }

    .footer-link {
        color: #0A0A44;
        font-size: 13px;
        text-decoration: underline;
        cursor: pointer;
    }

    /* ============================================= */
    /* 5. MEDIA QUERY UNTUK HP (Layar < 600px)       */
    /* ============================================= */
    @media (max-width: 600px) {
        .cover-container {
            /* Kurangi padding atas agar tidak terlalu turun */
            padding: 40px 5% 20px 5% !important; 
        }

        .main-title {
            /* Kecilkan font judul agar muat */
            font-size: 24px !important; 
        }

        .description {
            /* Kecilkan font deskripsi agar enak dibaca */
            font-size: 16px !important; 
        }

        div.stButton > button {
            /* Tombol full width di HP agar mudah ditekan */
            width: 100% !important; 
            padding: 10px 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    st.header("📝 Bagian 1: Karakteristik Wirausaha (Self-Efficacy, Innovativeness, Locus of Control, dan Need for Achievement)")
    
    # --- A. SAFETY CHECK (Profil & Session) ---
    if 'temp_profile' not in st.session_state:
        st.warning("Silakan isi profil terlebih dahulu.")
        if st.button("Kembali ke Profil"):
            st.session_state['halaman_sekarang'] = "profil"
            st.rerun()
        return

    if 'temp_answers_1' not in st.session_state: st.session_state['temp_answers_1'] = {}
    if 'q_index' not in st.session_state: st.session_state['q_index'] = 0

    # --- B. PERSIAPAN DATA SOAL ---
    current_idx = st.session_state['q_index']
    total_soal = len(KEYS_ENTRE)
    current_key = KEYS_ENTRE[current_idx]
    
    # Progress Bar
    progress_val = (current_idx + 1) / total_soal
    st.progress(progress_val, text=f"Pertanyaan {current_idx + 1} dari {total_soal}")

    # Ambil Teks & Nilai Default
    teks_soal = questions_A.get(current_key, f"Pertanyaan {current_key} belum diset.")
    default_val = st.session_state['temp_answers_1'].get(current_key, 3)

    # --- C. TAMPILKAN ITEM KUESIONER (Panggil Fungsi Helper) ---
    # Di sini CSS dan UI dirender otomatis
    jawaban = likert_item(
        question_text=f"{current_idx + 1}. {teks_soal}",
        key_name=f"radio_{current_key}",
        default_value=default_val
    )

    st.write("---")

    # --- D. NAVIGASI & LOGIKA PENYIMPANAN ---
    # Menggunakan layout [2, 10, 2] agar tombol Next mojok kanan (seperti request sebelumnya)
    col_prev, col_space, col_next = st.columns([2, 10, 2])

    # 1. TOMBOL PREV
    with col_prev:
        if current_idx > 0:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state['q_index'] -= 1
                st.rerun()

    # 2. TOMBOL NEXT / FINISH
    with col_next:
        # Jika BELUM soal terakhir
        if current_idx < total_soal - 1:
            if st.button("Next ➡️", type="primary", use_container_width=True):
                # Simpan jawaban sementara ke Session State
                st.session_state['temp_answers_1'][current_key] = jawaban
                st.session_state['q_index'] += 1
                st.rerun()
        
        # Jika SOAL TERAKHIR (Finish)
        else:
            if st.button("Next to second questionnaire 🚀", type="primary", use_container_width=True):
                # 1. Simpan jawaban soal terakhir ini
                st.session_state['temp_answers_1'][current_key] = jawaban
                
                # 2. Ambil ID User dari Session State
                user_id_saya = st.session_state.get('current_user_id')
                
                # Safety Check: ID hilang
                if not user_id_saya:
                    st.error("⚠️ Sesi habis. Silakan isi profil ulang.")
                    if st.button("Ke Profil"):
                        st.session_state['halaman_sekarang'] = 'profil'
                        st.rerun()
                    return

                # 3. UPDATE DATABASE
                try:
                    db = st.session_state['db']
                    # Update jawaban berdasarkan ID
                    db.update_user_answers(user_id_saya, st.session_state['temp_answers_1'])
                    
                    st.success("Jawaban Tersimpan!")
                    
                    # 4. Pindah ke Part 2
                    st.session_state['halaman_sekarang'] = "part_2"
                    st.session_state['q_index'] = 0 # Reset index untuk part 2 (opsional)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

def render_part_2():
    st.markdown("""
    <style>
    /* 1. SETUP DASAR */
    .stApp {
        background-color: #F8F9F1;
    }
    
    /* 2. CONTAINER COVER */
    .cover-container {
        text-align: left;
        /* Desktop: Padding besar agar lega */
        padding: 100px 10% 20px 10%; 
    }
    
    /* 3. TYPOGRAPHY (DESKTOP) */
    .main-title {
        color: #0A0A44;
        font-size: 36px; /* Besar di Desktop */
        font-weight: 800;
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
        line-height: 1.2;
    }
    
    .description {
        color: #2D4A44;
        font-size: 24px; /* Besar di Desktop */
        line-height: 1.5;
        margin-bottom: 30px;
        font-family: 'Inter', sans-serif;
    }
    
    .hint-text {
        color: #4A4A4A;
        font-size: 14px;
        margin-bottom: 5px;
    }
    
    .cta-text {
        color: #4A4A4A;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 30px;
    }

    /* 4. STYLING TOMBOL */
    div.stButton > button {
        background-color: #03043D !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 40px !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: 0.3s;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    
    div.stButton > button:hover {
        background-color: #1A1A5E !important;
        transform: scale(1.05);
    }

    .footer-link {
        color: #0A0A44;
        font-size: 13px;
        text-decoration: underline;
        cursor: pointer;
    }

    /* ============================================= */
    /* 5. MEDIA QUERY UNTUK HP (Layar < 600px)       */
    /* ============================================= */
    @media (max-width: 600px) {
        .cover-container {
            /* Kurangi padding atas agar tidak terlalu turun */
            padding: 40px 5% 20px 5% !important; 
        }

        .main-title {
            /* Kecilkan font judul agar muat */
            font-size: 24px !important; 
        }

        .description {
            /* Kecilkan font deskripsi agar enak dibaca */
            font-size: 16px !important; 
        }

        div.stButton > button {
            /* Tombol full width di HP agar mudah ditekan */
            width: 100% !important; 
            padding: 10px 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    st.header("📝 Bagian 2: Kepribadian (Big 5 Personality)")
    
    # --- A. SAFETY CHECK (Profil & Session) ---
    if 'temp_profile' not in st.session_state:
        st.warning("Silakan isi profil terlebih dahulu.")
        if st.button("Kembali ke Profil"):
            st.session_state['halaman_sekarang'] = "profil"
            st.rerun()
        return

    # Gunakan temp_answers_2 untuk menyimpan jawaban bagian ini
    if 'temp_answers_2' not in st.session_state: st.session_state['temp_answers_2'] = {}
    
    # Pastikan q_index ada (biasanya sudah di-reset di akhir Part 1)
    if 'q_index' not in st.session_state: st.session_state['q_index'] = 0

    # --- B. PERSIAPAN DATA SOAL ---
    current_idx = st.session_state['q_index']
    total_soal = len(KEYS_BIG5)
    
    # Safety check jika index melebihi total soal (misal refresh browser)
    if current_idx >= total_soal:
        current_idx = total_soal - 1
        st.session_state['q_index'] = current_idx

    current_key = KEYS_BIG5[current_idx]
    
    # Progress Bar
    progress_val = (current_idx + 1) / total_soal
    st.progress(progress_val, text=f"Pertanyaan {current_idx + 1} dari {total_soal}")

    # Ambil Teks & Nilai Default
    teks_soal = questions_B.get(current_key, f"Pertanyaan {current_key} belum diset.")
    
    # Ambil nilai dari temp_answers_2, default 3
    default_val = st.session_state['temp_answers_2'].get(current_key, 3)

    # --- C. TAMPILKAN ITEM KUESIONER (Panggil Fungsi Helper) ---
    # Menggunakan likert_item yang sama
    jawaban = likert_item(
        question_text=f"{current_idx + 1}. {teks_soal}",
        key_name=f"radio_{current_key}", 
        default_value=default_val
    )

    st.write("---")

    # --- D. NAVIGASI & LOGIKA PENYIMPANAN ---
    col_prev, col_space, col_next = st.columns([2, 10, 2])

    # 1. TOMBOL PREV
    with col_prev:
        if current_idx > 0:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state['q_index'] -= 1
                st.rerun()

    # 2. TOMBOL NEXT / FINISH
    with col_next:
        # Jika BELUM soal terakhir
        if current_idx < total_soal - 1:
            if st.button("Next ➡️", type="primary", use_container_width=True):
                # Simpan jawaban sementara ke temp_answers_2
                st.session_state['temp_answers_2'][current_key] = jawaban
                st.session_state['q_index'] += 1
                st.rerun()
        
        # Jika SOAL TERAKHIR (Finish)
        else:
            # Tombol Finalisasi
            if st.button("Lihat Hasil 🏁", type="primary", use_container_width=True):
                # 1. Simpan jawaban soal terakhir ini
                st.session_state['temp_answers_2'][current_key] = jawaban
                
                # 2. Ambil ID User
                user_id_saya = st.session_state.get('current_user_id')
                
                # Safety Check
                if not user_id_saya:
                    st.error("⚠️ Sesi habis. Silakan isi profil ulang.")
                    if st.button("Ke Profil"):
                        st.session_state['halaman_sekarang'] = 'profil'
                        st.rerun()
                    return

                # 3. UPDATE DATABASE (Simpan Jawaban Part 2)
                try:
                    db = st.session_state['db']
                    
                    # Update database dengan jawaban Part 2
                    db.update_user_answers(user_id_saya, st.session_state['temp_answers_2'])
                    
                    st.success("Semua Jawaban Tersimpan!")
                    
                    # 4. Pindah ke Halaman Hasil / Processing
                    # Anda harus membuat logic render_hasil() atau similar nanti
                    st.session_state['halaman_sekarang'] = "hasil_single" 
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

def render_feedback_section(user_id, db, sectors_single, sectors_hybrid):
    """
    Function khusus untuk menangani tampilan dan logika Feedback.
    Dipanggil di dalam dashboard perbandingan.
    """
    st.write("---")
    st.header("📝 Feedback Pengguna")
    st.info("Mohon bantu kami menilai metode mana yang memberikan rekomendasi paling akurat untuk Anda.")

    with st.container(border=True):
        with st.form("feedback_form"):
            # A. Input User
            # Buat 2 Kolom agar sejajar dengan tampilan hasil (Single Kiri, Hybrid Kanan)
            col_f1, col_f2 = st.columns(2, gap="medium")

            # --- PERTANYAAN 1 & 2: SINGLE METHOD ---
            with col_f1:
                st.markdown("### Single Method")
                
                # 1. Rating Single
                rate_single = st.radio(
                    "Secara keseluruhan, seberapa akurat rekomendasi Single Method?",
                    options=[1, 2, 3, 4, 5],
                    index=None,           # Default pilih angka 3 (Index dimulai dari 0, jadi 0=1, 1=2, 2=3)
                    horizontal=True,   # PENTING: Agar menyamping
                    key="rate_single",
                    # Format tampilan agar user tahu arti angkanya
                )
                st.caption("ℹ️ **1**: Kurang Akurat — **5**: Sangat Akurat")
                
                # 2. PILIH SEKTOR (MULTISELECT) - BARU
                st.write("2. Mana rekomendasi yang paling sesuai dengan preferensi/minat Anda? (Bisa memilih lebih dari 1)")
                if sectors_single:
                    chosen_s_list = st.multiselect(
                        "Pilih Sektor Single",
                        options=sectors_single, # Opsi diambil dari hasil rekomendasi
                        placeholder="Klik untuk memilih sektor...",
                        label_visibility="collapsed",
                        key="chosen_single"
                    )
                    if not chosen_s_list:
                        st.caption("*(Biarkan kosong jika tidak ada yang cocok)*")
                else:
                    st.caption("*(Tidak ada rekomendasi tampil)*")
                    chosen_s_list = []

                # 2. Alasan Single
                feedback_single = st.text_area(
                    "Apa masukan/pendapat Anda terkait sistem rekomendasi ini?",
                    height=100,
                    key="feedback_single"
                )

            # --- PERTANYAAN 3 & 4: HYBRID METHOD ---
            with col_f2:
                st.markdown("### Hybrid Method")

                # 3. Rating Hybrid
                rate_hybrid = st.radio(
                    "Secara keseluruhan, seberapa akurat rekomendasi Hybrid Method?",
                    options=[1, 2, 3, 4, 5],
                    index=None,           # Default pilih angka 3 (Index dimulai dari 0, jadi 0=1, 1=2, 2=3)
                    horizontal=True,   # PENTING: Agar menyamping
                    key="rate_hybrid",
                    # Format tampilan agar user tahu arti angkanya
                )
                st.caption("ℹ️ **1**: Kurang Akurat — **5**: Sangat Akurat")

                # 2. PILIH SEKTOR (MULTISELECT) - BARU
                st.write("2. Mana rekomendasi yang paling sesuai dengan preferensi/minat Anda? (Bisa memilih lebih dari 1)")
                if sectors_hybrid:
                    chosen_h_list = st.multiselect(
                        "Pilih Sektor Hybrid",
                        options=sectors_hybrid, # Opsi diambil dari hasil rekomendasi
                        placeholder="Klik untuk memilih sektor...",
                        label_visibility="collapsed",
                        key="chosen_hybrid"
                    )
                    if not chosen_h_list:
                        st.caption("*(Biarkan kosong jika tidak ada yang cocok)*")
                else:
                    st.caption("*(Tidak ada rekomendasi tampil)*")
                    chosen_h_list = []

                # 4. Alasan Hybrid
                feedback_hybrid = st.text_area(
                    "Apa masukan/pendapat Anda terkait sistem rekomendasi ini?",
                    height=100,
                    key="feedback_hybrid"
                )

            # B. Tombol Submit
            submit_feedback = st.form_submit_button("💾 Kirim Feedback", type="primary", use_container_width=True)

            # C. Logika Penyimpanan ke DB
            if submit_feedback:
                if not rate_single or not feedback_single or not rate_hybrid or not feedback_hybrid:
                    st.warning("⚠️ Harap diisi seluruh pertanyaan feedback.")
                    
                else:
                    try:
                        # --- Konversi List menjadi String ---
                        str_chosen_s = ", ".join(chosen_s_list) if chosen_s_list else ""
                        str_chosen_h = ", ".join(chosen_h_list) if chosen_h_list else ""
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        
                        # Update tabel mst_tbl
                        cursor.execute("""
                            UPDATE mst_tbl 
                            SET rate_single = %s, 
                                chosen_s_list = %s,
                                feedback_single = %s, 
                                rate_hybrid = %s, 
                                chosen_h_list = %s,
                                feedback_hybrid = %s
                            WHERE user_id = %s
                        """, (rate_single, str_chosen_s, feedback_single, rate_hybrid, str_chosen_h, feedback_hybrid, user_id))
                        
                        conn.commit()
                        conn.close()
                        st.success("✅ Terima kasih! Feedback Anda berhasil disimpan.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Gagal menyimpan feedback: {e}")

# deskripsi
@st.cache_data
def load_cluster_descriptions(file_path='deskripsi.xlsx'):
    try:
        # Hanya baca sheet 'Cluster_Desc'
        df = pd.read_excel(file_path, sheet_name='cluster')
        
        # Bersihkan nama kolom
        df.columns = [c.strip() for c in df.columns]
        
        # Ubah ke Dictionary
        # Key biarkan apa adanya (Sensitive) atau strip saja, karena nama cluster spesifik
        cluster_dict = dict(zip(
            df['Cluster'].astype(str).str.strip(), 
            df['Description']
        ))
        return cluster_dict
        
    except Exception as e:
        # st.error(f"Gagal load cluster: {e}")
        return {}

@st.cache_data # supaya file tidak dibaca berulang kali saat klik
def load_sector_descriptions(file_path='deskripsi.xlsx'):
    try:
        # Baca Excel
        df = pd.read_excel(file_path, sheet_name='sektor')
        
        # Pastikan nama kolom sesuai (bersihkan spasi jika ada)
        df.columns = [c.strip() for c in df.columns]
        
        # Ubah menjadi Dictionary: {'Nama Sektor': 'Deskripsi Panjang...'}
        # Kita gunakan .title() pada Key agar seragam formatnya
        sector_dict = dict(zip(
        df['Sector'].astype(str).str.title().str.strip(), 
        df['Description']
    ))
        
        return sector_dict
    except Exception as e:
        st.error(f"Gagal membaca file deskripsi: {e}")
        return {}

class RecommenderEngine:
    """Class untuk menangani perhitungan skor & dimensi"""
    def __init__(self):
        # --- 1. CONFIG PART A (ENTREPRENEUR) ---
        self.domain_cols = {
        "innovativeness":  ["INN-CE1", "INN-O2", "INN-W1", "INN-CE2", "INN-W2", "INN-O1"],
        "self_efficacy":   ["SE-M1", "SE-P2", "SE-IP1", "SE-IF1", "SE-S1", "SE-IF2", "SE-M2", "SE-S2", "SE-P1", "SE-IP2"],
        "need_achievement": ["NACH-FF2", "NACH-HS1", "NACH-HS2", "NACH-FF1"],
        "loc_internal":  ["LOC-I1", "LOC-I2"],
        "loc_external": ["LOC-E1", "LOC-E2"]
    }
        # Mapping Score Kategori ke Angka (0-3) untuk Euclidean Distance Part A
        self.score_map = {"low": 0, "mid-low": 1, "mid-high": 2, "high": 3}
        self.loc_map = {"external": 0, "internal": 1}
        
        # Rules Fuzzy Matching (Sektor Kandidat)
        self.rules = {
            "self_efficacy": {
                "high": ["Consumer Oriented Services", "Construction", "Non-High Tech Manufacturing", "Software", "Other Business Services", "Cutting-Edge Technology Manufacturing", "High Technology Manufacturing"],
                "mid-high": ["Skill-Intensive Services"],
                "mid-low": ["Wholesale And Retail Market", "Technology Intensive Services"],
                "low": []
            },
            "innovativeness": {
                "high": ["Non-High Tech Manufacturing", "High Technology Manufacturing", "Software", "Technology Intensive Services", "Cutting-Edge Technology Manufacturing"],
                "mid-high": ["Consumer Oriented Services"],
                "mid-low": ["Construction", "Wholesale And Retail Market", "Skill-Intensive Services", "Other Business Services"],
                "low": []
            },
            "need_achievement": {
                "high": ["Consumer Oriented Services", "Skill-Intensive Services", "Software", "Technology Intensive Services", "Cutting-Edge Technology Manufacturing", "High Technology Manufacturing"],
                "mid-high": ["Construction", "Non-High Tech Manufacturing", "Other Business Services"],
                "mid-low": [],
                "low": ["Wholesale And Retail Market"]
            },
            "loc": {
                "internal": ["Consumer Oriented Services", "Non-High Tech Manufacturing", "High Technology Manufacturing", "Software", "Technology Intensive Services", "Skill-Intensive Services", "Other Business Services", "Cutting-Edge Technology Manufacturing"],
                "external": ["Construction", "Wholesale And Retail Market"]
            }
        }
        # Prototype Sektor (Target Vector Part A)
        # Urutan Vector: [SE, INN, NACH, LOC]
        self.sector_proto = {
        "Consumer Oriented Services":           [3, 2, 3, 1],
        "Construction":                        [3, 1, 2, 0],
        "Wholesale And Retail Market":         [1, 1, 0, 0],
        "Non-High Tech Manufacturing":         [3, 3, 2, 1],
        "Skill-Intensive Services":            [2, 1, 3, 1],
        "Other Business Services":             [3, 1, 2, 1],
        "High Technology Manufacturing":       [3, 3, 3, 1],
        "Software":                            [3, 3, 3, 1],
        "Technology Intensive Services":       [1, 3, 3, 1],
        "Cutting-Edge Technology Manufacturing":[3, 3, 3, 1]
        }
    
        # Cluster Mapping (Sektor -> Cluster)
        self.cluster_mapping = {
        "Adaptive Services": [
            "Wholesale And Retail Market", "Consumer Oriented Services",
            "Non-High Tech Manufacturing", "Other Business Services"
        ],
        "Dynamic Knowledge Innovators": [
            "Skill-Intensive Services", "Technology Intensive Services",
            "Software", "High Technology Manufacturing"
        ],
        "Strategic Risk Navigators": [
            "Technology Intensive Services", "Skill-Intensive Services",
            "Other Business Services"
        ],
        "Multidimensional Service Innovators": [
            "Consumer Oriented Services", "Skill-Intensive Services",
            "Construction", "Wholesale And Retail Market",
            "Technology Intensive Services"
        ],
        "Focused Tech Innovators": [
            "Non-High Tech Manufacturing", "Other Business Services",
            "Software", "High Technology Manufacturing"
        ]
    }
        # --- 2. CONFIG PART B (BIG 5) ---
        # Definisi soal mana yang Normal dan mana yang Reverse
        self.big5 = {
            "openess": ["OPE-1", "OPE-2", "OPE-3"], # Semua normal di notebook Anda
            "conscientiousness": {"normal": ["CON-1", "CON-3"], "reverse": ["CON-2"]},
            "extraversion": {"normal": ["EXT-1", "EXT-2"], "reverse": ["EXT-3"]},
            "agreeableness": {"normal": ["AGR-2", "AGR-3"], "reverse": ["AGR-1"]},
            "neuroticism": {"normal": ["NEU-1", "NEU-2"], "reverse": ["NEU-3"]}
        }

         # Konversi Simbol ke Angka
        self.symbol_to_num = {'++': 2.0, '+': 1.0, '0': 0.0, '-': -1.0, '--': -2.0}

        # Rule Cluster Big 5 (Simbol Target)
        self.big5_cluster_rules = {
            'Adaptive Services': {
                'O':'++', 'C':'0/+', 'E':'+',  'A':'0',    'N':'--'
            },
            'Dynamic Knowledge Innovators': {
                'O':'++', 'C':'-',   'E':'++', 'A':'-',    'N':'--'
            },
            'Strategic Risk Navigators': {
                'O':'++', 'C':'-',   'E':'+',  'A':'-',    'N':'--'
            },
            'Multidimensional Service Innovators': {
                'O':'++','C':'-/+','E':'0/++', 'A':'--/0','N':'--/+'
            },
            'Focused Tech Innovators': {
                'O':'++','C':'-','E':'-/+','A':'0/+','N':'-'
            }
        }
        
        self.cluster_protos = {
            name: self.cluster_proto_numeric(sig) 
            for name, sig in self.big5_cluster_rules.items()
        }
        
        # --- HYBRID ---

        # 4 DOMAIN KEWIRAUSAHAAN
        self.likert_text_map = {
            "SE-S1": { # Self-Efficacy A. Searching (yakin bisa menemukan peluang usaha)
                1: "Saya sangat tidak percaya diri dalam mengidentifikasi kebutuhan atau peluang baru untuk dijadikan produk, layanan, atau solusi.",
                2: "Saya tidak percaya diri dapat mengidentifikasi kebutuhan atau peluang baru yang bisa dikembangkan menjadi produk, layanan, atau solusi.",
                3: "Saya cukup percaya diri, namun belum konsisten, dalam mengidentifikasi kebutuhan atau peluang baru untuk diwujudkan menjadi produk, layanan, atau solusi.",
                4: "Saya percaya diri dalam mengidentifikasi kebutuhan atau peluang baru yang dapat dikembangkan menjadi produk, layanan, atau solusi.",
                5: "Saya sangat percaya diri dan merasa mampu secara konsisten mengidentifikasi kebutuhan atau peluang baru yang bisa diwujudkan menjadi produk, layanan, atau solusi."
            },
            "SE-S2": { # Self-Efficacy A. Searching (merancang ide/solusi baru)
                1: "Saya sangat tidak percaya diri dalam merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar.",
                2: "Saya tidak percaya diri dapat merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar.",
                4: "Saya percaya diri dalam merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar.",
                5: "Saya sangat percaya diri dan merasa mampu secara konsisten merancang ide atau solusi baru yang sesuai dengan kebutuhan pasar."
            },
            "SE-P1": { # Self-Efficacy B. Planning (menyusun rencana bisnis)
                1: "Saya sangat tidak percaya diri dalam menyusun rencana bisnis, termasuk memperkirakan permintaan pasar dan merancang strategi pemasaran.",
                2: "Saya tidak percaya diri dapat menyusun rencana bisnis, memperkirakan permintaan pasar, atau membuat strategi pemasaran.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam menyusun rencana bisnis serta memperkirakan permintaan pasar dan strategi pemasaran.",
                4: "Saya percaya diri dapat menyusun rencana bisnis, termasuk memperkirakan permintaan pasar dan strategi pemasaran.",
                5: "Saya sangat percaya diri dan merasa mampu secara konsisten menyusun rencana bisnis, memperkirakan permintaan pasar, serta mengembangkan strategi pemasaran."
            },
            "SE-P2": { # Self-Efficacy B. Planning (memperkirakan modal)
                1: "Saya sangat tidak percaya diri dalam memperkirakan jumlah modal awal maupun modal kerja yang dibutuhkan untuk memulai atau menjalankan usaha, proyek, atau kegiatan baru.",
                2: "Saya tidak percaya diri dapat memperkirakan modal awal dan modal kerja yang diperlukan untuk memulai atau menjalankan usaha, proyek, atau kegiatan baru.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam memperkirakan jumlah modal awal dan modal kerja yang diperlukan untuk memulai atau menjalankan usaha, proyek, atau kegiatan baru.",
                4: "Saya percaya diri dapat memperkirakan jumlah modal awal dan modal kerja yang diperlukan untuk memulai atau menjalankan usaha, proyek, atau kegiatan baru.",
                5: "Saya sangat percaya diri dan merasa mampu secara konsisten memperkirakan jumlah modal awal dan modal kerja yang diperlukan untuk memulai atau menjalankan usaha, proyek, atau kegiatan baru."
            },
            "SE-M1": { # Self-Efficacy C. Marshalling (networking)
                1: "Saya sangat tidak percaya diri dalam melakukan networking, termasuk membangun hubungan dan bertukar informasi yang bermanfaat dengan berbagai pihak untuk mendukung kegiatan atau proyek saya.",
                2: "Saya tidak percaya diri dapat melakukan networking atau membangun hubungan yang bermanfaat dengan berbagai pihak untuk mendukung kegiatan atau proyek saya.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam melakukan networking dan membangun hubungan serta bertukar informasi yang bermanfaat dengan berbagai pihak.",
                4: "Saya percaya diri dapat melakukan networking, membangun hubungan, dan bertukar informasi yang bermanfaat dengan berbagai pihak untuk mendukung kegiatan atau proyek saya.",
                5: "Saya sangat percaya diri dan mampu secara konsisten melakukan networking, membangun hubungan, serta bertukar informasi yang bermanfaat dengan berbagai pihak untuk mendukung kegiatan atau proyek saya."
            },
            "SE-M2": { # Self-Efficacy C. Marshalling (meyakinkan orang lain)
                1: "Saya sangat tidak percaya diri dalam meyakinkan orang lain untuk memahami, mendukung, atau berkomitmen pada visi dan rencana yang saya buat.",
                2: "Saya tidak percaya diri dapat meyakinkan orang lain agar memahami, mendukung, dan ikut berkomitmen pada visi serta rencana yang saya buat.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam meyakinkan orang lain untuk memahami, mendukung, dan berkomitmen pada visi serta rencana saya.",
                4: "Saya percaya diri dapat meyakinkan orang lain untuk memahami, mendukung, dan ikut berkomitmen pada visi serta rencana yang saya buat.",
                5: "Saya sangat percaya diri dan mampu secara konsisten meyakinkan orang lain untuk memahami, mendukung, serta berkomitmen pada visi dan rencana yang saya buat."
            },
            "SE-IP1": { # Self-Efficacy D. Implementing-people (memotivasi tim)
                1: "Saya tidak percaya diri bahwa saya mampu memotivasi atau mendorong anggota tim untuk tetap semangat dalam bekerja.",
                2: "Saya kurang percaya diri bahwa saya dapat memotivasi anggota tim agar tetap semangat dalam bekerja.",
                3: "Saya merasa cukup percaya diri, tetapi belum tentu selalu bisa memotivasi anggota tim agar tetap semangat dalam bekerja.",
                4: "Saya percaya diri bahwa saya mampu memotivasi dan mendorong anggota tim untuk tetap semangat dalam bekerja.",
                5: "Saya sangat percaya diri bahwa saya dapat memotivasi dan mendorong anggota tim sehingga mereka tetap bersemangat dalam bekerja."
            },
            "SE-IP2": { # Self-Efficacy D. Implementing-people (memilih orang tepat)
                1: "Saya sangat tidak percaya diri dalam memilih orang yang tepat untuk bekerja sama maupun membantu mereka mengembangkan kemampuan yang dibutuhkan.",
                2: "Saya tidak percaya diri dapat memilih orang yang tepat untuk bekerja sama atau membantu mereka mengembangkan kemampuan yang diperlukan.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam memilih orang yang tepat untuk bekerja sama dan membantu mereka mengembangkan kemampuan yang dibutuhkan.",
                4: "Saya percaya diri dapat memilih orang yang tepat untuk bekerja sama serta membantu mereka mengembangkan kemampuan yang dibutuhkan.",
                5: "Saya sangat percaya diri dan mampu secara konsisten memilih orang yang tepat untuk bekerja sama serta membantu mereka mengembangkan kemampuan yang dibutuhkan."
            },
            "SE-IF1": { # Self-Efficacy E. Implementing-finance (mengorganisir catatan keuangan)
                1: "Saya sangat tidak percaya diri dalam mengorganisir atau memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan.",
                2: "Saya tidak percaya diri dapat mengorganisir dan memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam mengorganisir dan memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan.",
                4: "Saya percaya diri dapat mengorganisir dan memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan.",
                5: "Saya sangat percaya diri dan mampu secara konsisten mengorganisir serta memelihara catatan keuangan untuk usaha, proyek, atau kegiatan yang saya jalankan."
            },
            "SE-IF2": { # Self-Efficacy E. Implementing-finance (mengelola aset/sumber daya keuangan)
                1: "Saya sangat tidak percaya diri dalam mengelola aset atau sumber daya keuangan secara efektif untuk usaha, proyek, atau kegiatan saya.",
                2: "Saya tidak percaya diri dapat mengelola aset atau sumber daya keuangan secara efektif dalam usaha, proyek, atau kegiatan saya.",
                3: "Saya cukup percaya diri, tetapi belum konsisten, dalam mengelola aset atau sumber daya keuangan secara efektif untuk usaha, proyek, atau kegiatan saya.",
                4: "Saya percaya diri dapat mengelola aset atau sumber daya keuangan secara efektif dalam usaha, proyek, atau kegiatan saya.",
                5: "Saya sangat percaya diri dan mampu secara konsisten mengelola aset atau sumber daya keuangan secara efektif dalam usaha, proyek, atau kegiatan saya."
            },
            "INN-O1": { # Innovativeness A. Openness to new ideas (menikmati ide baru)
                1: "Saya sangat tidak menikmati mencoba ide-ide baru.",
                2: "Saya tidak menikmati mencoba ide-ide baru.",
                3: "Saya kadang menikmati, tetapi tidak selalu, ketika mencoba ide-ide baru.",
                4: "Saya menikmati mencoba ide-ide baru.",
                5: "Saya sangat menikmati dan merasa antusias ketika mencoba ide-ide baru."
            },
            "INN-O2": { # Innovativeness A. Openness to new ideas (terbuka cara baru)
                1: "Saya sangat tidak terbuka untuk menggunakan cara baru, terutama jika cara tersebut belum umum dipraktikkan orang lain.",
                2: "Saya tidak terbuka untuk menggunakan cara baru yang belum umum dipraktikkan orang lain.",
                3: "Saya cukup terbuka, tetapi tidak selalu, untuk menggunakan cara baru meskipun belum umum dipraktikkan orang lain.",
                4: "Saya terbuka untuk menggunakan cara baru meskipun cara tersebut belum umum dipraktikkan orang lain.",
                5: "Saya sangat terbuka dan dengan mudah menerima cara baru meskipun belum umum dipraktikkan orang lain."
            },
            "INN-W1": { # Innovativeness B. Willingness to change (bersedia coba cara baru)
                1: "Saya sangat tidak bersedia mencoba cara baru, terutama jika berbeda dari kebiasaan saya sebelumnya.",
                2: "Saya tidak bersedia mencoba cara baru yang berbeda dari kebiasaan saya sebelumnya.",
                3: "Saya kadang bersedia, tetapi tidak selalu, mencoba cara baru meskipun berbeda dari kebiasaan saya sebelumnya.",
                4: "Saya bersedia mencoba cara baru meskipun berbeda dari kebiasaan saya sebelumnya.",
                5: "Saya sangat bersedia dan nyaman mencoba cara baru meskipun berbeda dari kebiasaan atau pola yang biasa saya lakukan."
            },
            "INN-W2": { # Innovativeness B. Willingness to change (antusias adaptasi)
                1: "Saya sangat tidak merasa antusias ketika harus beradaptasi dengan situasi baru; justru saya cenderung menghindarinya.",
                2: "Saya tidak merasa antusias ketika harus beradaptasi dengan situasi baru.",
                3: "Saya kadang merasa antusias, tetapi tidak selalu, ketika harus beradaptasi dengan situasi baru.",
                4: "Saya merasa antusias ketika harus beradaptasi dengan situasi baru.",
                5: "Saya sangat merasa antusias dan justru bersemangat ketika harus beradaptasi dengan situasi baru."
            },
            "INN-CE1": { # Innovativeness C. Curiosity & experimentation (tertantang ketidakpastian)
                1: "Saya sangat tidak merasa tertantang oleh ketidakpastian atau masalah yang belum terpecahkan; justru saya menghindarinya.",
                2: "Saya tidak merasa tertantang oleh ketidakpastian dan masalah yang belum terpecahkan.",
                3: "Saya kadang merasa tertantang, tetapi tidak selalu, oleh ketidakpastian dan masalah yang belum terpecahkan.",
                4: "Saya merasa tertantang oleh ketidakpastian dan masalah yang belum terpecahkan.",
                5: "Saya sangat merasa tertantang dan justru termotivasi oleh ketidakpastian serta masalah yang belum terpecahkan."
            },
            "INN-CE2": { # Innovativeness C. Curiosity & experimentation (mengimprovisasi metode)
                1: "Saya sangat jarang atau tidak pernah mengimprovisasi metode ketika memecahkan masalah yang jawabannya tidak jelas.",
                2: "Saya jarang mengimprovisasi metode untuk memecahkan masalah ketika jawabannya tidak jelas.",
                3: "Saya kadang-kadang mengimprovisasi metode untuk memecahkan masalah ketika jawabannya tidak jelas.",
                4: "Saya sering mengimprovisasi metode untuk memecahkan masalah ketika jawabannya tidak jelas.",
                5: "Saya sangat sering dan secara alami mengimprovisasi metode untuk memecahkan masalah ketika jawabannya tidak jelas."
            },
            "LOC-I1": { # Locus of Control A. Internal (bekerja sungguh-sungguh)
                1: "Saya merasa bahwa meskipun saya bekerja dengan sungguh-sungguh, saya tetap tidak bisa mencapai hasil yang saya inginkan.",
                2: "Saya menilai bahwa bekerja dengan sungguh-sungguh tidak selalu membuat saya mencapai hasil yang saya inginkan.",
                3: "Saya merasa bekerja dengan sungguh-sungguh kadang membantu, tetapi tidak selalu memastikan saya mendapat hasil yang saya inginkan.",
                4: "Saya meyakini bahwa bekerja dengan sungguh-sungguh biasanya membuat saya mencapai hasil yang saya inginkan.",
                5: "Saya sangat yakin bahwa jika saya bekerja dengan sungguh-sungguh, saya pasti bisa mencapai hasil yang saya inginkan."
            },
            "LOC-I2": { # Locus of Control A. Internal (hasil bergantung pada usaha)
                1: "Saya merasa hasil pekerjaan saya hampir tidak ada hubungannya dengan usaha atau cara saya bekerja.",
                2: "Saya menilai usaha dan cara saya bekerja tidak terlalu menentukan hasil pekerjaan saya.",
                3: "Saya merasa usaha dan cara saya bekerja kadang berpengaruh, kadang tidak terhadap hasil pekerjaan saya.",
                4: "Saya meyakini bahwa usaha dan cara saya bekerja umumnya menentukan hasil pekerjaan saya.",
                5: "Saya sangat yakin bahwa hasil pekerjaan saya sepenuhnya bergantung pada usaha dan cara saya bekerja."
            },
            "LOC-E1": { # Locus of Control B. External (keberhasilan ditentukan faktor luar)
                1: "Saya sangat tidak merasa bahwa keberhasilan dalam pekerjaan ditentukan oleh faktor di luar kendali saya; saya percaya keberhasilan terutama berasal dari usaha dan tindakan saya sendiri.",
                2: "Saya tidak merasa bahwa keberhasilan dalam pekerjaan banyak ditentukan oleh faktor di luar kendali saya.",
                3: "Saya kadang merasa demikian, tetapi tidak selalu; sebagian keberhasilan menurut saya dipengaruhi faktor luar, sebagian dipengaruhi usaha saya.",
                4: "Saya merasa bahwa keberhasilan dalam pekerjaan banyak ditentukan oleh faktor di luar kendali saya.",
                5: "Saya sangat merasa bahwa keberhasilan dalam pekerjaan terutama ditentukan oleh faktor-faktor di luar kendali saya."
            },
            "LOC-E2": { # Locus of Control B. External (hasil kerja dipengaruhi orang lain)
                1: "Saya sangat tidak percaya bahwa hasil kerja saya terutama dipengaruhi oleh keadaan atau orang lain; saya meyakini bahwa usaha saya adalah faktor utamanya.",
                2: "Saya tidak percaya bahwa hasil kerja saya banyak dipengaruhi oleh keadaan atau orang lain.",
                3: "Saya cukup percaya, tetapi tidak sepenuhnya yakin, bahwa hasil kerja saya dipengaruhi oleh keadaan atau orang lain.",
                4: "Saya percaya bahwa hasil kerja saya banyak dipengaruhi oleh keadaan atau orang lain.",
                5: "Saya sangat percaya bahwa hasil kerja saya terutama dipengaruhi oleh keadaan atau orang lain, bukan oleh usaha saya sendiri."
            },
            "NACH-HS1": { # Need for Achievement A. Hope of Success (termotivasi segera bertindak)
                1: "Saya sangat tidak termotivasi untuk segera bertindak ketika menghadapi tantangan, bahkan jika tantangan tersebut bisa saya selesaikan.",
                2: "Saya tidak termotivasi untuk segera bertindak ketika menghadapi tantangan yang bisa saya selesaikan.",
                3: "Saya kadang termotivasi, tetapi tidak selalu, untuk segera bertindak ketika menghadapi tantangan yang bisa saya selesaikan.",
                4: "Saya termotivasi untuk segera bertindak ketika menghadapi tantangan yang bisa saya selesaikan.",
                5: "Saya sangat termotivasi dan langsung terdorong untuk mengambil tindakan ketika menghadapi tantangan yang bisa saya selesaikan."
            },
            "NACH-HS2": { # Need for Achievement A. Hope of Success (menikmati pengembangan kemampuan)
                1: "Saya sangat tidak menikmati situasi di mana saya bisa menggunakan dan mengembangkan kemampuan saya.",
                2: "Saya tidak menikmati situasi di mana saya bisa menggunakan dan mengembangkan kemampuan saya.",
                3: "Saya kadang menikmati, tetapi tidak selalu, situasi di mana saya bisa menggunakan dan mengembangkan kemampuan saya.",
                4: "Saya menikmati situasi di mana saya bisa menggunakan dan mengembangkan kemampuan saya.",
                5: "Saya sangat menikmati dan merasa bersemangat dalam situasi di mana saya dapat menggunakan sekaligus mengembangkan kemampuan saya."
            },
            "NACH-FF1": { # Need for Achievement B. Fear of Failure (takut gagal)
                1: "Saya sangat tidak merasa takut gagal, bahkan dalam situasi sulit ketika banyak hal bergantung pada saya.",
                2: "Saya tidak merasa takut gagal dalam situasi agak sulit ketika banyak hal bergantung pada saya.",
                3: "Saya kadang merasa takut gagal, namun tidak selalu, dalam situasi agak sulit ketika banyak hal bergantung pada saya.",
                4: "Saya merasa takut gagal dalam situasi agak sulit ketika banyak hal bergantung pada saya.",
                5: "Saya sangat merasa takut gagal dalam situasi agak sulit ketika banyak hal bergantung pada saya."
            },
            "NACH-FF2": { # Need for Achievement B. Fear of Failure (merasa cemas)
                1: "Saya sangat tidak merasa cemas ketika tidak langsung mengerti sebuah masalah.",
                2: "Saya tidak merasa cemas meskipun tidak langsung mengerti sebuah masalah.",
                3: "Saya kadang merasa cemas, tetapi tidak selalu, ketika saya tidak langsung mengerti sebuah masalah.",
                4: "Saya merasa cemas ketika saya tidak langsung mengerti sebuah masalah.",
                5: "Saya sangat merasa cemas ketika tidak langsung mengerti sebuah masalah."
            }
        }



        self.qb_text_mapping = {
            "OPE-1": { # Saya adalah seseorang yang orisinil dan membawa ide-ide baru [cite: 370, 371]
                1: "Saya tidak merasa diri saya orisinil dan jarang membawa ide-ide baru.", # [cite: 371]
                2: "Saya kadang merasa sulit untuk menghasilkan ide baru dan tidak selalu menunjukkan keorisinalan.", # [cite: 372]
                3: "Saya sesekali menunjukkan keorisinalan dan terkadang membawa ide-ide baru.", # [cite: 373]
                4: "Saya sering menunjukkan keorisinalan dan sering membawa ide-ide baru.", # [cite: 373]
                5: "Saya sangat orisinil dan secara konsisten membawa ide-ide baru." # [cite: 374]
            },
            "OPE-2": { # Saya adalah seseorang yang menghargai pengalaman artistik [cite: 375]
                1: "Saya tidak menghargai pengalaman artistik dan jarang merasa tertarik pada hal-hal yang bersifat seni.", # [cite: 375]
                2: "Saya kurang menghargai pengalaman artistik dan tidak sering merasa terlibat dalam kegiatan atau apresiasi seni.", # [cite: 376]
                3: "Saya kadang-kadang menghargai pengalaman artistik, tergantung situasi atau konteksnya.", # [cite: 377]
                4: "Saya sering menghargai pengalaman artistik dan menikmati berbagai bentuk kegiatan atau karya seni.", # [cite: 377]
                5: "Saya sangat menghargai pengalaman artistik dan secara konsisten menikmati serta mencari kesempatan untuk terlibat dalam seni." # [cite: 378]
            },
            "OPE-3": { # Saya adalah seseorang yang memiliki imajinasi yang jelas/hidup (atau kaya) dan penuh fantasi [cite: 379, 380]
                1: "Saya tidak memiliki imajinasi yang hidup dan jarang membayangkan hal-hal secara kreatif atau fantastis.", # [cite: 381]
                2: "Saya memiliki imajinasi yang kurang hidup dan tidak sering berfantasi atau membayangkan hal-hal secara mendetail.", # [cite: 382]
                3: "Saya memiliki imajinasi yang kadang-kadang hidup, dan sesekali membayangkan hal-hal secara kreatif atau fantastis.", # [cite: 383]
                4: "Saya memiliki imajinasi yang cukup hidup dan sering membayangkan hal-hal secara kreatif dan penuh fantasi.", # [cite: 384]
                5: "Saya memiliki imajinasi yang sangat hidup dan kaya, serta secara konsisten membayangkan hal-hal secara kreatif, mendetail, dan penuh fantasi." # [cite: 385]
            },
            "CON-1": { # Saya adalah seseorang yang bekerja secara teliti (atau menyeluruh) [cite: 386]
                1: "Saya tidak teliti dalam bekerja dan sering melewatkan detail penting.", # [cite: 387]
                2: "Saya kurang teliti dan kadang melewatkan beberapa detail dalam pekerjaan.", # [cite: 387]
                3: "Saya kadang-kadang teliti, tetapi tidak selalu konsisten dalam memperhatikan detail.", # [cite: 388]
                4: "Saya biasanya bekerja dengan teliti dan umumnya memperhatikan detail dengan baik.", # [cite: 389]
                5: "Saya sangat teliti dan selalu memperhatikan setiap detail secara menyeluruh dalam pekerjaan." # [cite: 390]
            },
            "CON-2": { # Saya adalah seseorang yang cenderung malas (atau agak malas) [cite: 391]
                1: "Saya tidak merasa malas dan selalu berusaha aktif dalam menyelesaikan pekerjaan.", # [cite: 391]
                2: "Saya jarang merasa malas dan biasanya tetap berinisiatif untuk menyelesaikan tugas.", # [cite: 392]
                3: "Saya kadang-kadang merasa malas, tetapi hal itu tidak terlalu sering mempengaruhi pekerjaan saya.", # [cite: 393]
                4: "Saya sering merasa malas dan hal itu kadang membuat saya menunda pekerjaan.", # [cite: 394]
                5: "Saya sangat cenderung malas dan sering menunda atau menghindari pekerjaan yang seharusnya saya lakukan." # [cite: 395]
            },
            "CON-3": { # Saya adalah seseorang yang menyelesaikan tugas secara efektif dan efisien [cite: 396]
                1: "Saya tidak menyelesaikan tugas secara efektif dan efisien, dan sering membutuhkan waktu lebih lama dari yang diperlukan.", # [cite: 397]
                2: "Saya kurang efektif dan efisien dalam menyelesaikan tugas dan kadang bekerja lebih lambat dari yang seharusnya.", # [cite: 398]
                3: "Saya kadang efektif dan efisien, tetapi tidak selalu konsisten dalam menyelesaikan tugas.", # [cite: 399]
                4: "Saya biasanya menyelesaikan tugas dengan efektif dan efisien dan mampu mengatur waktu dengan baik.", # [cite: 400]
                5: "Saya sangat efektif dan efisien dalam menyelesaikan tugas dan secara konsisten bekerja dengan cepat serta terorganisir." # [cite: 401]
            },
            "EXT-1": { # Saya adalah seseorang yang komunikatif dan banyak bicara (atau cerewet) [cite: 402]
                1: "Saya tidak komunikatif dan jarang berbicara dalam berbagai situasi.", # [cite: 403]
                2: "Saya kurang komunikatif dan tidak terlalu sering berbicara atau terlibat dalam percakapan.", # [cite: 403]
                3: "Saya kadang-kadang komunikatif, tetapi frekuensi berbicara saya bervariasi tergantung situasinya.", # [cite: 404]
                4: "Saya biasanya komunikatif dan sering berbicara atau terlibat dalam percakapan.", # [cite: 404]
                5: "Saya sangat komunikatif dan sering sekali berbicara atau menjadi orang yang paling aktif dalam percakapan." # [cite: 405]
            },
            "EXT-2": { # Saya adalah seseorang yang bisa keluar sendiri dan bersosialisasi (atau mudah bergaul) [cite: 406, 407]
                1: "Saya tidak mudah bergaul dan jarang ingin keluar sendiri atau bersosialisasi.", # [cite: 408]
                2: "Saya kurang suka bersosialisasi dan tidak terlalu nyaman keluar atau bergaul dengan orang baru.", # [cite: 409]
                3: "Saya kadang-kadang mau bersosialisasi atau keluar sendiri, tetapi itu tergantung situasi.", # [cite: 410]
                4: "Saya mudah bergaul dan sering merasa nyaman untuk keluar sendiri serta bersosialisasi.", # [cite: 411]
                5: "Saya sangat mudah bergaul dan sangat nyaman keluar sendiri serta aktif bersosialisasi dengan banyak orang." # [cite: 412]
            },
            "EXT-3": { # Saya adalah seseorang yang pendiam (atau tertutup) [cite: 413]
                1: "Saya tidak pendiam dan sering berbicara atau terbuka dalam berbagai situasi.", # [cite: 414]
                2: "Saya kurang pendiam dan biasanya cukup terbuka untuk berbicara dengan orang lain.", # [cite: 415]
                3: "Saya kadang pendiam, tetapi di beberapa situasi saya bisa cukup terbuka.", # [cite: 416]
                4: "Saya biasanya pendiam dan lebih sering memilih untuk tidak banyak berbicara.", # [cite: 417]
                5: "Saya sangat pendiam dan lebih suka tertutup, jarang berbicara atau mengungkapkan hal kepada orang lain." # [cite: 418]
            },
            "AGR-1": { # Saya adalah seseorang yang kadang-kadang agak kasar (atau sedikit tidak sopan) kepada orang lain [cite: 419, 420]
                1: "Saya tidak pernah bersikap kasar atau tidak sopan kepada orang lain.", # [cite: 421]
                2: "Saya jarang bersikap kasar atau tidak sopan, dan umumnya tetap menjaga sikap.", # [cite: 422]
                3: "Saya kadang-kadang bisa bersikap agak kasar, tetapi tidak terlalu sering.", # [cite: 423]
                4: "Saya cukup sering bersikap agak kasar atau sedikit tidak sopan dalam beberapa situasi.", # [cite: 424]
                5: "Saya sering bersikap agak kasar atau tidak sopan kepada orang lain dalam berbagai situasi." # [cite: 425]
            },
            "AGR-2": { # Saya adalah seseorang yang mudah memaafkan (atau bisa memaafkan) [cite: 426]
                1: "Saya sulit memaafkan dan jarang melupakan kesalahan orang lain.", # [cite: 426]
                2: "Saya kurang mudah memaafkan, meskipun kadang bisa melakukannya setelah waktu yang cukup lama.", # [cite: 427]
                3: "Saya kadang-kadang bisa memaafkan, tergantung situasi dan tingkat kesalahannya.", # [cite: 428]
                4: "Saya biasanya mudah memaafkan dan tidak menyimpan rasa kesal terlalu lama.", # [cite: 428]
                5: "Saya sangat mudah memaafkan dan cepat mengesampingkan kesalahan orang lain tanpa menyimpannya di hati." # [cite: 429]
            },
            "AGR-3": { # Saya adalah seseorang yang penuh perhatian dan baik hati terhadap orang lain [cite: 430]
                1: "Saya tidak penuh perhatian dan jarang menunjukkan kebaikan hati kepada orang lain.", # [cite: 431]
                2: "Saya kurang perhatian dan tidak selalu menunjukkan kebaikan hati dalam interaksi saya.", # [cite: 432]
                3: "Saya kadang-kadang perhatian dan baik hati, tetapi tidak selalu konsisten.", # [cite: 432]
                4: "Saya biasanya penuh perhatian dan sering menunjukkan kebaikan hati kepada orang lain.", # [cite: 433]
                5: "Saya sangat penuh perhatian dan secara konsisten menunjukkan kebaikan hati kepada orang lain." # [cite: 434]
            },
            "NEU-1": { # Saya adalah seseorang yang sering khawatir [cite: 435]
                1: "Saya jarang merasa khawatir dan umumnya tenang dalam berbagai situasi.", # [cite: 435]
                2: "Saya tidak terlalu sering khawatir, meskipun sesekali bisa merasa cemas.", # [cite: 436]
                3: "Saya kadang-kadang merasa khawatir, tergantung situasi atau tekanan yang dihadapi.", # [cite: 436]
                4: "Saya sering merasa khawatir dalam berbagai situasi, terutama ketika menghadapi ketidakpastian.", # [cite: 437]
                5: "Saya sangat sering merasa khawatir dan mudah cemas dalam banyak keadaan." # [cite: 438]
            },
            "NEU-2": { # Saya adalah seseorang yang mudah gugup [cite: 439]
                1: "Saya jarang merasa gugup dan biasanya tetap tenang dalam berbagai situasi.", # [cite: 439]
                2: "Saya tidak mudah gugup, meskipun sesekali bisa merasa tegang dalam kondisi tertentu.", # [cite: 440]
                3: "Saya kadang-kadang gugup, tergantung konteks dan situasinya.", # [cite: 440]
                4: "Saya cukup mudah gugup dan sering merasa tegang dalam beberapa situasi.", # [cite: 441]
                5: "Saya sangat mudah gugup dan sering merasa tegang bahkan dalam situasi yang ringan sekalipun." # [cite: 442]
            },
            "NEU-3": { # Saya adalah seseorang yang santai dan dapat mengatasi stres dengan baik [cite: 443, 444]
                1: "Saya tidak santai dan sering kesulitan mengatasi stres.", # [cite: 444]
                2: "Saya kurang santai dan kadang merasa sulit mengatasi stres.", # [cite: 445]
                3: "Saya kadang santai, tetapi kemampuan saya dalam mengatasi stres bervariasi tergantung situasinya.", # [cite: 445]
                4: "Saya biasanya santai dan cukup baik dalam mengatasi stres.", # [cite: 446]
                5: "Saya sangat santai dan sangat mampu mengatasi stres dengan baik dalam berbagai situasi." # [cite: 446]
            }
        }


    

    # MULAI
    def domain_cols_score(self, user_raw_scores):
        """
        Menghitung rata-rata skor per dimensi.
        Nilai diambil MENTAH (As Is) dari input user tanpa dibalik.
        """
        dim_scores = {}
        for domain, cols in domain_cols.items():
            # ambil value score
            values = [user_raw_scores[col] for col in cols]
            dim_scores[domain] = sum(values) / len(values)

        return dim_scores
        
    # --- KATEGORISASI (Low/Mid/High) ---
    def kategori_score(self, x):
        """Mengubah angka skor (1-5) menjadi label kategori."""
        if x < 2.5:
            return "low"
        elif 2.5 <= x < 3.5:
            return "mid-low"
        elif 3.5 <= x < 4.25:
            return "mid-high"
        else:
            return "high"

    def kategori_loc(self, internal, external):
        """Internal helper: Menentukan dominasi LOC."""
        return "internal" if internal >= external else "external"
    
    # --- MATCHING ---
    def rekomendasi_per_domain(self, row):
        """
        Input 'row' disini adalah Dictionary yang berisi kategori.
        Contoh: {'cat_self_efficacy': 'High', 'cat_innovativeness': 'Low', ...}
        """

        # buat set kosong untuk nampung sektor
        # set dipakai agar tidak ada duplikasi
        sektor = set()

        # mengambil kategori domain dari user tersebut
        # (Mengakses dictionary, sama seperti mengakses row pandas)
        # berada di main()
        # Ambil kategori dari row
        se = row.get("cat_self_efficacy")
        inn = row.get("cat_innovativeness")
        nach = row.get("cat_need_achievement")
        loc = row.get("cat_loc")

        # untuk setiap domain, masukkan sektor-sektor yang match ke dalam set
        # Gunakan self.rules karena rules sekarang milik class
        # Pastikan key dictionary rules kamu cocok dengan string ini
        if se in self.rules["self_efficacy"]:
            sektor.update(self.rules["self_efficacy"][se])
            
        if inn in self.rules["innovativeness"]:
            sektor.update(self.rules["innovativeness"][inn])
            
        if nach in self.rules["need_achievement"]:
            sektor.update(self.rules["need_achievement"][nach])
            
        if loc in self.rules["loc"]:
            sektor.update(self.rules["loc"][loc])

        # return semua sektor cocok dalam bentuk string, dipisahkan dengan koma
        # sorted() agar urut dan lebih rapi
        return ", ".join(sorted(sektor))

    def create_user_vector(self, row):
        vector_result = {}
        
        # Panggil menggunakan self.NAMA_KONSTANTA
        vector_result["score_SE"] = self.score_map.get(row["cat_self_efficacy"], 0)
        vector_result["score_INN"] = self.score_map.get(row["cat_innovativeness"], 0)
        vector_result["score_NACH"] = self.score_map.get(row["cat_need_achievement"], 0)
        vector_result["score_LOC"] = self.loc_map.get(row["cat_loc"], 0)

        return vector_result

    def euclidean_distance(self, vec1, vec2):
        """Helper: Menghitung jarak geometri antara dua array."""
        return np.sqrt(np.sum((np.array(vec1) - np.array(vec2))**2))

    def final_sector(self, row, rekomendasi_sektor):
        """
        Final Filter: Mencari 'Nearest Neighbor' dari daftar kandidat Fuzzy.
        Input:
            - broad_candidates: List nama sektor (hasil dari recommend_broad_match)
            - user_encoded_vector: Array 0-3 (hasil dari encode_user_category)
        Output:
            - List sektor terbaik (bisa lebih dari 1 jika seri)
        """
        # 1. Normalisasi Input (String -> List)
        # Ini penting karena input bisa berupa string "Sektor A, Sektor B" (dari database/csv)
        # atau sudah berupa list ["Sektor A", "Sektor B"] (dari proses python)
        sektor_list = []
        if isinstance(rekomendasi_sektor, str):
            if rekomendasi_sektor.strip():
                sektor_list = [x.strip() for x in rekomendasi_sektor.split(",")]
        elif isinstance(rekomendasi_sektor, list):
            sektor_list = rekomendasi_sektor
        
        # Validasi jika list kosong
        if not sektor_list:
            return {}, []

        # 1. Jika kandidat cuma 1, kembalikan apa adanya
        if len(sektor_list) == 1:
            single_sector = sektor_list[0]
            # Kita harus tetap mengembalikan format (Dictionary, List)
            # Kita buat dummy dictionary dengan jarak 0
            dummy_dict = {single_sector: 0}
            return dummy_dict, sektor_list  # <--- RETURN 2 NILAI

        # 2. Siapkan User Vector (Flatten agar jadi 1D array: [v1, v2, v3, v4])
        # user_encoded_vector bentuk aslinya [[...]], kita butuh [...]
        user_vec = [
        row["score_SE"],
        row["score_INN"],
        row["score_NACH"],
        row["score_LOC"]
        ]

        jarak_dict = {}

        # 3. Loop hanya sektor yang ada di kandidat (Broad Match)
        for s in sektor_list:
            if s in self.sector_proto:
                # Hitung Jarak
                dist = self.euclidean_distance(user_vec, self.sector_proto[s])
                jarak_dict[s] = dist
        
        # Jika setelah loop tidak ada sektor yang cocok sama sekali
        if not jarak_dict:
            return {}, []

        # 4. Sorting (Ranking dari jarak terdekat/terkecil)
        # Menggunakan lambda untuk sort berdasarkan value (jarak)
        jarak_sorted = dict(sorted(jarak_dict.items(), key=lambda x: x[1]))

        # 5. Cari Juara (Best Match)
        # Ambil jarak terkecil (elemen pertama karena sudah disort)
        min_dist = list(jarak_sorted.values())[0]
        
        # List comprehension untuk menangani jika ada yang SERI (jaraknya sama persis)
        top_picks = [s for s, d in jarak_sorted.items() if d == min_dist]

        return jarak_sorted, top_picks


    def cluster_weights_from_top5_qA(self, top5_list):
        """
        Menghitung kecenderungan User masuk ke Cluster mana berdasarkan Top 5 Sektor.
        Input: List string nama sektor (misal: ['software', 'construction', ...])
        Output: DataFrame bobot cluster yang sudah diurutkan.
        """
        # 1. Validasi Input
        if not isinstance(top5_list, list) or len(top5_list) == 0:
            return {}
        
        # Build reverse mapping
        self.sector_to_cluster = {}
        for cluster, sectors in self.cluster_mapping.items():
            for s in sectors:
                self.sector_to_cluster.setdefault(s, []).append(cluster)

        # 2. Definisi Bobot Ranking (Juara 1 dapat poin 5, dst)
        rank_weight = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1}

        # 3. Siapkan Dictionary Skor Cluster (Awalnya 0 semua)
        weights = {cluster: 0 for cluster in self.cluster_mapping}

        # 4. Loop Top 5 Sektor Saja
        # (Menggunakan slice [:5] untuk memastikan hanya ambil 5 teratas)
        for idx, sector in enumerate(top5_list):
            s_key = sector
            
            # Cek apakah sektor ini punya grup cluster
            if s_key in self.sector_to_cluster:
                # Ambil poin berdasarkan ranking
                w = rank_weight.get(idx, 0)
                
                # Tambahkan poin ke SEMUA cluster yang memiliki sektor ini
                for cluster in self.sector_to_cluster[s_key]:
                    weights[cluster] += w

        return weights

    def best_cluster_from_weights_qA(self, wdict):
        """
        Menentukan cluster pemenang berdasarkan bobot tertinggi.
        Input: Dictionary bobot (misal: {'Cluster A': 9, 'Cluster B': 5})
        Output: String nama cluster (misal: "Cluster A")
        """
        
        # jika dictionary kosong → return string kosong
        if not wdict:
            return "",[]
        
        # sort
        sorted_items = sorted(wdict.items(), key=lambda x: x[1], reverse=True)    

        # ambil nilai bobot tertinggi
        max_score = sorted_items[0][1]
        
        # ambil semua cluster yang memiliki bobot sama dengan bobot tertinggi
        best_clusters = [c for c, v in sorted_items if v == max_score]
        
        # Gabungkan jadi string
        best_str = ", ".join(best_clusters)

        return best_str, sorted_items
    

    def top5_clusters_with_sectors_qA(self, top5_list):
        """
        Mengelompokkan 5 sektor teratas ke dalam clusternya masing-masing.
        Input: List sektor ['Software', 'Retail', ...]
        Output: Dict {'Teknologi': ['Software'], 'Bisnis': ['Retail']}
        """

        # 1. SIAPKAN DATA MAPPING (Ambil dari Class)
        # Kita simpan ke variabel lokal 'cluster_mapping' agar logika di bawah tidak perlu diubah
        cluster_mapping = self.cluster_mapping 

        # 2. BUILD REVERSE MAPPING (Sektor -> Cluster)
        # Kita buat kamus pencarian cepat ini secara lokal
        sector_to_cluster = {}
        for cluster, sectors in cluster_mapping.items():
            for s in sectors:
                sector_to_cluster.setdefault(s, []).append(cluster)

        # --- MULAI KODE ASLI ANDA ---
        
        # jika datanya tidak valid -> kembalikan dict kosong
        if not isinstance(top5_list, list) or len(top5_list) == 0:
            return {}

        # buat dictionary cluster -> list sektor
        hasil = {cluster: [] for cluster in cluster_mapping}

        for sector in top5_list:
            if sector in sector_to_cluster:
                # cek cluster apa saja yg menaungi sektor ini
                clusters = sector_to_cluster[sector]

                # masukkan sektor ke masing-masing cluster tersebut
                for c in clusters:
                    hasil[c].append(sector)

        # hapus cluster yang kosong (tidak ada sektor Top 5 di dalamnya)
        hasil = {c: sectors for c, sectors in hasil.items() if len(sectors) > 0}

        return hasil
    
    def best_list_cluster_from_weights_qA(self, wdict):
        """
        Menentukan cluster terbaik (highest weight).
        Output: LIST berisi nama cluster juara.
        """
        
        # jika kosong → return list kosong
        if not wdict:
            return []

        # 1. Sort dictionary berdasarkan value (skor) dari besar ke kecil
        # Ini akan menghasilkan list of tuples: [('Cluster A', 5), ('Cluster B', 3), ...]
        sorted_items = sorted(wdict.items(), key=lambda x: x[1], reverse=True)    

        # 2. Ambil nilai bobot tertinggi (Juara 1)
        max_score = sorted_items[0][1]

        # ambil semua cluster yang memiliki bobot sama dengan max_score
        # (Variabel sama persis dengan request Anda)
        best_clusters = [c for c, v in wdict.items() if v == max_score]

        return best_clusters, sorted_items
    
# QUESTIONNAIRE B
    # --- HELPER KECIL (Untuk hitung rata-rata list) ---
    def _get_avg(self, values):
        if not values: return 0
        return sum(values) / len(values)
    
    def calculate_big5_scores(self, user_raw_scores):
        """
        Menghitung skor Big 5 per user.
        Logic: (Avg(Normal) + Avg(Reverse)) / 2
        """
        final_scores = {}
        
        # Helper reverse (Asumsi skala 1-5, jadi 6 - x)
        # Jika skala 1-7, ganti 6 jadi 8.
        def reverse_val(x): return 6 - x

        for trait, config in self.big5.items():
            
            # KASUS 1: Config cuma LIST (Contoh: 'openess')
            # Pandas: df[cols].mean(axis=1)
            if isinstance(config, list):
                # Ambil nilai jawaban user
                vals = [user_raw_scores.get(col, 3) for col in config]
                final_scores[f"avg_{trait}"] = self._get_avg(vals)

            # KASUS 2: Config berupa DICTIONARY (Ada Normal & Reverse)
            # Pandas: (mean_normal + mean_reverse) / 2
            elif isinstance(config, dict):
                
                # A. Hitung Rata-rata Normal
                normal_cols = config.get("normal", [])
                vals_normal = [user_raw_scores.get(c, 3) for c in normal_cols]
                avg_normal = self._get_avg(vals_normal)
                
                # B. Hitung Rata-rata Reverse (Pakai fungsi 6 - x)
                reverse_cols = config.get("reverse", [])
                # Logic .applymap(reverse_score)
                vals_reverse = [reverse_val(user_raw_scores.get(c, 3)) for c in reverse_cols]
                avg_reverse = self._get_avg(vals_reverse)
                
                # C. Gabungkan (Rumus: (N + R) / 2)
                score_gabungan = (avg_normal + avg_reverse) / 2
                final_scores[f"avg_{trait}"] = score_gabungan

        return final_scores
    
    def avg_to_notation(self, x):
        """
        Mengubah skor angka menjadi notasi simbol (++, +, 0, -, --).
        """
        # Cek NaN (Menggantikan np.isnan dengan math.isnan)
        # Kita tambah pengecekan 'x is None' untuk keamanan data
        if x is None or np.isnan(x):
            return None # atau return ""

        # LOGIKA ASLI (Variable x tidak diganti)
        if x >= 4.2:    return '++'
        elif x >= 3.5:  return '+'
        elif x >= 2.5:  return '0'
        elif x >= 1.8:  return '-'
        else:           return '--'
    
    def big5_notations(self, big5_scores):
        return {
            'Note_O': self.avg_to_notation(big5_scores.get('avg_openess')),
            'Note_C': self.avg_to_notation(big5_scores.get('avg_conscientiousness')),
            'Note_E': self.avg_to_notation(big5_scores.get('avg_extraversion')),
            'Note_A': self.avg_to_notation(big5_scores.get('avg_agreeableness')),
            'Note_N': self.avg_to_notation(big5_scores.get('avg_neuroticism'))
        }
    
    def symbol_matches(self, resp_sym, cluster_sym):
        """
        Cek kecocokan simbol (mendukung “0/+”, “-/+”, “--/+”).
        Input: 
            resp_sym: Simbol user (misal: '+')
            cluster_sym: Rule cluster (misal: '0/+')
        """
        
        # 1. Cek Null/Kosong (Pengganti pd.isna)
        # Jika user tidak punya notasi (None), anggap Tidak Cocok
        if resp_sym is None:
            return False

        # 2. Parsing Rule (Nama variabel tetap)
        options = cluster_sym.split('/')  # contoh "0/+" → ["0", "+"]
        
        # 3. Cek apakah simbol user ada di dalam opsi
        return resp_sym in options
    
    def cluster_proto_numeric(self, cluster_sig):
        """
        Mengubah rule cluster (notasi) -> vektor angka.
        Menggantikan np.mean dan np.array dengan List Python biasa.
        """
        vals = []  # simpan angka O, C, E, A, N
        
        for dim in ['O','C','E','A','N']:   # per dimensi
            opts = cluster_sig[dim].split('/')  # contoh "0/+" → ["0","+"]
            
            # ubah simbol ke angka (akses self.symbol_to_num)
            nums = [self.symbol_to_num[o] for o in opts]  
            
            # ambil nilai rata-rata (Ganti np.mean dengan sum/len)
            rata_rata = sum(nums) / len(nums)
            
            vals.append(rata_rata)  
            
        return vals # kembalikan sebagai list (pengganti vektor numpy)

    def compute_cluster_scores(self, row):
        """
        Menghitung persentase kecocokan (0.0 - 1.0) berdasarkan simbol.
        Input 'row' harus punya key: Note_O, Note_C, Note_E, Note_A, Note_N
        """
        cluster_scores = {}

        # Loop setiap cluster (Adaptive Services, dll)
        # self.big5_cluster_rules sudah didefinisikan di __init__
        for name, sig in self.big5_cluster_rules.items():
            matches = 0
            
            # Loop 5 Dimensi
            for dim in ['O','C','E','A','N']:
                # Ambil notasi user (Note_O, dll)
                user_note = row.get(f"Note_{dim}")
                # Ambil rule cluster (sig[dim])
                rule_note = sig[dim]
                
                # Cek kecocokan
                if self.symbol_matches(user_note, rule_note):
                    matches += 1

            # Hitung skor (Total Match / 5)
            cluster_scores[name] = matches / 5.0

        return cluster_scores

    def assign_cluster_with_top5(self, row):
        """
        Menentukan cluster terbaik dengan Tie-Breaker + Top 5 Ranking.
        """
        
        # 1. Hitung matching score semua cluster
        scores = self.compute_cluster_scores(row)

        # 2. Ranking cluster berdasarkan score (descending)
        sorted_clusters = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Ambil top-5 cluster
        top5_scores = sorted_clusters[:5]
        top5_names = [x[0] for x in top5_scores]
        
        # Safety Check: Jika kosong
        if not top5_scores:
            return None, 0, [], []

        # 3. Cari cluster pemenang — cek apakah ada tie
        best_score_value = top5_scores[0][1]
        tied_clusters = [c for c, s in top5_scores if s == best_score_value]

        # Jika hanya satu cluster → langsung pemenang
        if len(tied_clusters) == 1:
            best_cluster = tied_clusters[0]
            return best_cluster, best_score_value, top5_names, top5_scores

        # 4. Tie-breaker → Euclidean Distance
        # Mengganti np.array dengan List Python
        user_vec = np.array([
            self.symbol_to_num.get(row.get('Note_O'), 0.0), # Pakai .get() biar aman
            self.symbol_to_num.get(row.get('Note_C'), 0.0),
            self.symbol_to_num.get(row.get('Note_E'), 0.0),
            self.symbol_to_num.get(row.get('Note_A'), 0.0),
            self.symbol_to_num.get(row.get('Note_N'), 0.0)
        ])

        best_dist = np.inf
        best_name = None

        for name in tied_clusters:
            # Ambil vektor target dari memori class
            target_vec = self.cluster_protos[name]
            
            dist = np.linalg.norm(user_vec - target_vec)
            
            if dist < best_dist:
                best_dist = dist
                best_name = name

        return best_name, best_score_value, top5_names, top5_scores
    
    def pick_best_clusters_qB_multi(self, row):
        """
        Mengambil nama-nama cluster pemenang (bisa lebih dari 1 jika seri).
        Output: String gabungan (misal: "Cluster A, Cluster B")
        """
        # Ambil data dari dictionary row (menggunakan .get biar aman)
        top5 = row.get("top5_clusters_qB_score")   # list: [(cluster, score), ...]

        if not isinstance(top5, list) or len(top5) == 0:
            return ""

        # Ambil nilai tertinggi
        highest_score = max(score for _, score in top5)

        # Jika highest score = 0, kosongkan
        if highest_score == 0:
            return ""

        # Ambil semua cluster yang skor-nya sama dengan nilai tertinggi
        best_clusters = [name for name, score in top5 if score == highest_score]

        # Gabungkan dalam 1 string
        return ", ".join(best_clusters)

    def pick_best_clusters_qB_score(self, row):
        """
        Mengambil skor tertinggi dari cluster pemenang.
        Output: Angka (Float/Int) atau None.
        """
        top5 = row.get("top5_clusters_qB_score")

        if not isinstance(top5, list) or len(top5) == 0:
            return None # Pengganti np.nan

        highest_score = max(score for _, score in top5)

        # Jika highest score = 0, return None
        if highest_score == 0:
            return None # Pengganti np.nan

        return highest_score
    
    def top5_clusters_with_matched_sectors_qB(self, row):
        """
        Mencari irisan antara Cluster (berdasarkan Big 5) dengan Sektor (berdasarkan Entrepreneur).
        Output: Dictionary { 'Cluster A': ['Sektor X', 'Sektor Y'] }
        """
        
        # Ambil data dari dictionary input (gunakan .get untuk safety)
        top5_clusters_qB = row.get("top5_clusters_qB")          # list cluster nama
        top3_sectors_qA  = row.get("top3_euclid_qA")            # list sektor Top-3 Euclid qA

        # validasi
        if not isinstance(top5_clusters_qB, list) or not isinstance(top3_sectors_qA, list):
            return {}

        hasil = {}

        for cluster_name in top5_clusters_qB:

            # pastikan cluster ada di mapping (Gunakan SELF)
            if cluster_name in self.cluster_mapping:

                # ambil semua sektor cluster tsb
                sektor_cluster = self.cluster_mapping[cluster_name]

                # cocokkan dgn top3 euclid qA
                sektor_match = [s for s in sektor_cluster if s in top3_sectors_qA]

                # jika ada kecocokan → simpan
                if len(sektor_match) > 0:
                    hasil[cluster_name] = sektor_match

        return hasil
    
    def get_recommended_cluster_refined(self, row):
        """
        Menentukan Cluster Final dengan logika Irisan, Substitusi, dan Coverage.
        Menggabungkan hasil qA (Entrepreneur) dan qB (Big 5).
        """
        
        # [TRACKING START]
        # st.write("--- 🛠️ DEBUG TRACKING: get_recommended_cluster_refined ---")

        # 1. Ambil Data Input
        # qA = Cluster Juara dari sisi Entrepreneurship (List atau String)
        qA = row.get("cluster_top5_best_qA", [])
        
        # qB = Cluster Juara dari sisi Big 5 (List atau String)
        qB = row.get("cluster_top5_best_qB", [])
        
        # mapping = Dictionary isi sektor per cluster (Hasil step 6: top5_clusters_with_sectors_qA)
        mapping = row.get("top5_cluster_to_sector_qA", {}) or {}

        # [TRACKING]
        st.write(f"1. Raw Input: qA={qA}, qB={qB}")

        # 2. Normalisasi input (String -> List)
        # Jaga-jaga jika inputnya masih berbentuk string "Cluster A, Cluster B"
        if isinstance(qA, str):
            qA = [x.strip() for x in qA.split(",")] if qA.strip() else []
        if isinstance(qB, str):
            qB = [x.strip() for x in qB.split(",")] if qB.strip() else []

        # [TRACKING]
        # st.write(f"2. Normalized Input: qA={qA}, qB={qB}")

        # Jika salah satu kosong -> Gagal
        if not qA or not qB:
            # st.write("❌ Gagal: Salah satu input kosong.")
            return ["Belum dapat menentukan cluster yang sesuai."]

        # ---------------------------------------------------
        # RULE 1 — Irisan (Intersection)
        # ---------------------------------------------------
        # Cari cluster yang muncul di KEDUA hasil (qA dan qB)
        intersection = [c for c in qA if c in qB]
        
        # [TRACKING]
        # st.write(f"3. Intersection found: {intersection}")
        
        if intersection:
            initial = intersection[:]
            # st.write("   -> Using RULE 1 (Intersection Found)")
        else:
            # RULE 2 — Jika tidak ada irisan, Ambil terbaik masing-masing
            # Ambil juara 1 dari qA dan juara 1 dari qB
            # (Pastikan index 0 aman karena sudah dicek 'if not qA' diatas)
            initial = [qA[0], qB[0]]
            # st.write("   -> Using RULE 2 (Top 1 from each)")

        # [TRACKING]
        # st.write(f"4. Initial Candidates: {initial}")

        # ---------------------------------------------------
        # VALIDASI KANDIDAT AWAL
        # ---------------------------------------------------
        # Pastikan cluster yang dipilih benar-benar memiliki sektor di dalamnya (mapping > 0)
        valid_initial = [
            c for c in initial
            if c in mapping and len(mapping.get(c, [])) > 0
        ]

        # [TRACKING]
        # st.write(f"5. Valid Candidates (Mapping Check): {valid_initial}")

        final_candidates = valid_initial.copy() # yg valid aja

        # Siapkan daftar semua kandidat yang tersedia (Gabungan qA dan qB unik)
        # dict.fromkeys dipakai untuk menghilangkan duplikat sambil menjaga urutan
        all_clusters = list(dict.fromkeys(qA + qB))

        # Fungsi helper lokal (sesuai request)
        def sektor_baru(cluster, sektor_terwakili):
            return set(mapping.get(cluster, [])) - sektor_terwakili
        
        # ---------------------------------------------------
        # LOGIKA SUBSTITUSI (Mengganti Kandidat Invalid)
        # ---------------------------------------------------
        # Jika ada cluster di 'initial' yang dibuang karena kosong, cari penggantinya
        invalid_candidates = set(initial) - set(valid_initial)
        
        # [TRACKING]
        if invalid_candidates:
            # st.write(f"6. Substitution needed for invalid candidates: {invalid_candidates}")

        for invalid in invalid_candidates:

            # Cek sektor apa saja yang SUDAH terwakili oleh kandidat saat ini
            sektor_terwakili = set()
            for c in final_candidates:
                sektor_terwakili.update(mapping.get(c, []))

            best_choice = None
            best_gain = -1

            # Cari kandidat lain dari 'all_clusters' yang memberikan 'gain' (sektor baru) terbesar
            for candidate in all_clusters:
                if candidate in final_candidates:
                    continue
                if candidate not in mapping:
                    continue

                # Hitung berapa banyak sektor BARU yang dibawa cluster ini
                gain = len(sektor_baru(candidate, sektor_terwakili))
                
                if gain > best_gain:
                    best_gain = gain
                    best_choice = candidate

            # Jika ketemu pengganti yang bagus, masukkan
            if best_choice:
                final_candidates.append(best_choice)
                st.write(f"   -> Substituted with: {best_choice} (Gain: {best_gain})")

        # ---------------------------------------------------
        # RULE TAMBAHAN — COVERAGE SEKTOR USER
        # ---------------------------------------------------
        # Pastikan Top 3 Sektor User (top3_euclid_qA) sudah tercover oleh rekomendasi
        sektor_user = set(row.get("top3_euclid_qA", []))

        # Cek lagi apa yang sudah terwakili sekarang
        sektor_terwakili = set()
        for c in final_candidates:
            sektor_terwakili.update(mapping.get(c, []))

        sektor_kurang = sektor_user - sektor_terwakili

        # # [TRACKING]
        # st.write(f"7. Coverage Check. User Sectors: {sektor_user}")
        # st.write(f"   -> Missing Coverage: {sektor_kurang}")

        # Jika masih ada sektor user yang belum masuk rekomendasi
        if sektor_kurang:
            best_choice = None
            best_gain = -1

            # Cari cluster yang bisa menambal kekurangan tersebut
            for candidate in all_clusters:
                if candidate in final_candidates:
                    continue
                if candidate not in mapping:
                    continue

                # Gain dihitung berdasarkan irisan dengan 'sektor_kurang'
                gain = len(set(mapping[candidate]) & sektor_kurang)
                
                if gain > best_gain:
                    best_gain = gain
                    best_choice = candidate

            if best_choice:
                final_candidates.append(best_choice)
                # st.write(f"   -> Added for coverage: {best_choice} (Covered: {gain})")

        # [TRACKING END]
        result = final_candidates[:2]
        # st.write(f"🏁 FINAL RESULT: {result}")
        # st.write("--------------------------------------------------")

        return result
    
    # HYBRID - CONTENT BASED
    def build_narrative_text(self, row, mapping_dict):
        """
        Fungsi Generic: Mengubah jawaban angka jadi teks.
        Bisa dipakai untuk Part A (Likert) maupun Part B (Big 5).
        """
        texts = []
        
        # Loop dictionary mapping yang dikirim sebagai parameter
        for col, map_data in mapping_dict.items():
            
            # 1. Ambil nilai dari row (gunakan .get biar aman)
            val = row.get(col)
            
            # 2. Validasi: Pastikan tidak None dan tidak kosong
            # Kita pakai try-except atau check type untuk keamanan maksimal
            if val is not None:
                try:
                    val_int = int(val) # Coba ubah jadi integer
                    
                    # 3. Cek apakah angka tersebut ada di kamus kata-kata
                    if val_int in map_data:
                        texts.append(map_data[val_int])
                        
                except ValueError:
                    continue # Skip jika error (misal string kosong)

        return " ".join(texts)
    
    def compute_tfidf_ranking(self, user_text, candidates_dict, lang='id', ngram=(1,1), top_n=None):
        """
        Fungsi Generic TF-IDF untuk Part A (Sektor) & Part B (Cluster).
        
        Parameters:
        - user_text (str): Narasi profil user.
        - candidates_dict (dict): Dictionary { 'Nama': 'Deskripsi' }.
        - lang (str): 'id' (default) atau 'en' (untuk aktifkan stop_words english).
        - ngram (tuple): (1,1) per kata, (1,2) per frasa.
        - top_n (int): Ambil berapa besar? (None = ambil semua).
        
        Output:
        - List of Tuples: [('Nama A', 0.95), ('Nama B', 0.80), ...] yang SUDAH URUT.
        """
        # 1. Validasi Input
        if not user_text or not candidates_dict:
            return []

        # 2. Konfigurasi Vectorizer (Dinamis sesuai parameter)
        stop_words_setting = 'english' if lang == 'en' else None
        
        vectorizer = TfidfVectorizer(
            stop_words=stop_words_setting,
            ngram_range=ngram
        )

        # 3. Siapkan Corpus (Standardisasi: User selalu di Index 0)
        # Kita ubah dict jadi list agar urutannya terjaga
        candidate_names = list(candidates_dict.keys())
        candidate_docs = list(candidates_dict.values())
        
        # Corpus = [User Text, Doc 1, Doc 2, ... Doc N]
        corpus = [user_text] + candidate_docs

        try:
            # 4. Transformasi TF-IDF
            tfidf_matrix = vectorizer.fit_transform(corpus)
            
            # 5. Hitung Similarity
            # Bandingkan User (Index 0) vs Semua Kandidat (Index 1 sampai habis)
            similarities = cosine_similarity(
                tfidf_matrix[0:1], 
                tfidf_matrix[1:]
            )[0]
            
            # 6. Gabungkan Nama & Skor
            results = list(zip(candidate_names, similarities))
            
            # 7. Sorting Descending (Ranking)
            results.sort(key=lambda x: x[1], reverse=True)
            
            # 8. Slicing (Ambil Top N jika diminta)
            if top_n:
                results = results[:top_n]
                
            return results

        except ValueError:
            # Handle jika vocabulary kosong atau error teks
            return []
    
    def top3_clusters_with_matched_sectors_qB(self, row):
        """
        Mencari irisan (intersection) antara Cluster Minat (QB) 
        dengan Sektor Potensi (QA).
        """
        
        # Ambil data dari row (seperti kode aslimu)
        top3_clusters_qB = row["top3_cluster_tfidf_qB_hybrid"]     # list cluster nama (dari Minat)
        top3_sectors_qA  = row["top3_tfidf_sector_hybrid"]      # list sektor Top-3 (dari Kepribadian)

        
        list_cluster = [item[0] for item in top3_clusters_qB]
        # validasi input
        if not isinstance(top3_clusters_qB, list) or not isinstance(top3_sectors_qA, list):
            return {}

        hasil = {}

        for cluster_name in list_cluster:
           
            # pastikan cluster ada di mapping (panggil pakai self)
            if cluster_name in self.cluster_mapping:
                
                # ambil semua sektor cluster tsb
                sektor_cluster = self.cluster_mapping[cluster_name]
                
                # cocokkan dgn top3 euclid qA
                # (Mencari: Apakah sektor rekomendasi QA ada di dalam Cluster QB ini?)
                sektor_match = [s for s in sektor_cluster if s in top3_sectors_qA]

                # jika ada kecocokan → simpan
                if len(sektor_match) > 0:
                    hasil[cluster_name] = sektor_match
        return hasil
    
    def get_recommended_cluster_refined_hybrid(self, row):
        """
        Menentukan cluster final dengan strategi Hybrid:
        1. Irisan (Intersection) qA & qB.
        2. Fallback ke Top 1 masing-masing jika tidak ada irisan.
        3. Substitusi cerdas jika cluster terpilih ternyata kosong isinya.
        4. Safety net untuk memastikan sektor spesifik user ter-cover.
        """
        
        # 1. Ambil Data dari Row
        qA = row.get("cluster_top5_best_qA_hybrid", [])
        qB = row.get("cluster_top3_best_qB_hybrid", [])
        mapping = row.get("top3_cluster_to_sector_qA_hybrid", {}) or {}

        # st.markdown("### 1. Cek Data Mentah")
        # st.write(f"**qA (Potensi):** {qA} (Tipe: {type(qA)})")
        # st.write(f"**qB (Minat):** {qB} (Tipe: {type(qB)})")
        # st.write(f"**Mapping Sektor (Keys):** {list(mapping.keys())}")

        # 2. Normalisasi input (String "A, B" -> List ["A", "B"])
        if isinstance(qA, str):
            qA = [x.strip() for x in qA.split(",")] if qA.strip() else []
        if isinstance(qB, str):
            qB = [x.strip() for x in qB.split(",")] if qB.strip() else []

        # st.write(f"👉 **Setelah Normalisasi:** qA={qA}, qB={qB}")

        # 3. Cek Kekosongan
        if not qA:
            return qB
        elif not qB:
            return qA

        # ==========================================
        # STRATEGI 1: TENTUKAN KANDIDAT AWAL (INITIAL)
        # ==========================================
        
        # RULE 1 — Irisan (Intersection)
        intersection = [c for c in qA if c in qB] # Cari yang ada di Potensi DAN Minat
        
        if intersection:
            initial = intersection[:]
            # st.write(f"👉 **Irisan Ditemukan:** {initial}")
        else:
            # RULE 2 — Fallback: Ambil Juara 1 masing-masing
            # Jika tidak ada yang sama, ambil Top 1 Potensi & Top 1 Minat
            initial = [] 
            if len(qA) > 0: initial.append(qA[0])
            if len(qB) > 0: 
                # Cek biar gak dobel kalau ternyata qA[0] == qB[0] (meski jarang)
                if qB[0] not in initial:
                    initial.append(qB[0])
            # st.write(f"👉 **Tidak ada irisan, pakai Top 1 masing-masing:** {initial}")

        # ==========================================
        # STRATEGI 2: VALIDASI ISI CLUSTER
        # ==========================================
        
        # Validasi: Hanya loloskan cluster yang PUNYA isi sektor (berdasarkan mapping qA)
        # st.markdown("### 2. Cek Validasi Mapping")
        valid_initial = []
        
        for c in initial:
            # Cek keberadaan di mapping
            cek_ada = c in mapping
            
            # Cek isi mapping
            isi_sektor = mapping.get(c, [])
            cek_isi = len(isi_sektor) > 0
            
            status = "✅ Lolos" if (cek_ada and cek_isi) else "❌ Dibuang"
            # st.write(f"- Cluster **'{c}'**: Ada di Mapping? **{cek_ada}** | Punya Sektor? **{cek_isi}** ({isi_sektor}) -> {status}")
            
            if cek_ada and cek_isi:
                valid_initial.append(c)

        final_candidates = valid_initial.copy()
        # st.write(f"👉 **Kandidat Valid Saat Ini:** {final_candidates}")

        final_candidates = valid_initial.copy()

        # Daftar semua kemungkinan cluster (Gabungan qA dan qB tanpa duplikat)
        all_clusters = list(dict.fromkeys(qA + qB))

        # Helper function (Nested): Hitung berapa sektor BARU yang dibawa cluster ini
        def sektor_baru(cluster, sektor_terwakili):
            return set(mapping.get(cluster, [])) - sektor_terwakili
        
        # ==========================================
        # STRATEGI 3: SUBSTITUSI (PENGGANTI)
        # ==========================================
        # Substitusi jika ada kandidat invalid
        if len(valid_initial) < len(initial):
            # st.info("🔄 Melakukan Substitusi karena ada kandidat terbuang...")
            # Cari pengganti untuk kandidat yang terbuang (invalid)
            for invalid in set(initial) - set(valid_initial):
                # Cek apa yang sudah kita punya sekarang
                sektor_terwakili = set()
                for c in final_candidates:
                    sektor_terwakili.update(mapping.get(c, []))
                
                best_choice = None
                best_gain = -1

                # Audisi semua cluster lain
                for candidate in all_clusters:
                    if candidate in final_candidates: continue # Jangan pilih yang sudah ada
                    if candidate not in mapping: continue      # Jangan pilih yang kosong

                    # Hitung kontribusi unik (Gain)
                    gain = len(sektor_baru(candidate, sektor_terwakili))
                    
                    # Greedy: Ambil yang gain-nya paling besar
                    if gain > best_gain:
                        best_gain = gain
                        best_choice = candidate

                # Rekrut pemenang
                if best_choice:
                    # st.write(f"   + Menambahkan pengganti: **{best_choice}** (Gain: {best_gain})")
                    final_candidates.append(best_choice)
                # else:
                #     st.write("   - Tidak menemukan pengganti yang cocok.")

        # ==========================================
        # STRATEGI 4: SAFETY NET (COVERAGE)
        # ==========================================
        
        # Pastikan sektor Top User (dari TF-IDF) tidak tertinggal
        sektor_user = set(row.get("top3_tfidf_sector", []))

        # Cek lagi apa yang sudah terwakili oleh final_candidates saat ini
        sektor_terwakili = set()
        for c in final_candidates:
            sektor_terwakili.update(mapping.get(c, []))

        # Cari sektor user yang BELUM terwakili
        sektor_kurang = sektor_user - sektor_terwakili

        # Jika ada yang kurang, cari 1 cluster lagi untuk menambal kekurangan itu
        if sektor_kurang:
            st.info(f"🔄 Masih ada sektor user yang belum tercover: {sektor_kurang}")
            # Logic coverage... (sama seperti sebelumnya)
            best_choice = None
            best_gain = -1

            for candidate in all_clusters:
                if candidate in final_candidates: continue
                if candidate not in mapping: continue

                gain = len(set(mapping[candidate]) & sektor_kurang)
                if gain > best_gain:
                    best_gain = gain
                    best_choice = candidate

            if best_choice:
                st.write(f"   + Menambahkan pelengkap: **{best_choice}**")
                final_candidates.append(best_choice)
        
        # FINAL CHECK
        # st.success(f"🏁 **HASIL AKHIR:** {final_candidates}")
        # Fallback Terakhir agar tidak kosong melompong
        if not final_candidates and initial:
            st.error("⚠️ Filter membuang semua hasil. Mengembalikan Initial sebagai fallback.")
            return initial
        
        return final_candidates
    
    def get_sector_descriptions(self):
        # Class memanggil fungsi global yang sudah di-cache
        return load_sector_descriptions()

    def get_cluster_descriptions(self):
        # Class memanggil fungsi global yang sudah di-cache
        return load_cluster_descriptions()

def render_hasil_single():
    # --- 0. CSS STYLE (Hanya untuk elemen non-HTML block) ---
    st.markdown("""
    <style>
        /* 1. Background Halaman */
        .stApp {
            background-color: #F8F9F1;
        }

        /* 2. Kartu Big 5 Kecil */
        .big5-card {
            background-color: #fff;
            border-radius: 8px;
            padding: 10px 5px;
            text-align: center;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* 3. Styling Tombol Streamlit */
        div.stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        
        /* 4. Judul Expander Besar */
        div[data-testid="stExpander"] details summary p {
            font-size: 20px !important;
            font-weight: 700 !important;
            color: #154360 !important;
        }

        /* --- CLASS BARU UNTUK KOTAK DESKRIPSI (Ganti Inline CSS) --- */
        .info-box-blue {
            background-color: #EBF5FB; 
            border: 2px solid #AED6F1; 
            border-radius: 12px; 
            padding: 25px; 
            margin-bottom: 20px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            color: #0A0A44;
            font-size: 16px;
            line-height: 1.6;
            text-align: justify;
        }

        /* --- CLASS BARU UNTUK SEKTOR MATCHED (Ganti Inline CSS) --- */
        .sector-match-box {
            background-color: #e1f5fe;
            border-left: 5px solid #2980b9;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            color: #0c5460;
            font-size: 16px;
        }

        /* --- CLASS UNTUK LINK --- */
        .custom-link {
            text-decoration: none;
            color: #2980B9 !important;
            font-weight: bold;
            border-bottom: 1px dashed #2980B9;
        }
        .custom-link:hover {
            color: #154360 !important;
            border-bottom: 1px solid #154360;
        }

        /* Media Query HP */
        @media (max-width: 600px) {
            .mobile-text-left { text-align: left !important; }
            div[data-testid="stExpander"] details summary p {
                font-size: 18px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    # --- 1. AMBIL DATA DARI SESSION STATE ---
    # Gabungkan jawaban Part 1 dan Part 2
    answers_1 = st.session_state.get('temp_answers_1', {})
    answers_2 = st.session_state.get('temp_answers_2', {})

    user_input = {**answers_1, **answers_2}
    engine = RecommenderEngine()
    row_data = user_input.copy()

    # ============================================
    # STEP A: PROSES 4 DOMAIN KEWIRAUSAHAAN
    # ============================================
    
    # 1. Hitung Score & Kategori
    scores_A = engine.domain_cols_score(user_input)

    # Masukkan skor angka ke row_data (untuk keperluan vektor nanti)
    row_data['score_SE'] = scores_A['self_efficacy']
    row_data['score_INN'] = scores_A['innovativeness']
    row_data['score_NACH'] = scores_A['need_achievement']

    # Konversi Angka -> Kategori (String)
    row_data['cat_self_efficacy'] = engine.kategori_score(scores_A['self_efficacy'])
    row_data['cat_innovativeness'] = engine.kategori_score(scores_A['innovativeness'])
    row_data['cat_need_achievement'] = engine.kategori_score(scores_A['need_achievement'])
    
   # LOC Logic
    loc_i_raw = [user_input.get(k,3) for k in engine.domain_cols['loc_internal']]
    loc_e_raw = [user_input.get(k,3) for k in engine.domain_cols['loc_external']]
    row_data['cat_loc'] = engine.kategori_loc(sum(loc_i_raw)/len(loc_i_raw), sum(loc_e_raw)/len(loc_e_raw))
    
    # 2. Fuzzy Match (Broad Recommendation)
    rekomendasi_sektor_qA = engine.rekomendasi_per_domain(row_data)
    row_data['rekomendasi_sektor_qA'] = rekomendasi_sektor_qA
    # 3. Create User Vector (untuk Euclidean)
    vector_vals = engine.create_user_vector(row_data)
    row_data.update(vector_vals) # Masukkan score_SE, score_INN, dll ke row_data

    # 4. Euclidean Distance (Final Sector Ranking)
    jarak_sorted, top_picks = engine.final_sector(row_data, rekomendasi_sektor_qA) #jarak_s
    row_data["final_sector_qA"] = top_picks # List sektor terurut dari jarak terdekat
    sector_names_list = list(jarak_sorted.keys())
    
    # Simpan Top 3 & top 5 untuk Logic Refinement nanti
    row_data['top3_euclid_qA'] = sector_names_list[:3]
    row_data['top5_euclid_qA'] = sector_names_list[:5]

    # 5. Mapping Sektor -> Cluster A
    row_data['cluster_weights_top5_qA'] = engine.cluster_weights_from_top5_qA(row_data['top3_euclid_qA'])
    row_data['cluster_top5_best_qA'], row_data['cluster_top5_ranking_qA'] = engine.best_list_cluster_from_weights_qA(row_data['cluster_weights_top5_qA'])

    # Simpan mapping sektor mana saja yang masuk ke cluster terpilih
    row_data['top5_cluster_to_sector_qA'] = engine.top5_clusters_with_sectors_qA(row_data['top3_euclid_qA'])

    # ============================================
    # STEP B: PROSES BIG 5 PERSONALITY
    # ============================================

    # 1. Hitung Score & Notasi
    scores_B = engine.calculate_big5_scores(user_input)
    notations = engine.big5_notations(scores_B)
    row_data.update(notations) # Masukkan Note_O, Note_C, dll ke row_data
    
    # 2. Cari Cluster B (Euclidean Distance terhadap Prototype Simbol)
    best_name, best_score, list_names, list_scores = engine.assign_cluster_with_top5(row_data)

    row_data['top5_clusters_qB'] = list_names
    row_data['top5_clusters_qB_score'] = list_scores
    
    # 3. ambil nama cluster(-cluster) dengan nilai tertinggi
    row_data['cluster_top5_best_qB'] = engine.pick_best_clusters_qB_multi(row_data)

    # 4. ambil nilai tertinggi
    row_data['cluster_top5_best_qB_score'] = engine.pick_best_clusters_qB_score(row_data)

    # 5. 
    row_data["top5_cluster_to_sector_qB"] = engine.top5_clusters_with_matched_sectors_qB(row_data)
    
    # ============================================
    # STEP C: FINAL REFINEMENT (GABUNGAN)
    # ============================================
    
    final_clusters = engine.get_recommended_cluster_refined(row_data)
    # st.write(jarak_sorted)
    # # ============================================
    # # [DEBUGGING AREA] LIHAT ISI ROW DATA
    # # ============================================
    # st.info("Debugging Mode Active")
    # with st.expander("🔍 KLIK DISINI: Lihat Data Mentah (JSON Row Data)"):
    #     st.write("Ini adalah data lengkap hasil perhitungan sebelum ditampilkan ke UI:")
        # st.json(row_data) # <--- INI AKAN MENAMPILKAN SEMUA ISI DICTIONARY
        
    #     st.write("---")
    #     st.write("**Final Decision:**", final_clusters)


    # ============================================
    # TAMPILAN UI
    # ============================================
    scroll_to_here(0, key='scroll_hasil_single')
    st.success("Analisis Selesai! Berikut adalah hasil rekomendasi berdasarkan profil Anda.")
    st.header("🎯 Hasil Rekomendasi (Single Method)")
    # --- PANDUAN TERPADU ---
    with st.expander("📖 Panduan Cara Membaca Hasil Analisis", expanded=False):
        st.markdown("### Skor & Notasi")
        
        # Tabel Gabungan untuk Penilaian
        st.markdown("""
        | Level / Notasi | Interpretasi | Keterangan |
        | :--- | :--- | :--- |
        | **High / ++** | Sangat Tinggi | Karakteristik ini sangat dominan pada diri Anda. |
        | **Mid-High / +** | Tinggi | Anda memiliki potensi kuat pada aspek ini. |
        | **Mid-Low / 0** | Menengah | Karakteristik ini berada pada level rata-rata. |
        | **Low / -** | Rendah | Aspek ini bukan merupakan kekuatan utama Anda. |
        | **--** | Sangat Rendah | Aspek ini sama sekali bukan merupakan kekuatan utama Anda. |
        """)

        st.markdown("---")
        
        st.markdown("### Definisi Istilah")
        col_guide1, col_guide2 = st.columns(2)
        
        with col_guide1:
            st.markdown("""
            **Karakteristik Wirausaha:**
            * **Self-Efficacy**: Keyakinan pada kemampuan diri dalam mengerjakan atau melakukan sesuatu.
            * **Innovativeness**: Keinginan untuk mencoba ide dan cara baru yang kreatif.
            * **Need for Achievement**: Dorongan untuk mencapai kesuksesan dan prestasi.
            * **Locus of Control**: Keyakinan bahwa sukses ditentukan oleh usaha sendiri (Internal) atau faktor luar seperti orang lain, situasi, dan lainnya (External).
            """)
            
        with col_guide2:
            st.markdown("""
            **Dimensi Kepribadian (Big Five):**
            * **Openness**: Keterbukaan terhadap imajinasi dan pengalaman baru.
            * **Conscientiousness**: Tingkat ketelitian, disiplin, dan keteraturan.
            * **Extraversion**: Tingkat kenyamanan dalam interaksi sosial.
            * **Agreeableness**: Sikap kooperatif, ramah, dan peduli sesama.
            * **Neuroticism**: Stabilitas emosi (Skor tinggi = mudah cemas/gugup).
            """)

    # 2. DETAIL SEKTOR (OPEN ALL)
    st.markdown(
    """
    <h2 style='font-size: 36px; margin-bottom: 20px;'>
        Detail Sektor Pilihan (Top 3)
    </h2>
    """, 
    unsafe_allow_html=True
    )
    st.caption("Klik panah untuk melihat detail analisis setiap sektor.")
    

    # Pastikan data pendukung sudah siap
    sector_docs = engine.get_sector_descriptions()

    # LOOPING TOP 3 SEKTOR
    for i, s in enumerate(row_data['top3_euclid_qA']):
        
        # ----------------------------------------
        # 1. PERSIAPAN DATA (Teks & Skor)
        # ----------------------------------------
        
        # A. Ambil & Format Deskripsi
        desc_sector = sector_docs.get(s.title(), "")
        if desc_sector:
            # Ganti baris baru jadi <br>
            txt = desc_sector.replace('\n', '<br>')
            # Ganti **Bold** jadi <b>Bold</b> (Regex)
            txt = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #3FB68E;">\1</b>', txt)
        else:
            txt = "Deskripsi belum tersedia."

        # B. Hitung Skor Kecocokan (Real Euclidean)
        real_dist = jarak_sorted.get(s, 0)
        
        # Rumus Similarity: 1 / (1 + distance)
        similarity_score = (1 / (1 + real_dist)) * 100
        match_score = int(similarity_score)

        # C. Buat ID Anchor (untuk link jump)
        clean_id = s.lower().replace(" ", "-")
        st.markdown(f"<div id='{clean_id}' style='padding-top: 80px; margin-top: -80px; pointer-events: none;'></div>", unsafe_allow_html=True)
        
        # ----------------------------------------
        # 2. TAMPILAN UI (Render Expander)
        # ----------------------------------------
        
        # Siapkan Label Expander (Pindahkan Judul kesini)
        icon_rank = "🏆" if i == 0 else "🥈"
        label_exp = f"{icon_rank} {s.title()} (Skor: {match_score}%)"

        # Gunakan st.expander MENGGANTIKAN st.container
        # expanded=True hanya untuk juara 1 (i==0)
        with st.expander(label_exp, expanded=(i==0)):
            
            # Progress Bar
            st.progress(match_score, text=f"Tingkat Kecocokan: **{match_score}%**")
            
            st.markdown("---")
            

            # -----------------------------------------------------------
            # C. CHART HORIZONTAL (LEBIH RENGGANG)
            # -----------------------------------------------------------
            st.caption("📊 **Perbandingan Detail: Anda vs Target Kebutuhan Sektor**")
            
            # 1. Siapkan Data
            chart_data = []
            val_map = {"low": 1, "mid-low": 2, "mid-high": 3, "high": 4, 
                        "external": 2, "internal": 4, "-": 0}
            
            domains = [
                ("Innovativeness", "cat_innovativeness", "innovativeness"),
                ("Self-Efficacy", "cat_self_efficacy", "self_efficacy"),
                ("Need for Achievement", "cat_need_achievement", "need_achievement"),
                ("Locus of Control", "cat_loc", "loc")
            ]
            
            for label, u_key, r_key in domains:
                # Cari Target
                t_lvl = "low"
                d_rules = engine.rules.get(r_key, {})
                for lvl, sec_list in d_rules.items():
                    if any(x.lower() == s.lower() for x in sec_list):
                        t_lvl = lvl; break
                
                # Ambil User
                u_lvl = row_data.get(u_key, "low")
                
                # Masukkan Data
                chart_data.append({"Aspek": label, "Skor": val_map.get(str(u_lvl).lower(), 1), "Jenis": "1. Anda", "Level": str(u_lvl).title()})
                chart_data.append({"Aspek": label, "Skor": val_map.get(str(t_lvl).lower(), 1), "Jenis": "2. Target", "Level": str(t_lvl).title()})
            
            df_chart = pd.DataFrame(chart_data)

            # 2. Render Chart Horizontal (Altair)
            
            base = alt.Chart(df_chart).encode(
                # --- [UPDATE 1] Tambahkan padding di sini ---
                y=alt.Y('Aspek:N', 
                        axis=alt.Axis(title=None, labelFontSize=13, labelPadding=15, labelLimit=1000, minExtent=150), 
                        scale=alt.Scale(padding=0.4) # Padding 0.4 membuat jarak antar grup lebih lebar
                ), 
                x=alt.X('Skor:Q', axis=None, scale=alt.Scale(domain=[0, 4.5])), # Domain diperbesar dikit biar teks label muat
                color=alt.Color('Jenis:N', legend=alt.Legend(title=None, orient='bottom'), scale=alt.Scale(range=['#295ABB', "#3FB68E"]))
            )

            bars = base.mark_bar(height=12).encode(
                yOffset=alt.YOffset('Jenis:N', sort=['1. Anda', '2. Target']) 
            )

            # Label Teks
            text = base.mark_text(dx=5, align='left', color='black', fontSize=11).encode(
                yOffset=alt.YOffset('Jenis:N', sort=['1. Anda', '2. Target']),
                text='Level:N'
            )

            # --- [UPDATE 2] Perbesar Height Chart ---
            final_chart = (bars + text).properties(height=220).configure(background='transparent').configure_view(stroke='gray', strokeWidth=2)
            
            st.altair_chart(final_chart, use_container_width=True)

            st.markdown("---")
            
            # D. Deskripsi Text
            st.markdown(f"""
            <div class="info-box-blue">
                {txt}
            </div>
            """, unsafe_allow_html=True)

    # 3. HASIL CLUSTER (OPEN ALL)
    st.markdown("## Anda masuk ke klaster:")
    cluster_docs = engine.get_cluster_descriptions()
    
    if final_clusters:
        for i, cluster in enumerate(final_clusters):
            
            # Gunakan Expander MENGGANTIKAN Container
            label_cluster = f"#{i+1} {cluster}"
            
            with st.expander(label_cluster, expanded=True):
                
                # B. Deskripsi Cluster
                desc = cluster_docs.get(cluster, "")

                # --- PERBAIKAN FORMAT TEXT (BOLD & JUSTIFY) ---
                if desc:
                    # 1. Ganti baris baru jadi <br>
                    desc = desc.replace('\n', '<br>')
                    # 2. Ganti **Bold** jadi <b>Bold</b> (Regex)
                    desc = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #295ABB;">\1</b>', desc)

                # Render dengan Justify agar rapi
                st.markdown(f"""
                <div class="info-box-blue">
                    {desc}
                </div>
                """, unsafe_allow_html=True)
                
                # --- [UPDATE] KARTU PERBANDINGAN: USER VS TARGET ---
                rules = engine.big5_cluster_rules.get(cluster, {})
                
                if rules:
                    st.markdown("##### ⚖️ Kecocokan Kepribadian Anda vs Standar Klaster:")
                    
                    # Kita pakai 5 kolom
                    cols_b5 = st.columns(5)
                    traits = [
                        ("Openness", "O"), ("Conscientious", "C"), 
                        ("Extraversion", "E"), ("Agreeableness", "A"), 
                        ("Neuroticism", "N")
                    ]
                    
                    for idx, (trait_name, trait_code) in enumerate(traits):
                        # 1. Ambil Data
                        target_rule = rules.get(trait_code, "?")          # Misal: "0/+"
                        user_score = row_data.get(f'Note_{trait_code}')   # Misal: "-"
                        
                        # 2. Cek Kecocokan (Pakai fungsi engine)
                        is_match = engine.symbol_matches(user_score, target_rule)
                        
                        # 3. Tentukan Warna & Ikon
                        if is_match:
                            bg_color = "#d1e7dd" # Hijau Soft
                            text_color = "#0f5132"
                            border_color = "#badbcc"
                            icon = "✅"
                            status = "Sesuai"
                        else:
                            # Warna Kuning Soft (Kesan: Perlu Adaptasi)
                            bg_color = "#fff6cd" 
                            text_color = "#856404"
                            border_color = "#ffeeba"
                            icon = "❌"  # Atau bisa ganti "🔄" untuk kesan adaptasi
                            status = "Berbeda"
                        
                        # 4. Render Kartu Kecil
                        with cols_b5[idx]:
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: {bg_color}; 
                                    color: {text_color}; 
                                    padding: 10px 5px; 
                                    border-radius: 8px; 
                                    text-align: center; 
                                    border: 1px solid {border_color};
                                    font-size: 13px;
                                    line-height: 1.4;">
                                    <strong style="font-size:12px; text-transform:uppercase;">{trait_name}</strong><br>
                                    <div style="margin-top:5px; margin-bottom:5px; font-size: 16px;">{icon} <b>{status}</b></div>
                                    <hr style="margin: 5px 0; border-color: {text_color}; opacity: 0.3;">
                                    Target: <b>{target_rule}</b><br>
                                    Anda: <b>{user_score}</b>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                    
                    st.caption("ℹ️ **Target:** Syarat kepribadian klaster | **Anda:** Hasil tes kepribadian Anda.")
                
                st.divider()
                
                
                # C. Kecocokan Sektor (Link Clickable)
                all_sectors_in_cluster = engine.cluster_mapping.get(cluster, [])
                user_top_picks = row_data.get('top3_euclid_qA', [])
                
                matches = [s for s in all_sectors_in_cluster if s in user_top_picks]
                
                if matches:
                    links_html = []
                    for m in matches:
                        clean_id = m.lower().replace(" ", "-")
                        display_text = m.title()
                        links_html.append(f"<a href='#{clean_id}' target='_self' style='text-decoration:none; color: #7ED9BC; font-weight:bold; border-bottom:1px dashed #155724;'>{display_text}</a>")
                    
                    link_str = ", ".join(links_html)
                    st.markdown(
                        f"""
                        <div style="background-color:#e1f5fe; border-left:5px solid #2980b9; padding:10px; border-radius:5px; margin:10px 0; color:#0c5460;">
                            ⭐ <b>Sektor yang sesuai dengan Anda:</b> {link_str}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            
    
    # [UPDATE] Simpan ke Database (Single: Cluster & Sektor)
    user_id = st.session_state.get('current_user_id')
    if user_id:
        try:
            db = st.session_state['db']
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 1. Siapkan String Cluster
            str_cluster = ", ".join(final_clusters)
            
            # 2. Siapkan String Sektor (Single pakai Euclidean)
            str_sector = ", ".join(row_data.get('top3_euclid_qA', [])) 
            
            # 3. Update Database
            cursor.execute("""
                UPDATE mst_tbl 
                SET rec_single = %s, top3_sector_single = %s 
                WHERE user_id = %s
            """, (str_cluster, str_sector, user_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            # st.error(f"Error saving DB: {e}") # Aktifkan jika ingin debug
            pass

    else:
        st.warning("Tidak ditemukan cluster spesifik. Profil Anda sangat unik atau seimbang.")
       

    # ============================================
    # NAVIGASI PERPINDAHAN PAGE (UPDATE DISINI)
    # ============================================
    st.write("---")

    
    if st.button("🚀 Lanjut ke Analisis Hybrid", type="primary", use_container_width=True):
        st.session_state['halaman_sekarang'] = "hasil_hybrid"
        st.rerun()

def render_hasil_hybrid():
    # --- 0. CSS STYLE (Background & Helper Classes) ---
    st.markdown("""
    <style>
        /* 1. Background Halaman */
        .stApp {
            background-color: #F8F9F1;
        }

        /* 2. Kartu Big 5 Kecil */
        .big5-card {
            background-color: #fff;
            border-radius: 8px;
            padding: 10px 5px;
            text-align: center;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* 3. Styling Tombol Streamlit */
        div.stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        
        /* 4. Judul Expander Besar */
        div[data-testid="stExpander"] details summary p {
            font-size: 20px !important;
            font-weight: 700 !important;
            color: #154360 !important;
        }

        /* --- CLASS BARU UNTUK KOTAK DESKRIPSI (Ganti Inline CSS) --- */
        .info-box-blue {
            background-color: #EBF5FB; 
            border: 2px solid #AED6F1; 
            border-radius: 12px; 
            padding: 25px; 
            margin-bottom: 20px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            color: #0A0A44;
            font-size: 16px;
            line-height: 1.6;
            text-align: justify;
        }

        /* --- CLASS BARU UNTUK SEKTOR MATCHED (Ganti Inline CSS) --- */
        .sector-match-box {
            background-color: #e1f5fe;
            border-left: 5px solid #2980b9;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            color: #0c5460;
            font-size: 16px;
        }

        /* --- CLASS UNTUK LINK --- */
        .custom-link {
            text-decoration: none;
            color: #2980B9 !important;
            font-weight: bold;
            border-bottom: 1px dashed #2980B9;
        }
        .custom-link:hover {
            color: #154360 !important;
            border-bottom: 1px solid #154360;
        }

        /* Media Query HP */
        @media (max-width: 600px) {
            .mobile-text-left { text-align: left !important; }
            div[data-testid="stExpander"] details summary p {
                font-size: 18px !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    # ... (Bagian Load Data Sama) ...
    answers_1 = st.session_state.get('temp_answers_1', {})
    answers_2 = st.session_state.get('temp_answers_2', {})
    
    if not answers_1 or not answers_2:
        st.warning("Data belum lengkap.")
        return

    user_input = {**answers_1, **answers_2}
    engine = RecommenderEngine()
    row_data = user_input.copy() # Copy agar user_input aman

    # ============================================
    # STEP A: PROSES ENTREPRENEUR (EUCLIDEAN + TF-IDF)
    # ============================================
    
    # 1. Hitung Score & Kategori (Sama seperti sebelumnya)
    scores_A = engine.domain_cols_score(user_input)
    row_data.update(scores_A)
    
    row_data['cat_self_efficacy'] = engine.kategori_score(scores_A['self_efficacy'])
    row_data['cat_innovativeness'] = engine.kategori_score(scores_A['innovativeness'])
    row_data['cat_need_achievement'] = engine.kategori_score(scores_A['need_achievement'])
    
    # LOC Logic
    loc_i_raw = [user_input.get(k,3) for k in engine.domain_cols['loc_internal']]
    loc_e_raw = [user_input.get(k,3) for k in engine.domain_cols['loc_external']]
    val_i = sum(loc_i_raw)/len(loc_i_raw) if loc_i_raw else 0
    val_e = sum(loc_e_raw)/len(loc_e_raw) if loc_e_raw else 0
    row_data['cat_loc'] = engine.kategori_loc(val_i, val_e)

    # 2. Fuzzy Match & Vector
    rekomendasi_sektor_qA_hybrid = engine.rekomendasi_per_domain(row_data)
    row_data['rekomendasi_sektor_qA_hybrid'] = rekomendasi_sektor_qA_hybrid
    row_data.update(engine.create_user_vector(row_data))

    st.write("rekomendasi_sektor_qA_hybrid")
    st.write(rekomendasi_sektor_qA_hybrid)


    # 3. Euclidean Distance (Dapatkan Top 5 Awal)
    jarak_sorted, top_picks = engine.final_sector(row_data, rekomendasi_sektor_qA_hybrid)
    
    st.write("jarak sorted")
    st.write(jarak_sorted)

    # Simpan hasil Euclidean
    row_data['top3_euclid_qA_hybrid'] = list(jarak_sorted.keys())[:3]
    row_data['top5_euclid_qA_hybrid'] = list(jarak_sorted.keys())[:5]

    # --- BAGIAN BARU: CONTENT-BASED (TF-IDF) ---
    
    # 4. Build User Text Profile (Cell 34)
    row_data['user_text_profile_A_hybrid'] = engine.build_narrative_text(row_data, engine.likert_text_map)
    
    # 5. Hitung TF-IDF Similarity (Cell 39)
    # Menggunakan Top 5 Euclidean sebagai kandidat
    sector_docs = engine.get_sector_descriptions()

    candidates_A = {
        s: sector_docs.get(s, "")
        for s in row_data['top5_euclid_qA_hybrid'] 
        if s in sector_docs
    }

    # Panggil Generic Function
    top3_tfidf_A = engine.compute_tfidf_ranking(
        user_text=row_data['user_text_profile_A_hybrid'], 
        candidates_dict=candidates_A,
        lang='id',    # Settingan Lokal
        ngram=(1,1),  # Settingan Standar
        top_n=3   # Ambil 3 Terbaik
    )

    
    # 2. PROSES HASIL (PENTING: Ambil Namanya Saja)
    if top3_tfidf_A:
        # Extract nama sektor dari tuple (item[0])
        # Contoh: [('Software', 0.9), ('Construction', 0.8)] -> ['Software', 'Construction']
        top3_tfidf_A_names = [item[0] for item in top3_tfidf_A]
    else:
        # Fallback: Jika TF-IDF gagal/kosong, ambil dari Euclidean (Keys sudah berupa string)
        top3_tfidf_A_names = list(jarak_sorted.keys())[:3]

    row_data['top3_tfidf_A_hybrid'] = top3_tfidf_A
    row_data['top3_tfidf_sector_hybrid'] = top3_tfidf_A_names

    # 7. Cluster Weights dari Top 3 TF-IDF (Cell 52)
    # Perhatikan: Inputnya sekarang 'top3_tfidf_sector' sesuai notebook
    weights_A = engine.cluster_weights_from_top5_qA(row_data['top3_tfidf_sector_hybrid'])
    
    juara_A_list, ranking_A_list = engine.best_list_cluster_from_weights_qA(weights_A)
    
    row_data['cluster_top5_best_qA_hybrid'] = juara_A_list
    row_data['cluster_top5_ranking_qA_hybrid'] = ranking_A_list
    row_data['top3_cluster_to_sector_qA_hybrid'] = engine.top5_clusters_with_sectors_qA(row_data['top3_tfidf_sector_hybrid'])
    

    # ============================================
    # STEP B: PROSES BIG 5 (Sama seperti sebelumnya)
    # ============================================
    scores_B = engine.calculate_big5_scores(user_input)
    notations = engine.big5_notations(scores_B)
    row_data.update(notations)

    _, _, list_names_B, list_scores_B = engine.assign_cluster_with_top5(row_data)
    row_data['top3_clusters_qB_hybrid'] = list_names_B[:3]
    row_data['top3_clusters_qB_score_hybrid'] = list_scores_B[:3]


    cluster_docs = engine.get_cluster_descriptions()
    # TF IDF
    row_data['user_text_profile_B_hybrid'] = engine.build_narrative_text(row_data, engine.qb_text_mapping)
    candidates_B_hybrid = {
        s: cluster_docs.get(s, "")
        for s in row_data['top3_clusters_qB_hybrid'] 
        if s in cluster_docs
    }


    # Panggil Generic Function
    top3_tfidf_B_hybrid = engine.compute_tfidf_ranking(
        user_text=row_data["user_text_profile_B_hybrid"], 
        candidates_dict=candidates_B_hybrid,
        lang='id',    # Settingan Lokal
        ngram=(1,1),  # Settingan Standar
        top_n=3       # Ambil 3 Terbaik
    )

    # Fallback: Jika TF-IDF gagal/kosong, ambil dari perhitungan Euclidean (list_scores_B)
    if not top3_tfidf_B_hybrid:
        # st.write("masuk 1")
        # Ambil Top 1 dari Euclidean jika TF-IDF gagal
        best_qB_cluster_tfidf_hybrid = list_names_B[0] if list_names_B else "Unknown"
        best_qB_score_tfidf_hybrid = 0.0
        
        # Format ulang agar kompatibel (List of tuples)
        top3_tfidf_B_score_hybrid = [(best_qB_cluster_tfidf_hybrid, best_qB_score_tfidf_hybrid)]
    else:
        # st.write("masuk 2")
        # Ambil Juara 1 dari hasil TF-IDF
        best_qB_cluster_tfidf_hybrid = top3_tfidf_B_hybrid[0][0] # Ambil Nama
        best_qB_score_tfidf_hybrid = top3_tfidf_B_hybrid[0][1]   # Ambil Skor
        
    
    # top 1
    row_data['cluster_top3_best_qB_hybrid'] = best_qB_cluster_tfidf_hybrid
    row_data['cluster_top3_best_qB_score_hybrid'] = best_qB_score_tfidf_hybrid

    #top 3
    row_data['top3_cluster_tfidf_qB_hybrid'] = top3_tfidf_B_hybrid
    row_data['top3_cluster_tfidf_qB_score_hybrid'] = top3_tfidf_B_hybrid

    # st.write(row_data['top3_cluster_tfidf_qB_hybrid'])
    
    # matching
    top3_cluster_to_sector_qB_hybrid = engine.top3_clusters_with_matched_sectors_qB(row_data)
    row_data['top3_cluster_to_sector_qB_hybrid'] = top3_cluster_to_sector_qB_hybrid
    
    
    # top sectors matched
    row_data['top3_sector_matched'] = [item for sublist in top3_cluster_to_sector_qB_hybrid.values() for item in sublist]
    # st.write(row_data['top3_sector_matched'])

    # ============================================
    # STEP C: FINAL REFINEMENT (HYBRID)
    # ============================================
    final_clusters_hybrid = engine.get_recommended_cluster_refined_hybrid(row_data)

    # st.write(final_clusters_hybrid)
    # ============================================
    # [DEBUGGING AREA] LIHAT ISI ROW DATA
    # ============================================
    st.info("Debugging Mode Active")
    with st.expander("🔍 KLIK DISINI: Lihat Data Mentah (JSON Row Data)"):
        st.write("Ini adalah data lengkap hasil perhitungan sebelum ditampilkan ke UI:")
        st.json(row_data) # <--- INI AKAN MENAMPILKAN SEMUA ISI DICTIONARY
    
    # ============================================
    # TAMPILAN UI
    # ============================================

    scroll_to_here(0, key='scroll_hasil_hybrid')
    # 2. Panggil fungsi untuk loncat ke jangkar tersebut
    st.header("🎯 Hasil Rekomendasi (Hybrid Method)")

    # --- PANDUAN TERPADU ---
    with st.expander("📖 Panduan Cara Membaca Hasil Analisis", expanded=False):
        st.markdown("### Skor & Notasi")
        
        # Tabel Gabungan untuk Penilaian
        st.markdown("""
        | Level / Notasi | Interpretasi | Keterangan |
        | :--- | :--- | :--- |
        | **High / ++** | Sangat Tinggi | Karakteristik ini sangat dominan pada diri Anda. |
        | **Mid-High / +** | Tinggi | Anda memiliki potensi kuat pada aspek ini. |
        | **Mid-Low / 0** | Menengah | Karakteristik ini berada pada level rata-rata. |
        | **Low / -** | Rendah | Aspek ini bukan merupakan kekuatan utama Anda. |
        | **--** | Sangat Rendah | Aspek ini sama sekali bukan merupakan kekuatan utama Anda. |
        """)

        st.markdown("---")
        
        st.markdown("### Definisi Istilah")
        col_guide1, col_guide2 = st.columns(2)
        
        with col_guide1:
            st.markdown("""
            **Karakteristik Wirausaha:**
            * **Self-Efficacy**: Keyakinan pada kemampuan diri dalam mengerjakan atau melakukan sesuatu.
            * **Innovativeness**: Keinginan untuk mencoba ide dan cara baru yang kreatif.
            * **Need for Achievement**: Dorongan untuk mencapai kesuksesan dan prestasi.
            * **Locus of Control**: Keyakinan bahwa sukses ditentukan oleh usaha sendiri (Internal) atau faktor luar seperti orang lain, situasi, dan lainnya (External).
            """)
            
        with col_guide2:
            st.markdown("""
            **Dimensi Kepribadian (Big Five):**
            * **Openness**: Keterbukaan terhadap imajinasi dan pengalaman baru.
            * **Conscientiousness**: Tingkat ketelitian, disiplin, dan keteraturan.
            * **Extraversion**: Tingkat kenyamanan dalam interaksi sosial.
            * **Agreeableness**: Sikap kooperatif, ramah, dan peduli sesama.
            * **Neuroticism**: Stabilitas emosi (Skor tinggi = mudah cemas/gugup).
            """)

    # -----------------------------------------------------------
    # 1. DETAIL SEKTOR (SEKARANG DI ATAS) - PAKAI EXPANDER
    # -----------------------------------------------------------
    
    st.markdown("<h2 style='font-size: 26px; margin-bottom: 20px;'>Detail Sektor Pilihan (Top 3 Hybrid)</h2>", unsafe_allow_html=True)
    st.caption("Klik panah untuk melihat detail analisis sektor.")

    # Logika Target Sektor
    target_sectors = row_data.get('top3_tfidf_sector_hybrid', [])
    target_sectors = list(dict.fromkeys(target_sectors)) # Hapus duplikat

    # Kamus Skor TF-IDF
    tfidf_map = {name: score for name, score in top3_tfidf_A} if top3_tfidf_A else {}

    for i, s in enumerate(target_sectors[:3]):
        
        # Deskripsi
        desc_sector = sector_docs.get(s.title(), "")
        txt = desc_sector.replace('\n', '<br>') if desc_sector else "Deskripsi belum tersedia."
        txt = re.sub(r'\*\*(.*?)\*\*', r'<b style="color: #3FB68E;">\1</b>', txt)

        # Hitung Skor (TF-IDF > Euclidean)
        tfidf_val = tfidf_map.get(s)
        if tfidf_val is not None:
            match_score = int(tfidf_val * 100)
            score_type_color = "#2196F3" # Biru (Text Match)
        else:
            real_dist = jarak_sorted.get(s, 0)
            match_score = int((1 / (1 + real_dist)) * 100)
            score_type_color = "#555" # Abu (Data Match)

        clean_id = s.lower().replace(" ", "-")
        # Pointer events none agar tidak menghalangi klik expander
        st.markdown(f"<div id='{clean_id}' style='padding-top: 80px; margin-top: -80px; pointer-events: none;'></div>", unsafe_allow_html=True)
        
        # LABEL EXPANDER SEKTOR
        icon_rank = "🥇" if i == 0 else "🥈"
        label_exp = f"{icon_rank} {s.title()} (Skor: {match_score}%)"

        # RENDER EXPANDER SEKTOR
        with st.expander(label_exp, expanded=(i==0)):
            
            st.progress(match_score, text=f"Kecocokan Profil: {match_score}%")
            st.markdown("---")

            # CHART (Altair Transparan & Responsif)
            st.caption("📊 Perbandingan Detail: Anda vs Target")
            
            chart_data = []
            val_map = {"low": 1, "mid-low": 2, "mid-high": 3, "high": 4, "external": 2, "internal": 4, "-": 0}
            domains = [("Innovativeness", "cat_innovativeness", "innovativeness"), ("Self-Efficacy", "cat_self_efficacy", "self_efficacy"), ("Need for Achievement", "cat_need_achievement", "need_achievement"), ("LOC", "cat_loc", "loc")]
            
            for label, u_key, r_key in domains:
                t_lvl = "low"
                d_rules = engine.rules.get(r_key, {})
                for lvl, sec_list in d_rules.items():
                    if any(x.lower() == s.lower() for x in sec_list):
                        t_lvl = lvl; break
                u_lvl = row_data.get(u_key, "low")

                chart_data.append({"Aspek": label, "Skor": val_map.get(str(u_lvl).lower(), 1), "Jenis": "1. Anda", "Level": str(u_lvl).title()})
                chart_data.append({"Aspek": label, "Skor": val_map.get(str(t_lvl).lower(), 1), "Jenis": "2. Target", "Level": str(t_lvl).title()})
            
            df_chart = pd.DataFrame(chart_data)

            # Render Chart
            base = alt.Chart(df_chart).encode(
                y=alt.Y('Aspek:N', axis=alt.Axis(title=None, labelFontSize=13, labelLimit=120), scale=alt.Scale(padding=0.3)), 
                x=alt.X('Skor:Q', axis=None, scale=alt.Scale(domain=[0, 4.5])),
                color=alt.Color('Jenis:N', scale=alt.Scale(range=['#2196F3', '#3FB68e']))
            )
            bars = base.mark_bar(height=15).encode(yOffset=alt.YOffset('Jenis:N'))
            text = base.mark_text(dx=5, align='left').encode(yOffset=alt.YOffset('Jenis:N'), text='Level:N')
            
            final_chart = (bars + text).properties(height=220).configure(background='transparent').configure_view(stroke='gray', strokeWidth=2)
            st.altair_chart(final_chart, use_container_width=True)
            
            st.markdown("---")
            # Inline style untuk justify text deskripsi
            st.markdown(f"""
            <div class="info-box-blue">
                {txt}
            </div>
            """, unsafe_allow_html=True)

    # -----------------------------------------------------------
    # 2. HASIL CLUSTER (SEKARANG DI BAWAH) - PAKAI EXPANDER
    # -----------------------------------------------------------
    st.write("---")
    st.markdown("## Anda masuk ke klaster profil:")
    
    if final_clusters_hybrid:
        for i, cluster in enumerate(final_clusters_hybrid):
            
            # LABEL EXPANDER KLASTER
            label_cluster = f"#{i+1} {cluster}"
            
            # RENDER EXPANDER KLASTER
            with st.expander(label_cluster, expanded=True):
                
                desc = cluster_docs.get(cluster, "")
                if desc:
                    # 1. Ganti baris baru
                    desc = desc.replace('\n', '<br>')
                    
                    # 2. Ganti **Bold** jadi HTML (Gunakan kutip satu ' di dalam style agar aman)
                    # Pastikan ada huruf 'r' di depan tanda kutip regex
                    desc = re.sub(r'\*\*(.*?)\*\*', r"<b style='color: #3FB68E;'>\1</b>", desc)
                st.markdown(f"""
                <div class="info-box-blue">
                    {desc}
                </div>
                """, unsafe_allow_html=True)
                
                # KARTU BIG 5
                rules = engine.big5_cluster_rules.get(cluster, {})
                if rules:
                    st.markdown("##### ⚖️ Kecocokan Kepribadian vs Standar Klaster:")
                    cols_b5 = st.columns(5)
                    traits = [("Openness", "O"), ("Conscientious", "C"), ("Extraversion", "E"), ("Agreeableness", "A"), ("Neuroticism", "N")]
                    
                    for idx, (trait_name, trait_code) in enumerate(traits):
                        target_rule = rules.get(trait_code, "?")
                        user_score = row_data.get(f'Note_{trait_code}')
                        is_match = engine.symbol_matches(user_score, target_rule)
                        
                        if is_match:
                            bg, txt, border, icon, status = "#d1e7dd", "#0f5132", "#badbcc", "✅", "Sesuai"
                        else:
                            bg, txt, border, icon, status = "#fff3cd", "#856404", "#ffeeba", "❌", "Beda"
                        
                        with cols_b5[idx]:
                            st.markdown(f"""
                                <div class="big5-card" style="background-color:{bg}; color:{txt}; border:1px solid {border};">
                                    <strong style="font-size:11px;">{trait_name}</strong><br>
                                    <div style="margin:5px 0; font-size:16px;">{icon} <b>{status}</b></div>
                                    <hr style="margin:5px 0; opacity:0.3;">
                                    <span style="font-size:11px;">Target: <b>{target_rule}</b><br>Anda: <b>{user_score}</b></span>
                                </div>
                                """, unsafe_allow_html=True)
                
                st.divider()

                # SEKTOR MATCHED
                sectors = engine.cluster_mapping.get(cluster, [])
                matched = [s for s in sectors if s in row_data['top3_sector_matched']]
                
                if matched:

                    links_html = []
                    for m in matched:
                        clean_id = m.lower().replace(" ", "-")
                        links_html.append(f"<a href='#{clean_id}' target='_self' style='text-decoration:none; color:#2980B9; font-weight:bold; border-bottom:1px dashed #2980B9;'>{m.title()}</a>")
                    
                    link_str = ", ".join(links_html)
                    
                    st.markdown(
                        f"""
                        <div style="background-color:#e1f5fe; border-left:5px solid #2980b9; padding:10px; border-radius:5px; margin:10px 0; color:#0c5460;">
                            ⭐ <b>Sektor yang sesuai dengan Anda:</b> {link_str}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    remaining = [s for s in sectors if s not in matched]
                    if remaining: st.caption(f"Opsi lain di klaster ini: {', '.join(remaining)}")
                else:
                    st.caption(f"Sektor dalam klaster ini: {', '.join(sectors)}")

    else:
        st.warning("Tidak ditemukan cluster spesifik.")

    # 4. SIMPAN KE DB
    user_id = st.session_state.get('current_user_id')
    if user_id:
        try:
            db = st.session_state['db']
            conn = db.get_connection()
            cursor = conn.cursor()
            str_cluster = ", ".join(final_clusters_hybrid)
            str_sector = ", ".join(target_sectors)
            cursor.execute("UPDATE mst_tbl SET rec_hybrid = %s, top3_sector_hybrid = %s WHERE user_id = %s", (str_cluster, str_sector, user_id))
            conn.commit(); conn.close()
        except: pass

    # NAVIGASI
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🚀 Lanjut ke Summary", type="primary", use_container_width=True):
            st.session_state['halaman_sekarang'] = "hasil_summary"
            st.rerun()
    with col_btn2:
        if st.button("⏮️ Back to Single", use_container_width=True):
            st.session_state['halaman_sekarang'] = "hasil_single"
            st.rerun()


def render_comparison_dashboard():
    # --- 1. CSS STYLING (Tema Pastel Blue & Responsif) ---
    st.markdown("""
    <style>
    /* Background Halaman */
    .stApp {
        background-color: #F8F9F1;
    }

    /* Box Cluster (Biru Muda) */
    .cluster-box {
        background-color: #EBF5FB; 
        border: 2px solid #AED6F1;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        font-weight: 700;
        color: #154360;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        font-size: 16px;
    }

    /* Box Cluster Hybrid (Sedikit Beda Warna Border) */
    .cluster-box-hybrid {
        background-color: #E8F8F5; /* Hijau Mint Sangat Muda */
        border: 2px solid #A3E4D7; 
        color: #0E6251;
    }

    /* Judul Kolom */
    .col-header {
        text-align: center;
        font-size: 20px;
        font-weight: 800;
        color: #0A0A44;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Styling Tombol */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Responsive adjustment */
    @media (max-width: 600px) {
        .col-header { font-size: 18px; margin-top: 20px; }
    }
    </style>
    """, unsafe_allow_html=True)

    scroll_to_here(0, key='summary')

    st.title("⚖️ Perbandingan Hasil Rekomendasi")

    user_id = st.session_state.get('current_user_id')
    if not user_id:
        st.warning("⚠️ User ID tidak ditemukan. Silakan isi profil ulang.")
        return

    # 2. FETCH DATA DARI DATABASE
    if 'db' not in st.session_state:
        st.session_state['db'] = DatabaseManager()
    
    db = st.session_state['db']
    conn = db.get_connection()
    
    # Ambil 4 Kolom Penting
    df = pd.read_sql_query(f"""
        SELECT rec_single, top3_sector_single, rec_hybrid, top3_sector_hybrid 
        FROM mst_tbl WHERE user_id = '{user_id}'
    """, conn)
    conn.close()

    if df.empty:
        st.error("Data tidak ditemukan di database.")
        return

    # 3. PARSING DATA (String -> List)
    row = df.iloc[0]
    
    def parse_db_str(s):
        if not s: return []
        return [x.strip() for x in s.split(",")]

    final_single = parse_db_str(row['rec_single'])
    sectors_single = parse_db_str(row['top3_sector_single'])
    
    final_hybrid = parse_db_str(row['rec_hybrid'])
    sectors_hybrid = parse_db_str(row['top3_sector_hybrid'])

    # Cek Data Kosong
    if not final_single or not final_hybrid:
        st.warning("⚠️ Data belum lengkap. Pastikan Anda menyelesaikan proses Single dan Hybrid.")
        return

    # --- 4. TAMPILAN UI ---
    col1, col2 = st.columns(2, gap="medium")

    # === KOLOM KIRI: SINGLE ===
    with col1:
        st.markdown("<h3 style='text-align: center;'>Single Method</h3>", unsafe_allow_html=True)
        
        # Cluster
        if len(final_single) > 1:
            c1, c2 = st.columns(2)
            with c1: st.markdown(f"<div class='cluster-box'>{final_single[0]}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='cluster-box'>{final_single[1]}</div>", unsafe_allow_html=True)
        elif len(final_single) == 1:
             st.markdown(f"<div class='cluster-box'>{final_single[0]}</div>", unsafe_allow_html=True)

        # Sektor
        with st.container(border=True):
            st.markdown("#### 🏢 Top 3 Business Sector")
            st.markdown("---")
            for i, s in enumerate(sectors_single):
                st.write(f"**{i+1}. {s}**")

    # === KOLOM KANAN: HYBRID ===
    with col2:
        st.markdown("<h3 style='text-align: center;'>Hybrid Method</h3>", unsafe_allow_html=True)
        
        # Cluster
        if len(final_hybrid) > 1:
            c1, c2 = st.columns(2)
            with c1: st.markdown(f"<div class='cluster-box cluster-box-hybrid'>{final_hybrid[0]}</div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='cluster-box cluster-box-hybrid'>{final_hybrid[1]}</div>", unsafe_allow_html=True)
        elif len(final_hybrid) == 1:
             st.markdown(f"<div class='cluster-box cluster-box-hybrid'>{final_hybrid[0]}</div>", unsafe_allow_html=True)

        # Sektor
        with st.container(border=True):
            st.markdown("#### 🚀 Top 3 Business Sector")
            st.markdown("---")
            for i, s in enumerate(sectors_hybrid):
                if s not in sectors_single:
                    st.write(f"**{i+1}. {s}** (🆕)")
                else:
                    st.write(f"**{i+1}. {s}**")


    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        # TOMBOL PINDAH KE HYBRID
        if st.button("⏮️ Back to Single", type="primary", use_container_width=True):
            st.session_state['halaman_sekarang'] = "hasil_single"
            st.rerun()

    with col_btn2:
        # TOMBOL RESET
        if st.button("⏮️ Back to Hybrid", type="primary", use_container_width=True):
            st.session_state['halaman_sekarang'] = "hasil_hybrid"
            st.rerun()

    render_feedback_section(user_id, db, sectors_single, sectors_hybrid)

    


def main():

    st.set_page_config(page_title="Form Profil", layout="wide")
    # --- [FIX] INISIALISASI DATABASE DISINI ---
    # Cek dulu: Apakah 'db' sudah ada di tas? Kalau belum, masukkan sekarang.
    if 'db' not in st.session_state:
        st.session_state['db'] = DatabaseManager()
        

    # Inisialisasi session state (jika belum ada)
    if 'halaman_sekarang' not in st.session_state:
        st.session_state['halaman_sekarang'] = "cover"
    
    # --- ROUTING / NAVIGASI ---
    page = st.session_state['halaman_sekarang']

    if page == "cover":
        render_cover_page()

    elif page == "profil":
        render_profile()
        
    elif page == "part_1":     
        render_part_1()
        
    elif page == "part_2":     
        render_part_2()
    
    elif page == "hasil_single":      
        render_hasil_single()
    
    elif page == "hasil_hybrid":      
        render_hasil_hybrid()

    elif page == "hasil_summary": 
        render_comparison_dashboard()

if __name__ == "__main__":

    main()

