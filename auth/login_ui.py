"""
Kullanıcı Giriş (Login) Ekranı Bileşeni.
"""
import streamlit as st
from auth.auth_manager import AuthManager

def render_login_screen() -> bool:
    """
    Kullanıcıya şık ve modern bir giriş kartı sunar.
    Başarılı giriş durumunda True döner ve sayfayı yeniler.
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="margin-bottom: 5px;">🔒 Giriş Yapın</h2>
                    <p style="color: #888; font-size: 14px;">Nabulu İçerik Üretici Keşif & Analiz Asistanı</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input(
                    "Kurumsal E-posta Adresi",
                    placeholder="ornek@nabulu.com.tr",
                    key="login_email"
                )
                password = st.text_input(
                    "Şifre",
                    type="password",
                    placeholder="••••••••",
                    key="login_password"
                )
                
                submitted = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")
                
                if submitted:
                    if not email or not password:
                        st.error("Lütfen e-posta adresinizi ve şifrenizi girin.")
                    else:
                        success = AuthManager.login(email, password)
                        if success:
                            st.success(f"Giriş başarılı! Hoş geldiniz, {st.session_state['auth_user']['name']}.")
                            st.rerun()
                        else:
                            st.error("Hatalı e-posta adresi veya şifre. Lütfen bilgilerinizi kontrol edin.")
            
            st.markdown(
                """
                <div style="text-align: center; margin-top: 15px;">
                    <small style="color: #999;">Bu sistem yalnızca yetkili Nabulu ekibi üyelerine açıktır.</small>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    return False
