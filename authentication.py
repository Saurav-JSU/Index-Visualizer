"""
authentication.py
Handles Earth Engine authentication for the Climate Analysis Tool
"""

import os
import json
import time
import ee
from ipywidgets import widgets, VBox, HBox, Layout
from IPython.display import display, clear_output

class AuthenticationManager:
    """Manages Earth Engine authentication for climate analysis tool"""
    
    def __init__(self):
        """Initialize authentication manager"""
        self.project_id = None
        self.auth_status = "Not authenticated"
        self.credentials_path = os.path.expanduser("~/.climate_tool/credentials.json")
        self._ensure_credentials_dir()
    
    def _ensure_credentials_dir(self):
        """Ensure the credentials directory exists"""
        os.makedirs(os.path.dirname(self.credentials_path), exist_ok=True)
    
    def load_credentials(self):
        """Load stored credentials if available"""
        try:
            if os.path.exists(self.credentials_path):
                with open(self.credentials_path, 'r') as f:
                    credentials = json.load(f)
                    self.project_id = credentials.get('project_id')
                    return True
            return False
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
            return False
    
    def save_credentials(self):
        """Save credentials for future use"""
        try:
            credentials = {
                'project_id': self.project_id,
                'timestamp': time.time()
            }
            with open(self.credentials_path, 'w') as f:
                json.dump(credentials, f)
            return True
        except Exception as e:
            print(f"Error saving credentials: {str(e)}")
            return False
    
    def initialize_ee(self, project_id=None):
        """Initialize Earth Engine with project ID"""
        if project_id:
            self.project_id = project_id
            
        try:
            if self.project_id:
                ee.Initialize(project=self.project_id)
            else:
                ee.Initialize()
            self.auth_status = "Authenticated"
            self.save_credentials()
            return True
        except Exception as e:
            self.auth_status = f"Authentication failed: {str(e)}"
            return False
    
    def authenticate_ee(self):
        """Perform Earth Engine authentication"""
        try:
            ee.Authenticate()
            return True
        except Exception as e:
            self.auth_status = f"Authentication failed: {str(e)}"
            return False
    
    def create_auth_widgets(self):
        """Create authentication widgets for the UI"""
        title = widgets.HTML(
            value="<h2>Earth Engine Authentication</h2>" +
                  "<p>Authenticate and provide your Earth Engine project ID to begin.</p>"
        )
        
        # Project ID input
        project_id_input = widgets.Text(
            value=self.project_id if self.project_id else "",
            placeholder="Enter Earth Engine project ID",
            description="Project ID:",
            layout=Layout(width='500px')
        )
        
        # Auth button
        auth_button = widgets.Button(
            description="Authenticate Earth Engine",
            button_style="primary",
            layout=Layout(width='250px')
        )
        
        # Status display
        status_display = widgets.HTML(
            value=f"<p>Status: {self.auth_status}</p>"
        )
        
        # Start tool button (initially disabled)
        start_button = widgets.Button(
            description="Start Climate Tool",
            button_style="success",
            disabled=True,
            layout=Layout(width='250px')
        )
        
        # Handle authentication button click
        def on_auth_click(b):
            clear_output(wait=True)
            
            status_display.value = "<p>Authenticating with Earth Engine...</p>"
            display(VBox([title, project_id_input, auth_button, status_display]))
            
            success = self.authenticate_ee()
            
            if success:
                status_display.value = "<p>Authentication successful! Now initializing with project ID...</p>"
                time.sleep(1)  # Brief pause to show the message
                
                project_id = project_id_input.value.strip()
                if project_id:
                    init_success = self.initialize_ee(project_id)
                    if init_success:
                        status_display.value = "<p style='color: green'>✓ Authentication complete! You can now start the tool.</p>"
                        start_button.disabled = False
                    else:
                        status_display.value = f"<p style='color: red'>✗ {self.auth_status}</p>"
                else:
                    status_display.value = "<p style='color: orange'>⚠ No project ID provided. You can continue but some features may be limited.</p>"
                    init_success = self.initialize_ee()
                    if init_success:
                        start_button.disabled = False
            else:
                status_display.value = f"<p style='color: red'>✗ {self.auth_status}</p>"
            
            # Redisplay all widgets
            display(VBox([title, project_id_input, auth_button, status_display, start_button]))
        
        auth_button.on_click(on_auth_click)
        
        # Check if already authenticated
        try:
            ee.Initialize(project=self.project_id)
            self.auth_status = "Authenticated"
            status_display.value = "<p style='color: green'>✓ Already authenticated</p>"
            start_button.disabled = False
        except:
            pass
        
        return VBox([title, project_id_input, auth_button, status_display, start_button]), start_button
    
    def is_authenticated(self):
        """Check if Earth Engine is authenticated"""
        try:
            # Try a simple EE operation to check authentication
            ee.Number(1).getInfo()
            return True
        except:
            return False