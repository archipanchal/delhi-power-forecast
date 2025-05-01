import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='sso.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SSOAuth:
    def __init__(self):
        # Google OAuth 2.0 settings
        self.google_client_id = st.secrets["GOOGLE_CLIENT_ID"]
        self.google_client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
        self.google_authorize_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.google_token_url = 'https://oauth2.googleapis.com/token'
        self.google_scope = ['openid', 'email', 'profile']
        
        # Microsoft OAuth 2.0 settings
        self.microsoft_client_id = st.secrets["MICROSOFT_CLIENT_ID"]
        self.microsoft_client_secret = st.secrets["MICROSOFT_CLIENT_SECRET"]
        self.microsoft_authorize_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.microsoft_token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.microsoft_scope = ['openid', 'email', 'profile']
        
        self.redirect_uri = 'http://localhost:8501/callback'
        self.users_file = 'sso_users.json'
        self.load_users()
    
    def load_users(self):
        """Load SSO users from JSON file"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}
            self.save_users()
    
    def save_users(self):
        """Save SSO users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def google_login(self):
        """Initiate Google OAuth login"""
        try:
            session = OAuth2Session(
                self.google_client_id,  
                self.google_client_secret,
                scope=self.google_scope,
                redirect_uri=self.redirect_uri
            )
            uri, state = session.create_authorization_url(self.google_authorize_url)
            st.session_state['oauth_state'] = state
            return uri
        except Exception as e:
            logging.error(f"Google login failed: {str(e)}")
            return None
    
    def microsoft_login(self):
        """Initiate Microsoft OAuth login"""
        try:
            session = OAuth2Session(
                self.microsoft_client_id,
                self.microsoft_client_secret,
                scope=self.microsoft_scope,
                redirect_uri=self.redirect_uri
            )
            uri, state = session.create_authorization_url(self.microsoft_authorize_url)
            st.session_state['oauth_state'] = state
            return uri
        except Exception as e:
            logging.error(f"Microsoft login failed: {str(e)}")
            return None
    
    def handle_callback(self, provider, code, state):
        """Handle OAuth callback"""
        try:
            if state != st.session_state.get('oauth_state'):
                return False, "Invalid state"
            
            if provider == 'google':
                token_url = self.google_token_url
                client_id = self.google_client_id
                client_secret = self.google_client_secret
            else:
                token_url = self.microsoft_token_url
                client_id = self.microsoft_client_id
                client_secret = self.microsoft_client_secret
            
            session = OAuth2Session(
                client_id,
                client_secret,
                state=state
            )
            
            token = session.fetch_token(
                token_url,
                code=code,
                client_secret=client_secret
            )
            
            user_info = session.get('userinfo_endpoint').json()
            
            # Store user info
            self.users[user_info['email']] = {
                'provider': provider,
                'name': user_info.get('name'),
                'email': user_info['email'],
                'last_login': datetime.now().isoformat()
            }
            self.save_users()
            
            logging.info(f"SSO login successful: {user_info['email']} via {provider}")
            return True, user_info
            
        except Exception as e:
            logging.error(f"Callback handling failed: {str(e)}")
            return False, str(e)

def render_sso_ui():
    """Render SSO UI in Streamlit"""
    st.title("Single Sign-On")
    
    sso = SSOAuth()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Sign in with Google"):
            auth_url = sso.google_login()
            if auth_url:
                st.markdown(f'[Click here to sign in with Google]({auth_url})')
            else:
                st.error("Failed to initialize Google login")
    
    with col2:
        if st.button("Sign in with Microsoft"):
            auth_url = sso.microsoft_login()
            if auth_url:
                st.markdown(f'[Click here to sign in with Microsoft]({auth_url})')
            else:
                st.error("Failed to initialize Microsoft login")
    
    # Handle callback
    query_params = st.experimental_get_query_params()
    if 'code' in query_params and 'state' in query_params:
        provider = query_params.get('provider', [''])[0]
        code = query_params['code'][0]
        state = query_params['state'][0]
        
        success, result = sso.handle_callback(provider, code, state)
        if success:
            st.success(f"Welcome {result['name']}!")
            st.session_state['authenticated'] = True
            st.session_state['user_email'] = result['email']
        else:
            st.error(f"Authentication failed: {result}")

if __name__ == "__main__":
    render_sso_ui() 