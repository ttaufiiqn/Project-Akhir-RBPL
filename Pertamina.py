import streamlit as st
import mysql.connector
from mysql.connector import Error
import time
from datetime import datetime
import pandas as pd
from streamlit_calendar import calendar
import os 
import plotly.express as px
import plotly.graph_objects as go
from plotly import data


st.set_page_config(
    page_title= "Pertamina Retail",
    page_icon= "🐸",
)

# Fungsi buat koneksi ke database MySQL
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost', 
            user='root', 
            password='', 
            database='pertamina'
        )
        if connection.is_connected():
            print("Koneksi ke MySQL berhasil")
    except Error as e:
        print(f"Error: '{e}'")
    return connection

# Fungsi untuk memeriksa kredensial pengguna
def check_credentials(nip, password, connection):
    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM user WHERE nip = %s AND password = %s"
    cursor.execute(query, (nip, password))
    user = cursor.fetchone()
    cursor.close()
    return user

# Fungsi untuk mengambil data tertentu
def get_user_data(nip, connection, columns):
    cursor = connection.cursor(dictionary=True)
    query = f"SELECT {', '.join(columns)} FROM user WHERE nip = %s"
    cursor.execute(query, (nip,))
    data = cursor.fetchone()
    cursor.close()
    return data

# Fungsi untuk mengambil nama dari NIP yang diinputkan
def get_user_name(nip, connection):
    cursor = connection.cursor()
    query = "SELECT nama FROM user WHERE nip = %s"
    cursor.execute(query, (nip,))
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return result[0]  # Ambil nama dari hasil query jika ada
    else:
        return None  # Kembalikan None jika tidak ada hasil yang ditemukan
    

# Fungsi untuk menampilkan halaman dashboard
def show_dashboard(nip, connection):
    nip = st.session_state.get('nip', 'Tidak diketahui')
    st.title("Pertamina Retail Data Visualization")

    nama = get_user_name(nip, connection)
    st.subheader(f"Selamat datang, {nama}!")

    calendar_options = {
        "editable": "true",
        "selectable": "true",
        "headerToolbar": {
            "left": "today",
            "center": "title",
            "right": "prev,next",
        },

    }

    custom_css="""
        .fc-toolbar-title {
            font-size: 2rem;
        }
    """

    kalender = calendar(options=calendar_options, custom_css=custom_css)

    # Komponen Streamlit untuk menampilkan waktu
    placeholder = st.empty()

    # Loop untuk memperbarui waktu setiap detik
    while True:
        # Mendapatkan waktu saat ini
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Memperbarui placeholder dengan waktu saat ini
        placeholder.title(f"{current_time}")
        
        # Tunggu 1 detik sebelum memperbarui lagi
        time.sleep(1)

#Fungsi halaman login
def login_page():
    # Judul
    st.title("Login")

    # Form login
    nip = st.text_input("NIP")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    # Autentikasi
    if login_button:
        if connection and connection.is_connected():
            user = check_credentials(nip, password, connection)
            if user:
                st.success("Login berhasil!")
                st.session_state.logged_in = True
                if 'nip' not in st.session_state:
                    st.session_state.nip = nip
                # Menuju dashboard
                #redirect_to_dashboard(nip)
            else:
                st.error("NIP atau password salah")
        else:
            st.error("Koneksi ke database gagal")


# Fungsi untuk menyimpan path file ke database
def insert_file_path_to_db(connection, file_path, tanggal, nip):
    cursor = connection.cursor()
    query = "INSERT INTO data_input (tanggal, file, nip) VALUES (%s, %s, %s)"
    cursor.execute(query, (tanggal, file_path, nip))
    connection.commit()
    cursor.close()


def insert_file_to_db(connection, df):
    cursor = connection.cursor()
    for index, row in df.iterrows():
        query = """
            INSERT INTO file (tanggal, spbu_id, spbu_name, location, transaction_id, payment_id, payment_type, amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
        try:
            cursor.execute(query, (row["tanggal"], row["spbu_id"], row["spbu_name"], row["location"], row["transaction_id"], row["payment_id"], row["payment_type"], row["amount"]))
        except Error as e:
            print(f"Error inserting data: {e}")
    connection.commit()
    cursor.close()

def page_upload_data(nip, connection):
    st.title("Upload Data")
    #upload file csv
    with st.form("csv_upload_form"):
        uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
        submit_button = st.form_submit_button("Upload")

    if uploaded_file is not None:
        # Membaca file CSV
        df = pd.read_csv(uploaded_file)

        # Menambahkan kolom tanggal di DataFrame
        current_date = datetime.now().date()
        df['tanggal'] = current_date


        column_order = ['tanggal'] + [col for col in df.columns if col != 'tanggal']
        df = df[column_order]

        # Menampilkan DataFrame di Streamlit
        st.write("Isi file CSV yang diunggah:")
        st.write(df)

    if uploaded_file is not None:
        # Menyimpan file yang diunggah ke direktori lokal
        save_directory = 'uploaded_files'
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        
        file_path = os.path.join(save_directory, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.write("File berhasil diunggah ke:", file_path)
        
        current_date = datetime.now().date()
        nip = st.session_state.get('nip', 'Tidak diketahui')  # Mengambil nip dari session state
        
        # Membuat koneksi ke database
        connection = create_connection()
        
        if connection is not None:
            try:
                insert_file_path_to_db(connection, file_path, current_date, nip)
                st.success('Path file dan isi file berhasil disimpan ke database!')
            except Error as e:
                st.error(f'Terjadi kesalahan saat memasukkan data: {e}')

            try:
                insert_file_to_db(connection, df)
            except Error as e:
                st.error(f'Terjadi kesalahan saat memasukkan data file: {e}')
            finally:
                connection.close()
    else:
        st.write("Silahkan unggah file")

# Fungsi utama untuk navigasi
def main(nip, connection):
    st.sidebar.title("Navbar")
    page = st.sidebar.selectbox("Pilih halaman", ["Dashboard", "Data dan Pencarian", "Visualisasi Data", "Upload Data"])
    
    # Dictionary yang memetakan nama halaman ke fungsi yang sesuai
    pages = {
        "Dashboard": show_dashboard,
        "Data dan Pencarian": page_data,
        "Visualisasi Data": page_visualisasi,
        "Upload Data": page_upload_data
    }

    # Membuat koneksi ke database
    connection = create_connection()

    # Mengecek apakah file akan dibuka
    if 'file_to_open' in st.session_state:
        page_file(st.session_state['file_to_open'])
    else:
        nip = st.session_state.get('nip', 'Tidak diketahui')
        pages[page](nip, connection)


def search_by_id_data(search_id):
    try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM data_input WHERE id_data = %s"
            cursor.execute(query, (search_id,))
            search_results = cursor.fetchall()
            df = pd.DataFrame(search_results)
            
            if not df.empty:
                st.write(f"Hasil pencarian untuk ID '{search_id}':")
                st.dataframe(df)
            else:
                st.write(f"Tidak ada hasil untuk ID '{search_id}'")
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def search_by_date_data(search_date):
     try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file WHERE tanggal = %s"
            cursor.execute(query, (search_date,))
            search_results = cursor.fetchall()
            df = pd.DataFrame(search_results)
            
            if not df.empty:
                st.write(f"Hasil pencarian untuk ID '{search_date}':")
                st.dataframe(df)
            else:
                st.write(f"Tidak ada hasil untuk ID '{search_date}'")
     except mysql.connector.Error as err:
        st.error(f"Error: {err}")
     finally:
        cursor.close()
        connection.close()

def search_data(search_isi_data):
    try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file WHERE %s"
            cursor.execute(query, (search_isi_data,))
            search_results = cursor.fetchall()
            df = pd.DataFrame(search_results)
            
            if not df.empty:
                st.write(f"Hasil pencarian untuk '{search_isi_data}':")
                st.dataframe(df)
            else:
                st.write(f"Tidak ada hasil pencarian untuk '{search_isi_data}'")
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def page_data(nip, connection):
    
        page = st.sidebar.selectbox("Pilih Opsi", ["Data yang sudah diupload", "Isi Data"])
            
            # Dictionary yang memetakan nama halaman ke fungsi yang sesuai
        pages = {
                "Data yang sudah diupload": page_list_data,
                "Isi Data": read_data,
            }

        pages[page]()
        

def page_list_data():
    st.title("Data dan Pencarian")
    search_id = st.text_input("Masukkan Id_data untuk mencari")

    if search_id:
        search_by_id_data(search_id)

    else:
        st.write("")
        st.subheader("DAFTAR DATA YANG SUDAH DI UPLOAD")
    # dataset
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM data_input"
            cursor.execute(query)
            all_data = cursor.fetchall()
            df = pd.DataFrame(all_data)

            st.dataframe(df)

        except mysql.connector.Error as err:
            st.error(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def read_data():
    page = st.sidebar.selectbox("Pilih data yang ingin ditampilkan", ["Semua Data", "Data Hari Ini", "Data Bulan Ini"])
            
    # Dictionary yang memetakan nama halaman ke fungsi yang sesuai
    pages = {
                "Semua Data": alldata,
                "Data Hari Ini": daily_data,
                "Data Bulan Ini": montly_data,
            }

    pages[page]()   


def alldata():
    st.title("Data dan Pencarian")
   # st.subheader("Semua Data")
    search_date = st.text_input("Masukkan tanggal untuk mencari")
    if search_date:
        search_by_date_data(search_date)

    else:
        st.write("")
        st.subheader("ISI SEMUA DATA YANG SUDAH DI UPLOAD")
    # dataset
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file"
            cursor.execute(query)
            all_data = cursor.fetchall()
            df = pd.DataFrame(all_data)

            st.dataframe(df)

        except mysql.connector.Error as err:
            st.error(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()
    
def daily_data():
    st.title("Data dan Pencarian")
    st.subheader("Data Hari Ini")
    search_isi_data = st.text_input("Data yang akan dicari")
    if search_isi_data:
        search_data(search_isi_data)

    else:
        st.write("")
        st.subheader("ISI DATA YANG SUDAH DI UPLOAD")
        current_date = datetime.now().date()
    # dataset
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file WHERE tanggal = %s"
            cursor.execute(query, (current_date,))
            daily_data = cursor.fetchall()
            df = pd.DataFrame(daily_data)
            if daily_data: 
                #st.write(daily_data)
                st.dataframe(df)
            else : 
                st.write(f"Data hari ini ({current_date}) belum di Upload. Silahkan upload data terlebih dahulu")

        except mysql.connector.Error as err:
            st.error(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()
    
def montly_data(): 
    st.title("Data dan Pencarian")
    #st.subheader("Data Bulan Ini")
    search_date = st.text_input("Masukkan tanggal untuk mencari")
    if search_date:
        search_by_date_data(search_date)

    else:
        st.write("")
        st.subheader("ISI DATA YANG SUDAH DI UPLOAD BULAN INI")
    # dataset
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file"
            cursor.execute(query)
            all_data = cursor.fetchall()
            df = pd.DataFrame(all_data)

            st.dataframe(df)

        except mysql.connector.Error as err:
            st.error(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

# Fungsi untuk menampilkan halaman isi file
def page_file(file_path):
    st.title("Isi File")
    try:
        df = pd.read_csv(file_path)
        st.write("Isi file CSV:")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Kembali"):
        st.session_state.pop('file_to_open', None)
        st.rerun()

def load_and_process_file_from_path(file_path):
    if file_path and os.path.exists(file_path):
        # Membaca file CSV ke dalam DataFrame
        df = pd.read_csv(file_path)
        return df
    else:
        st.error("File path tidak ditemukan atau file tidak ada.")
        return None

def get_file_path_from_db(connection, current_date):
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT file FROM data_input WHERE tanggal = %s"
        cursor.execute(query, (current_date,))
        result = cursor.fetchone()
        if result:
            return result['file']
        else:
            return None
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None
    finally:
        cursor.close()

def rata_rata_amount_per_lokasi(df):
   # df['amount'] = pd.to_numeric(df['amount'].fillna(0).astype(str), errors='coerce')

   # Menghapus koma, spasi, dan huruf "Rp", lalu mengonversi ke float, lalu ke integer
    df['amount'] = df['amount'].apply(lambda x: str(x).replace(',', '').replace(' ', '').replace('Rp', '').strip()).astype(float).astype(int)

    rata_rata_per_lokasi = df.groupby('spbu_name')['amount'].mean().reset_index()
    return rata_rata_per_lokasi

def jumlah_pemasukan_per_spbu(df):
    #df['amount'] = pd.to_numeric(df['amount'].fillna(0).astype(str), errors='coerce')


    # Menghapus koma, spasi, dan huruf "Rp", lalu mengonversi ke float, lalu ke integer
    df['amount'] = df['amount'].apply(lambda x: str(x).replace(',', '').replace(' ', '').replace('Rp', '').strip()).astype(float).astype(int).astype(str)
    return df.groupby('location')['amount'].sum().reset_index()

def page_visualisasi(nip, connection):
    page = st.sidebar.selectbox("Pilih Opsi", ["Visualisasi Semua Data", "Visualisasi Hari Ini", "Visualisasi Bulan Ini"])
            
            # Dictionary yang memetakan nama halaman ke fungsi yang sesuai
    pages = {
                "Visualisasi Semua Data": all_visualization,
                "Visualisasi Hari Ini": daily_visualization,
                "Visualisasi Bulan Ini": monthly_visualization,
            }

    pages[page]()

def data_hari_ini():
    try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM file WHERE tanggal = %s"
            current_date = datetime.now().date()
            cursor.execute(query, (current_date,))
            search_results = cursor.fetchall()
            df = pd.DataFrame(search_results)
            
            if not df.empty:
                return df
            else:
                st.write(f"Data hari ini belum di Upload '{current_date}'")
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()

def get_all_data_from_database(connection):
    cursor = connection.cursor()
    query = "SELECT * FROM file"
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columns)
    return df

def get_monthly_data_from_database(connection):
    cursor = connection.cursor()
    current_month = datetime.now().strftime('%Y-%m')
    query = """
        SELECT *
        FROM file
        WHERE tanggal LIKE %s
    """
    cursor.execute(query, (f"%{current_month}%",))
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columns)
    return df

def all_visualization():
    try:
        st.title("Visualisasi Semua Data")
        connection = create_connection()
        df = get_all_data_from_database(connection)
        if df is not None:
            df1 = data_hari_ini()
            if df1 is not None and not df1.empty:
                 # Membuat dua kolom untuk grafik sejajar
                col1, col2 = st.columns(2)
                with col1:
                    mean = rata_rata_amount_per_lokasi(df)
                            
                    fig = px.pie(mean, values='amount', names='spbu_name', title='Persentase Pendapatan Rata - Rata SPBU tiap Provinsi', color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig)

                    #Grafik 2
                with col2:
                        # Membaca data dari file CSV
                    payment = df

                        # Mengelompokkan data berdasarkan metode pembayaran (payment_type)
                    payment_counts = payment['payment_type'].value_counts().reset_index()
                    payment_counts.columns = ['payment_type', 'count']

                        # Membuat diagram pie menggunakan Plotly
                    fig1 = px.pie(payment_counts, values='count', names='payment_type', title='Persentase Metode Pembayaran')
                    st.plotly_chart(fig1)
                    
                    #Grafik 3
                jumlah = df
                jumlah = jumlah_pemasukan_per_spbu(jumlah)

                fig2 = go.Figure(
                        data=[
                            go.Bar(x=jumlah['location'], y=jumlah['amount']),
                        ],
                        layout=dict(
                            title="Grafik Pendapatan Tiap SPBU",
                            bargap=0.2, 
                            barcornerradius=5,
                        )
                    )
                st.plotly_chart(fig2)

            else:
                st.write(f"Jadi grafik dibawah tidak termasuk data hari ini. Silahkan Upload data untuk memperbarui grafik.")
                # Membuat dua kolom untuk grafik sejajar
                col1, col2 = st.columns(2)
                with col1:
                    mean = rata_rata_amount_per_lokasi(df)
                            
                    fig = px.pie(mean, values='amount', names='spbu_name', title='Persentase Pendapatan Rata - Rata SPBU tiap Provinsi', color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig)

                    #Grafik 2
                with col2:
                        # Membaca data dari file CSV
                    payment = df

                        # Mengelompokkan data berdasarkan metode pembayaran (payment_type)
                    payment_counts = payment['payment_type'].value_counts().reset_index()
                    payment_counts.columns = ['payment_type', 'count']

                        # Membuat diagram pie menggunakan Plotly
                    fig1 = px.pie(payment_counts, values='count', names='payment_type', title='Persentase Metode Pembayaran')
                    st.plotly_chart(fig1)
                    
                    #Grafik 3
                jumlah = df
                jumlah = jumlah_pemasukan_per_spbu(jumlah)

                fig2 = go.Figure(
                        data=[
                            go.Bar(x=jumlah['location'], y=jumlah['amount']),
                        ],
                        layout=dict(
                            title="Grafik Pendapatan Tiap SPBU",
                            bargap=0.2, 
                            barcornerradius=5,
                        )
                    )
                st.plotly_chart(fig2)

    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
            connection.close()


def daily_visualization():
    st.title("Visualisasi Data")
    current_date = datetime.now().date()

    if current_date is not None:
        try:
            connection = create_connection()
            file_path = get_file_path_from_db(connection, current_date)

            if file_path:
                #st.write(f"File path ditemukan: {file_path}")

                df = load_and_process_file_from_path(file_path)

                if df is not None and not df.empty:
                    st.subheader(f"Data hari ini telah di upload '{current_date}':")
                    #st.dataframe(df)
                    

                    # Membuat dua kolom untuk grafik sejajar
                    col1, col2 = st.columns(2)
                    with col1:
                        mean = rata_rata_amount_per_lokasi(df)
                        
                        fig = px.pie(mean, values='amount', names='spbu_name', title='Persentase Pendapatan Rata - Rata SPBU tiap Provinsi', color_discrete_sequence=px.colors.sequential.RdBu)
                        st.plotly_chart(fig)

                #Grafik 2
                with col2:
                    # Membaca data dari file CSV
                    payment = load_and_process_file_from_path(file_path)

                    # Mengelompokkan data berdasarkan metode pembayaran (payment_type)
                    payment_counts = payment['payment_type'].value_counts().reset_index()
                    payment_counts.columns = ['payment_type', 'count']

                    # Membuat diagram pie menggunakan Plotly
                    fig1 = px.pie(payment_counts, values='count', names='payment_type', title='Persentase Metode Pembayaran')
                    st.plotly_chart(fig1)
                
                #Grafik 3
                jumlah = load_and_process_file_from_path(file_path)
                jumlah = jumlah_pemasukan_per_spbu(jumlah)

                fig2 = go.Figure(
                    data=[
                        go.Bar(x=jumlah['location'], y=jumlah['amount']),
                    ],
                    layout=dict(
                        title="Grafik Pendapatan Tiap SPBU",
                        bargap=0.2, 
                        barcornerradius=5,
                    )
                )
                st.plotly_chart(fig2)

            else:
                st.write(f"Tidak ada data yang di upload hari ini '{current_date}'. Silahkan Upload data terlebih dahulu.")
        except mysql.connector.Error as err:
            st.error(f"Error: {err}")
        finally:
            connection.close()


def monthly_visualization():
    try:
        st.title("Visualisasi Data Bulan Ini")
        connection = create_connection()
        df = get_monthly_data_from_database(connection)
        df = pd.DataFrame(df)
        if df is not None:
            df1 = data_hari_ini()
            if df1 is not None and not df1.empty:
                 # Membuat dua kolom untuk grafik sejajar
                col1, col2 = st.columns(2)
                with col1:
                    mean = rata_rata_amount_per_lokasi(df)
                            
                    fig = px.pie(mean, values='amount', names='spbu_name', title='Persentase Pendapatan Rata - Rata SPBU tiap Provinsi', color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig)

                    #Grafik 2
                with col2:
                        # Membaca data dari file CSV
                    payment = df

                        # Mengelompokkan data berdasarkan metode pembayaran (payment_type)
                    payment_counts = payment['payment_type'].value_counts().reset_index()
                    payment_counts.columns = ['payment_type', 'count']

                        # Membuat diagram pie menggunakan Plotly
                    fig1 = px.pie(payment_counts, values='count', names='payment_type', title='Persentase Metode Pembayaran')
                    st.plotly_chart(fig1)
                    
                    #Grafik 3
                jumlah = df
                jumlah = jumlah_pemasukan_per_spbu(jumlah)

                fig2 = go.Figure(
                        data=[
                            go.Bar(x=jumlah['location'], y=jumlah['amount']),
                        ],
                        layout=dict(
                            title="Grafik Pendapatan Tiap SPBU",
                            bargap=0.2, 
                            barcornerradius=5,
                        )
                    )
                st.plotly_chart(fig2)

            else:
                st.write(f"Jadi grafik dibawah tidak termasuk data hari ini. Silahkan Upload data untuk memperbarui grafik.")
                # Membuat dua kolom untuk grafik sejajar
                col1, col2 = st.columns(2)
                with col1:
                    mean = rata_rata_amount_per_lokasi(df)
                            
                    fig = px.pie(mean, values='amount', names='spbu_name', title='Persentase Pendapatan Rata - Rata SPBU tiap Provinsi', color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig)

                    #Grafik 2
                with col2:
                        # Membaca data dari file CSV
                    payment = df

                        # Mengelompokkan data berdasarkan metode pembayaran (payment_type)
                    payment_counts = payment['payment_type'].value_counts().reset_index()
                    payment_counts.columns = ['payment_type', 'count']

                        # Membuat diagram pie menggunakan Plotly
                    fig1 = px.pie(payment_counts, values='count', names='payment_type', title='Persentase Metode Pembayaran')
                    st.plotly_chart(fig1)
                    
                    #Grafik 3
                jumlah = df
                jumlah = jumlah_pemasukan_per_spbu(jumlah)

                fig2 = go.Figure(
                        data=[
                            go.Bar(x=jumlah['location'], y=jumlah['amount']),
                        ],
                        layout=dict(
                            title="Grafik Pendapatan Tiap SPBU",
                            bargap=0.2, 
                            barcornerradius=5,
                        )
                    )
                st.plotly_chart(fig2)

    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
    finally:
            connection.close()

# Koneksi ke database MySQL
connection = create_connection()

# Memeriksa apakah pengguna sudah login dan menampilkan dashboard jika iya
if "logged_in" in st.session_state:
    nip = st.session_state.get("nip")
    main(nip, connection)
else:
    login_page()
    