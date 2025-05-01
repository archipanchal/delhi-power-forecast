import streamlit as st
import smtplib
import random
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
from datetime import datetime, timedelta
import json
import hashlib
import logging

# Configure logging
logging.basicConfig(
    filename='auth.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AuthSystem:
    def __init__(self):
        self.users_file = 'users.json'
        self.load_users()
        
        # Email configuration
        self.email_sender = "your-email@gmail.com"  # Replace with your email
        self.email_password = st.secrets["EMAIL_PASSWORD"]
        
        # Twilio configuration for SMS
        self.twilio_sid = st.secrets["TWILIO_SID"]
        self.twilio_token = st.secrets["TWILIO_TOKEN"]
        self.twilio_phone = st.secrets["TWILIO_PHONE"]
        
        self.verification_codes = {}
    
    def load_users(self):
        """Load users from JSON file"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}
            self.save_users()
    
    def save_users(self):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_verification_code(self):
        """Generate 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    def send_email_verification(self, email):
        """Send verification code via email"""
        try:
            code = self.generate_verification_code()
            self.verification_codes[email] = {
                'code': code,
                'expires': datetime.now() + timedelta(minutes=10)
            }
            
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = email
            msg['Subject'] = "Verification Code for Power Demand Analysis App"
            
            body = f"Your verification code is: {code}\nThis code will expire in 10 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Verification email sent to {email}")
            return True
        except Exception as e:
            logging.error(f"Failed to send email verification: {str(e)}")
            return False
    
    def send_sms_verification(self, phone):
        """Send verification code via SMS"""
        try:
            code = self.generate_verification_code()
            self.verification_codes[phone] = {
                'code': code,
                'expires': datetime.now() + timedelta(minutes=10)
            }
            
            client = Client(self.twilio_sid, self.twilio_token)
            message = client.messages.create(
                body=f"Your verification code for Power Demand Analysis App is: {code}",
                from_=self.twilio_phone,
                to=phone
            )
            
            logging.info(f"Verification SMS sent to {phone}")
            return True
        except Exception as e:
            logging.error(f"Failed to send SMS verification: {str(e)}")
            return False
    
    def verify_code(self, contact, code):
        """Verify the provided code"""
        if contact in self.verification_codes:
            stored_code = self.verification_codes[contact]
            if (datetime.now() <= stored_code['expires'] and 
                stored_code['code'] == code):
                del self.verification_codes[contact]
                return True
        return False
    
    def register_user(self, email, phone, password):
        """Register a new user"""
        try:
            if email in self.users:
                return False, "Email already registered"
            
            user_data = {
                'email': email,
                'phone': phone,
                'password': self.hash_password(password),
                'created_at': datetime.now().isoformat()
            }
            
            self.users[email] = user_data
            self.save_users()
            logging.info(f"New user registered: {email}")
            return True, "Registration successful"
        except Exception as e:
            logging.error(f"Registration failed: {str(e)}")
            return False, "Registration failed"
    
    def login_user(self, email, password):
        """Login user"""
        try:
            if email in self.users:
                user = self.users[email]
                if user['password'] == self.hash_password(password):
                    logging.info(f"User logged in: {email}")
                    return True, "Login successful"
            return False, "Invalid credentials"
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False, "Login failed"

def render_auth_ui():
    """Render authentication UI in Streamlit"""
    st.title("Power Demand Analysis - Authentication")
    
    auth = AuthSystem()
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.header("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            success, message = auth.login_user(login_email, login_password)
            if success:
                st.success(message)
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = login_email
            else:
                st.error(message)
    
    with tab2:
        st.header("Register")
        reg_email = st.text_input("Email", key="reg_email")
        reg_phone = st.text_input("Phone Number", key="reg_phone")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Send Email Verification"):
                if auth.send_email_verification(reg_email):
                    st.success("Verification code sent to email")
                else:
                    st.error("Failed to send email verification")
        
        with col2:
            if st.button("Send SMS Verification"):
                if auth.send_sms_verification(reg_phone):
                    st.success("Verification code sent to phone")
                else:
                    st.error("Failed to send SMS verification")
        
        email_code = st.text_input("Email Verification Code")
        phone_code = st.text_input("SMS Verification Code")
        
        if st.button("Register"):
            if auth.verify_code(reg_email, email_code) and auth.verify_code(reg_phone, phone_code):
                success, message = auth.register_user(reg_email, reg_phone, reg_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Invalid verification codes")

if __name__ == "__main__":
    render_auth_ui() 