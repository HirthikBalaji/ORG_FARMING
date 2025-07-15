# server.py - Flask API Server for Smart Agriculture System

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sqlite3
import datetime
import json
import threading
import time
import random
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
def init_db():
    conn = sqlite3.connect('agriculture.db')
    cursor = conn.cursor()
    
    # Sensor data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            probe_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,
            ph REAL,
            humidity REAL,
            temperature REAL,
            soil_moisture REAL,
            fertility_index REAL
        )
    ''')
    
    # Commands table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id TEXT UNIQUE NOT NULL,
            command_type TEXT NOT NULL,
            zone TEXT NOT NULL,
            parameters TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME NOT NULL,
            executed_at DATETIME,
            result TEXT
        )
    ''')
    
    # Rovers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rovers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rover_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'idle',
            current_zone TEXT,
            battery_level REAL DEFAULT 100,
            last_seen DATETIME
        )
    ''')
    
    conn.commit()
    conn.close()

@dataclass
class SensorReading:
    probe_id: str
    timestamp: datetime.datetime
    nitrogen: float
    phosphorus: float
    potassium: float
    ph: float
    humidity: float
    temperature: float
    soil_moisture: float
    fertility_index: float

@dataclass
class Command:
    command_id: str
    command_type: str
    zone: str
    parameters: dict
    status: str
    timestamp: datetime.datetime
    executed_at: Optional[datetime.datetime] = None
    result: Optional[str] = None

class DatabaseManager:
    def __init__(self):
        self.db_lock = threading.Lock()
    
    def get_connection(self):
        return sqlite3.connect('agriculture.db')
    
    def insert_sensor_data(self, reading: SensorReading):
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sensor_data 
                (probe_id, timestamp, nitrogen, phosphorus, potassium, ph, 
                 humidity, temperature, soil_moisture, fertility_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reading.probe_id, reading.timestamp, reading.nitrogen,
                reading.phosphorus, reading.potassium, reading.ph,
                reading.humidity, reading.temperature, reading.soil_moisture,
                reading.fertility_index
            ))
            conn.commit()
            conn.close()
    
    def get_latest_sensor_data(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sensor_data 
            WHERE timestamp IN (
                SELECT MAX(timestamp) FROM sensor_data GROUP BY probe_id
            )
            ORDER BY probe_id
        ''')
        data = cursor.fetchall()
        conn.close()
        return data
    
    def get_sensor_history(self, probe_id: str, hours: int = 24):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sensor_data 
            WHERE probe_id = ? AND timestamp > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(hours), (probe_id,))
        data = cursor.fetchall()
        conn.close()
        return data
    
    def insert_command(self, command: Command):
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO commands 
                (command_id, command_type, zone, parameters, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                command.command_id, command.command_type, command.zone,
                json.dumps(command.parameters), command.status, command.timestamp
            ))
            conn.commit()
            conn.close()
    
    def get_pending_commands(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM commands WHERE status = 'pending' ORDER BY timestamp
        ''')
        data = cursor.fetchall()
        conn.close()
        return data
    
    def update_command_status(self, command_id: str, status: str, result: str = None):
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE commands 
                SET status = ?, executed_at = ?, result = ?
                WHERE command_id = ?
            ''', (status, datetime.datetime.now(), result, command_id))
            conn.commit()
            conn.close()

# Initialize database and manager
init_db()
db_manager = DatabaseManager()

# Sensor simulator
class SensorSimulator:
    def __init__(self):
        self.probes = ['Probe_1', 'Probe_2', 'Probe_3', 'Probe_4']
        self.base_values = {
            'Probe_1': {'nitrogen': 45, 'phosphorus': 30, 'potassium': 35, 'ph': 6.5, 'humidity': 65, 'temperature': 24},
            'Probe_2': {'nitrogen': 40, 'phosphorus': 25, 'potassium': 30, 'ph': 6.8, 'humidity': 70, 'temperature': 23},
            'Probe_3': {'nitrogen': 50, 'phosphorus': 35, 'potassium': 40, 'ph': 6.3, 'humidity': 60, 'temperature': 25},
            'Probe_4': {'nitrogen': 35, 'phosphorus': 20, 'potassium': 25, 'ph': 7.0, 'humidity': 75, 'temperature': 22}
        }
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._simulate_sensors)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _simulate_sensors(self):
        while self.running:
            for probe_id in self.probes:
                base_vals = self.base_values[probe_id]
                
                reading = SensorReading(
                    probe_id=probe_id,
                    timestamp=datetime.datetime.now(),
                    nitrogen=max(0, base_vals['nitrogen'] + random.uniform(-5, 5)),
                    phosphorus=max(0, base_vals['phosphorus'] + random.uniform(-3, 3)),
                    potassium=max(0, base_vals['potassium'] + random.uniform(-4, 4)),
                    ph=max(4, min(9, base_vals['ph'] + random.uniform(-0.3, 0.3))),
                    humidity=max(0, min(100, base_vals['humidity'] + random.uniform(-5, 5))),
                    temperature=base_vals['temperature'] + random.uniform(-2, 2),
                    soil_moisture=random.uniform(30, 80),
                    fertility_index=random.uniform(60, 95)
                )
                
                # Store in database
                db_manager.insert_sensor_data(reading)
                
                # Emit to connected clients
                socketio.emit('sensor_data', asdict(reading))
            
            time.sleep(10)  # Update every 10 seconds

# Rover simulator
class RoverSimulator:
    def __init__(self):
        self.rovers = {
            'rover_1': {'name': 'Irrigation Rover', 'status': 'idle', 'battery': 100},
            'rover_2': {'name': 'Fertilizer Rover', 'status': 'idle', 'battery': 95}
        }
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._process_commands)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _process_commands(self):
        while self.running:
            commands = db_manager.get_pending_commands()
            
            for cmd_data in commands:
                command_id = cmd_data[1]
                command_type = cmd_data[2]
                zone = cmd_data[3]
                parameters = json.loads(cmd_data[4])
                
                # Simulate command execution
                print(f"Executing command: {command_type} in {zone}")
                
                # Simulate execution time
                execution_time = random.uniform(5, 15)
                time.sleep(execution_time)
                
                # Update command status
                result = f"Successfully executed {command_type} in {zone}"
                db_manager.update_command_status(command_id, 'completed', result)
                
                # Emit completion event
                socketio.emit('command_completed', {
                    'command_id': command_id,
                    'result': result,
                    'timestamp': datetime.datetime.now().isoformat()
                })
            
            time.sleep(5)  # Check for new commands every 5 seconds

# Initialize simulators
sensor_simulator = SensorSimulator()
rover_simulator = RoverSimulator()

# API Routes

@app.route('/api/sensors/latest', methods=['GET'])
def get_latest_sensor_data():
    """Get latest sensor readings from all probes"""
    try:
        data = db_manager.get_latest_sensor_data()
        sensors = []
        for row in data:
            sensors.append({
                'id': row[0],
                'probe_id': row[1],
                'timestamp': row[2],
                'nitrogen': row[3],
                'phosphorus': row[4],
                'potassium': row[5],
                'ph': row[6],
                'humidity': row[7],
                'temperature': row[8],
                'soil_moisture': row[9],
                'fertility_index': row[10]
            })
        return jsonify({'success': True, 'data': sensors})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sensors/<probe_id>/history', methods=['GET'])
def get_sensor_history(probe_id):
    """Get historical sensor data for a specific probe"""
    try:
        hours = request.args.get('hours', 24, type=int)
        data = db_manager.get_sensor_history(probe_id, hours)
        
        history = []
        for row in data:
            history.append({
                'id': row[0],
                'probe_id': row[1],
                'timestamp': row[2],
                'nitrogen': row[3],
                'phosphorus': row[4],
                'potassium': row[5],
                'ph': row[6],
                'humidity': row[7],
                'temperature': row[8],
                'soil_moisture': row[9],
                'fertility_index': row[10]
            })
        
        return jsonify({'success': True, 'data': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/commands', methods=['POST'])
def send_command():
    """Send command to rover"""
    try:
        data = request.get_json()
        
        command = Command(
            command_id=str(uuid.uuid4()),
            command_type=data['command_type'],
            zone=data['zone'],
            parameters=data.get('parameters', {}),
            status='pending',
            timestamp=datetime.datetime.now()
        )
        
        db_manager.insert_command(command)
        
        # Emit command to connected rovers
        socketio.emit('new_command', asdict(command))
        
        return jsonify({
            'success': True,
            'command_id': command.command_id,
            'message': 'Command sent successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/commands/history', methods=['GET'])
def get_command_history():
    """Get command history"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM commands 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        data = cursor.fetchall()
        conn.close()
        
        commands = []
        for row in data:
            commands.append({
                'id': row[0],
                'command_id': row[1],
                'command_type': row[2],
                'zone': row[3],
                'parameters': json.loads(row[4]) if row[4] else {},
                'status': row[5],
                'timestamp': row[6],
                'executed_at': row[7],
                'result': row[8]
            })
        
        return jsonify({'success': True, 'data': commands})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    try:
        # Get latest sensor data
        sensor_data = db_manager.get_latest_sensor_data()
        
        # Get pending commands count
        pending_commands = db_manager.get_pending_commands()
        
        status = {
            'sensors': {
                'total_probes': len(sensor_data),
                'active_probes': len(sensor_data),
                'last_update': datetime.datetime.now().isoformat()
            },
            'commands': {
                'pending': len(pending_commands),
                'total_rovers': 2,
                'active_rovers': 2
            },
            'system': {
                'status': 'operational',
                'uptime': '24h 15m',
                'version': '1.0.0'
            }
        }
        
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket Events

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'message': 'Connected to Smart Agriculture Server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_latest_data')
def handle_request_data():
    """Send latest sensor data to client"""
    data = db_manager.get_latest_sensor_data()
    emit('latest_sensor_data', data)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'services': {
            'database': 'operational',
            'sensors': 'operational',
            'rovers': 'operational'
        }
    })

if __name__ == '__main__':
    try:
        print("Starting Smart Agriculture Server...")
        print("Initializing sensors...")
        sensor_simulator.start()
        
        print("Initializing rovers...")
        rover_simulator.start()
        
        print("Server running on http://localhost:5000")
        print("WebSocket available on ws://localhost:5000")
        
        # Run the Flask app with SocketIO
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sensor_simulator.stop()
        rover_simulator.stop()
        print("Server stopped.")
