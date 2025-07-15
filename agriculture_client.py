# client_dashboard.py - Streamlit Client Dashboard

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import json
import socketio
import time
import threading
from typing import Dict, List, Optional

# Page configuration
st.set_page_config(
    page_title="Smart Agriculture Client Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
SERVER_URL = "http://localhost:5000"
SOCKET_URL = "http://localhost:5000"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 2rem;
    }
    .probe-card {
        background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-online {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-offline {
        color: #F44336;
        font-weight: bold;
    }
    .alert-critical {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-warning {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-good {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = []
if 'command_history' not in st.session_state:
    st.session_state.command_history = []
if 'server_status' not in st.session_state:
    st.session_state.server_status = 'disconnected'
if 'socket_client' not in st.session_state:
    st.session_state.socket_client = None

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = 10
    
    def get_latest_sensor_data(self) -> Optional[Dict]:
        """Fetch latest sensor data from server"""
        try:
            response = requests.get(f"{self.base_url}/api/sensors/latest", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error fetching sensor data: {str(e)}")
            return None
    
    def get_sensor_history(self, probe_id: str, hours: int = 24) -> Optional[Dict]:
        """Fetch sensor history for a specific probe"""
        try:
            response = requests.get(
                f"{self.base_url}/api/sensors/{probe_id}/history",
                params={'hours': hours},
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error fetching sensor history: {str(e)}")
            return None
    
    def send_command(self, command_type: str, zone: str, parameters: Dict) -> Optional[Dict]:
        """Send command to server"""
        try:
            payload = {
                'command_type': command_type,
                'zone': zone,
                'parameters': parameters
            }
            response = requests.post(
                f"{self.base_url}/api/commands",
                json=payload,
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error sending command: {str(e)}")
            return None
    
    def get_command_history(self) -> Optional[Dict]:
        """Fetch command history"""
        try:
            response = requests.get(f"{self.base_url}/api/commands/history", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error fetching command history: {str(e)}")
            return None
    
    def get_system_status(self) -> Optional[Dict]:
        """Get system status"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            return None
    
    def health_check(self) -> bool:
        """Check if server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# Initialize API client
api_client = APIClient(SERVER_URL)

def get_status_indicator(value: float, param_type: str) -> str:
    """Get status indicator for a parameter"""
    thresholds = {
        'nitrogen': {'good': (40, 60), 'warning': (30, 70)},
        'phosphorus': {'good': (20, 40), 'warning': (15, 50)},
        'potassium': {'good': (30, 50), 'warning': (20, 60)},
        'ph': {'good': (6.0, 7.5), 'warning': (5.5, 8.0)},
        'humidity': {'good': (60, 80), 'warning': (50, 90)},
        'temperature': {'good': (20, 30), 'warning': (15, 35)},
        'soil_moisture': {'good': (40, 70), 'warning': (30, 80)},
        'fertility_index': {'good': (70, 100), 'warning': (50, 70)}
    }
    
    if param_type in thresholds:
        good_range = thresholds[param_type]['good']
        warning_range = thresholds[param_type]['warning']
        
        if good_range[0] <= value <= good_range[1]:
            return 'good'
        elif warning_range[0] <= value <= warning_range[1]:
            return 'warning'
        else:
            return 'critical'
    return 'unknown'

def main():
    st.markdown('<h1 class="main-header">🌱 Smart Agriculture Client Dashboard</h1>', unsafe_allow_html=True)
    
    # Server connection status
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if api_client.health_check():
            st.markdown('<p class="status-online">🟢 Server Online</p>', unsafe_allow_html=True)
            st.session_state.server_status = 'connected'
        else:
            st.markdown('<p class="status-offline">🔴 Server Offline</p>', unsafe_allow_html=True)
            st.session_state.server_status = 'disconnected'
    
    with col2:
        auto_refresh = st.checkbox("Auto Refresh", value=True)
    
    with col3:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    # Only proceed if server is connected
    if st.session_state.server_status == 'disconnected':
        st.error("Cannot connect to server. Please check if the server is running on http://localhost:5000")
        st.info("Run the server with: python server.py")
        return
    
    # Fetch latest sensor data
    sensor_response = api_client.get_latest_sensor_data()
    if sensor_response and sensor_response.get('success'):
        sensor_data = sensor_response['data']
        
        # Display probe overview
        st.markdown("## 📊 Probe Overview")
        cols = st.columns(4)
        
        for i, probe_data in enumerate(sensor_data):
            with cols[i]:
                st.markdown(f'<div class="probe-card">', unsafe_allow_html=True)
                st.markdown(f"### {probe_data['probe_id']}")
                
                # Key metrics
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Nitrogen", f"{probe_data['nitrogen']:.1f}%")
                    st.metric("Phosphorus", f"{probe_data['phosphorus']:.1f}%")
                with col_b:
                    st.metric("Potassium", f"{probe_data['potassium']:.1f}%")
                    st.metric("pH", f"{probe_data['ph']:.1f}")
                
                # Status indicators
                fertility_status = get_status_indicator(probe_data['fertility_index'], 'fertility_index')
                if fertility_status == 'good':
                    st.success(f"✅ Fertility: {probe_data['fertility_index']:.1f}%")
                elif fertility_status == 'warning':
                    st.warning(f"⚠️ Fertility: {probe_data['fertility_index']:.1f}%")
                else:
                    st.error(f"❌ Fertility: {probe_data['fertility_index']:.1f}%")
                
                # Additional metrics
                st.info(f"🌡️ Temp: {probe_data['temperature']:.1f}°C")
                st.info(f"💧 Moisture: {probe_data['soil_moisture']:.1f}%")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Historical data charts
        st.markdown("## 📈 Historical Data")
        
        # Fetch historical data for charts
        probe_histories = {}
        for probe_data in sensor_data:
            probe_id = probe_data['probe_id']
            history_response = api_client.get_sensor_history(probe_id, hours=6)
            if history_response and history_response.get('success'):
                probe_histories[probe_id] = history_response['data']
        
        if probe_histories:
            # Create comprehensive charts
            fig_nutrients = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Nitrogen Levels (%)', 'Phosphorus Levels (%)', 'Potassium Levels (%)', 'pH Levels'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
            
            for i, (probe_id, history) in enumerate(probe_histories.items()):
                if history:
                    df = pd.DataFrame(history)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    fig_nutrients.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['nitrogen'], 
                                  name=f'{probe_id} N', line=dict(color=colors[i])),
                        row=1, col=1
                    )
                    fig_nutrients.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['phosphorus'], 
                                  name=f'{probe_id} P', line=dict(color=colors[i])),
                        row=1, col=2
                    )
                    fig_nutrients.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['potassium'], 
                                  name=f'{probe_id} K', line=dict(color=colors[i])),
                        row=2, col=1
                    )
                    fig_nutrients.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['ph'], 
                                  name=f'{probe_id} pH', line=dict(color=colors[i])),
                        row=2, col=2
                    )
            
            fig_nutrients.update_layout(height=600, title_text="Nutrient and pH Monitoring (Last 6 Hours)")
            st.plotly_chart(fig_nutrients, use_container_width=True)
            
            # Environmental conditions
            fig_env = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Humidity (%)', 'Temperature (°C)', 'Soil Moisture (%)')
            )
            
            for i, (probe_id, history) in enumerate(probe_histories.items()):
                if history:
                    df = pd.DataFrame(history)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    fig_env.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['humidity'], 
                                  name=f'{probe_id} Humidity', line=dict(color=colors[i])),
                        row=1, col=1
                    )
                    fig_env.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['temperature'], 
                                  name=f'{probe_id} Temp', line=dict(color=colors[i])),
                        row=1, col=2
                    )
                    fig_env.add_trace(
                        go.Scatter(x=df['timestamp'], y=df['soil_moisture'], 
                                  name=f'{probe_id} Moisture', line=dict(color=colors[i])),
                        row=1, col=3
                    )
            
            fig_env.update_layout(height=400, title_text="Environmental Conditions (Last 6 Hours)")
            st.plotly_chart(fig_env, use_container_width=True)
        
        # Generate alerts based on current data
        st.markdown("## 🚨 Alerts & Recommendations")
        
        alerts = []
        for probe_data in sensor_data:
            probe_id = probe_data['probe_id']
            
            # Check various parameters
            if probe_data['nitrogen'] < 35:
                alerts.append(('critical', f"{probe_id}: Low nitrogen levels ({probe_data['nitrogen']:.1f}%) - Apply nitrogen fertilizer"))
            elif probe_data['nitrogen'] > 65:
                alerts.append(('warning', f"{probe_id}: High nitrogen levels ({probe_data['nitrogen']:.1f}%) - Reduce fertilizer"))
            
            if probe_data['soil_moisture'] < 35:
                alerts.append(('critical', f"{probe_id}: Low soil moisture ({probe_data['soil_moisture']:.1f}%) - Irrigation needed"))
            elif probe_data['soil_moisture'] > 75:
                alerts.append(('warning', f"{probe_id}: High soil moisture ({probe_data['soil_moisture']:.1f}%) - Check drainage"))
            
            if probe_data['ph'] < 6.0 or probe_data['ph'] > 7.5:
                alerts.append(('warning', f"{probe_id}: pH out of optimal range ({probe_data['ph']:.1f}) - Adjust soil pH"))
            
            if probe_data['fertility_index'] < 60:
                alerts.append(('critical', f"{probe_id}: Low fertility index ({probe_data['fertility_index']:.1f}%) - Comprehensive soil treatment needed"))
        
        if alerts:
            for alert_type, message in alerts:
                if alert_type == 'critical':
                    st.markdown(f'<div class="alert-critical">🔴 <strong>CRITICAL:</strong> {message}</div>', unsafe_allow_html=True)
                elif alert_type == 'warning':
                    st.markdown(f'<div class="alert-warning">🟡 <strong>WARNING:</strong> {message}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-good">✅ <strong>ALL SYSTEMS NORMAL:</strong> No alerts detected</div>', unsafe_allow_html=True)
        
        # Rover Command Center
        st.markdown("## 🤖 Rover Command Center")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🚰 Irrigation Control")
            with st.container():
                irrigation_zone = st.selectbox(
                    "Select Zone", 
                    ["Probe_1_Area", "Probe_2_Area", "Probe_3_Area", "Probe_4_Area"], 
                    key="irrigation_zone"
                )
                irrigation_duration = st.slider("Duration (minutes)", 5, 60, 15, key="irrigation_duration")
                irrigation_intensity = st.selectbox("Intensity", ["Low", "Medium", "High"], key="irrigation_intensity")
                
                if st.button("🚰 Start Irrigation", key="start_irrigation"):
                    parameters = {
                        'duration': irrigation_duration,
                        'intensity': irrigation_intensity
                    }
                    
                    response = api_client.send_command('irrigation', irrigation_zone, parameters)
                    if response and response.get('success'):
                        st.success(f"✅ Irrigation command sent to {irrigation_zone} for {irrigation_duration} minutes")
                        st.info(f"Command ID: {response['command_id']}")
                    else:
                        st.error("Failed to send irrigation command")
        
        with col2:
            st.markdown("### 🌱 Fertilizer Application")
            with st.container():
                fertilizer_zone = st.selectbox(
                    "Select Zone", 
                    ["Probe_1_Area", "Probe_2_Area", "Probe_3_Area", "Probe_4_Area"], 
                    key="fertilizer_zone"
                )
                fertilizer_type = st.selectbox(
                    "Fertilizer Type", 
                    ["Nitrogen", "Phosphorus", "Potassium", "NPK_Balanced"], 
                    key="fertilizer_type"
                )
                fertilizer_amount = st.slider("Amount (kg)", 1, 20, 5, key="fertilizer_amount")
                
                if st.button("🌱 Apply Fertilizer", key="apply_fertilizer"):
                    parameters = {
                        'type': fertilizer_type,
                        'amount': fertilizer_amount
                    }
                    
                    response = api_client.send_command('fertilizer', fertilizer_zone, parameters)
                    if response and response.get('success'):
                        st.success(f"✅ Fertilizer command sent: {fertilizer_amount}kg of {fertilizer_type} to {fertilizer_zone}")
                        st.info(f"Command ID: {response['command_id']}")
                    else:
                        st.error("Failed to send fertilizer command")
        
        # Quick Actions
        if alerts:
            st.markdown("### ⚡ Quick Actions")
            st.markdown("*One-click solutions for detected issues*")
            
            quick_actions_cols = st.columns(3)
            action_count = 0
            
            for alert_type, message in alerts[:6]:  # Show first 6 alerts
                with quick_actions_cols[action_count % 3]:
                    if 'nitrogen' in message.lower() and 'low' in message.lower():
                        zone = message.split(':')[0] + "_Area"
                        if st.button(f"Apply Nitrogen to {zone}", key=f"quick_nitrogen_{action_count}"):
                            response = api_client.send_command('fertilizer', zone, {'type': 'Nitrogen', 'amount': 10})
                            if response and response.get('success'):
                                st.success("🚀 Quick nitrogen application sent!")
                    
                    elif 'moisture' in message.lower() and 'low' in message.lower():
                        zone = message.split(':')[0] + "_Area"
                        if st.button(f"Irrigate {zone}", key=f"quick_irrigation_{action_count}"):
                            response = api_client.send_command('irrigation', zone, {'duration': 20, 'intensity': 'Medium'})
                            if response and response.get('success'):
                                st.success("🚀 Quick irrigation sent!")
                    
                    elif 'fertility' in message.lower() and 'low' in message.lower():
                        zone = message.split(':')[0] + "_Area"
                        if st.button(f"Apply NPK to {zone}", key=f"quick_npk_{action_count}"):
                            response = api_client.send_command('fertilizer', zone, {'type': 'NPK_Balanced', 'amount': 15})
                            if response and response.get('success'):
                                st.success("🚀 Quick NPK application sent!")
                
                action_count += 1
        
        # Command History
        st.markdown("## 📋 Command History")
        
        command_response = api_client.get_command_history()
        if command_response and command_response.get('success'):
            commands = command_response['data']
            
            if commands:
                # Create a DataFrame for better display
                df_commands = pd.DataFrame(commands)
                df_commands['timestamp'] = pd.to_datetime(df_commands['timestamp'])
                df_commands = df_commands.sort_values('timestamp', ascending=False)
                
                # Display with colored status
                for _, cmd in df_commands.head(10).iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 3])
                    
                    with col1:
                        st.text(cmd['timestamp'].strftime('%Y-%m-%d %H:%M:%S'))
                    with col2:
                        st.text(cmd['command_type'].title())
                    with col3:
                        st.text(cmd['zone'])
                    with col4:
                        if cmd['status'] == 'completed':
                            st.success(cmd['status'].title())
                        elif cmd['status'] == 'pending':
                            st.warning(cmd['status'].title())
                        else:
                            st.error(cmd['status'].title())
                    with col5:
                        if cmd['result']:
                            st.text(cmd['result'][:50] + "..." if len(cmd['result']) > 50 else cmd['result'])
                        else:
                            st.text("Processing...")
            else:
                st.info("No commands sent yet")
        
        # System Status
        st.markdown("## 🔧 System Status")
        
        status_response = api_client.get_system_status()
        if status_response and status_response.get('success'):
            system_status = status_response['data']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📡 Sensors")
                st.metric("Active Probes", system_status['sensors']['active_probes'])
                st.metric("Total Probes", system_status['sensors']['total_probes'])
            
            with col2:
                st.markdown("### 🤖 Rovers")
                st.metric("Active Rovers", system_status['commands']['active_rovers'])
                st.metric("Pending Commands", system_status['commands']['pending'])
            
            with col3:
                st.markdown("### 🖥️ System")
                st.metric("Status", system_status['system']['status'].title())
                st.metric("Version", system_status['system']['version'])
        
    else:
        st.error("Failed to fetch sensor data from server")
        st.info("Please check server connection and try again")
    
    # Auto-refresh functionality
    if auto_refresh and st.session_state.server_status == 'connected':
        time.sleep(10)
        st.rerun()

if __name__ == "__main__":
    main()