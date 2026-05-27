import streamlit as st
from dotenv import load_dotenv
import auth

# Load .env
load_dotenv()

# Redirect already logged-in users to main page
if st.session_state.get("user_authenticated"):
    st.switch_page("main.py")

st.set_page_config(page_title="Giriş / Kayıt", page_icon="🔒", layout="centered",initial_sidebar_state="collapsed")

# Sidebar'ı gizle
st.markdown("""
    <style>
        /* Navigasyon listesini gizle */
        [data-testid="stSidebarNav"] {display: none;}
        /* Sidebar'ın kendisini tamamen etkisizleştir */
        [data-testid="stSidebar"] {display: none;}
        /* Sol üstteki sidebar açma butonunu gizle */
        [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("🔒 Giriş / Kayıt")

# Initialize auth DB
auth.init_auth()

tabs = st.tabs(["Giriş", "Kayıt Ol"])

with tabs[0]:
    st.subheader("Hesabınıza giriş yapın")
    email = st.text_input("E-posta")
    password = st.text_input("Parola", type="password")

    if st.button("Giriş Yap"):
        if not email or not password:
            st.error("E-posta ve parola gereklidir.")
        else:
            user = auth.verify_user(email.strip().lower(), password)
            if user:
                st.session_state["user_authenticated"] = True
                st.session_state["user_email"] = user["email"]
                st.session_state["user_company"] = user["company_name"]
                st.success(f"Hoş geldiniz, {user['company_name']}!")
                st.switch_page("main.py")
            else:
                st.error("Geçersiz e-posta veya parola.")

with tabs[1]:
    st.subheader("Yeni hesap oluştur")
    r_email = st.text_input("E-posta", key="reg_email")
    r_password = st.text_input("Parola", type="password", key="reg_password")
    company = st.text_input("Şirket Adı", key="reg_company")

    if st.button("Kayıt Ol"):
        if not r_email or not r_password or not company:
            st.error("Tüm alanlar gereklidir.")
        else:
            created = auth.create_user(r_email.strip().lower(), r_password, company.strip())
            if created:
                st.success("Kayıt başarılı — giriş yapıldı.")
                st.session_state["user_authenticated"] = True
                st.session_state["user_email"] = created["email"]
                st.session_state["user_company"] = created["company_name"]
                st.switch_page("main.py")
            else:
                st.error("Bu e-posta zaten kayıtlı.")

# Offer logout if already logged in
if st.session_state.get("user_authenticated"):
    st.divider()
    st.write(f"Giriş Yapıldı: {st.session_state.get('user_email')} ({st.session_state.get('user_company')})")
    if st.button("Çıkış Yap"):
        auth.logout()
