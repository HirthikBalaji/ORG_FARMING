# 🌾 Smart Agriculture Server – ORG_FARMING

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask-lightgreen)
![WebSocket](https://img.shields.io/badge/Real--Time-Socket.IO-purple)
![License](https://img.shields.io/badge/License-MIT-green)

A real-time Flask-based server that powers **ORG_FARMING**, a smart agriculture automation system. It manages soil sensors, rover commands, real-time WebSocket data streaming, and historical data tracking — all simulated and managed locally using SQLite.


---

## 🚀 Features

- 📡 Simulates 4 soil probes with live readings (NPK, pH, temperature, moisture, etc.)
- 🤖 Sends commands to simulated rovers (e.g., irrigation, fertilization)
- 📈 Historical data retrieval by probe
- 🔄 WebSocket for real-time sensor and command updates
- 🛡️ Thread-safe database transactions
- ✅ RESTful API with health checks

---

## 🗂️ Project Structure

```

ORG\_FARMING/
│
├── agriculture\_server.py      # Main server logic
├── agriculture.db             # SQLite database (auto-created)
├── README.md                  # You're reading this 🙂
└── requirements.txt           # Dependencies (you can create this)

````

---

## ⚙️ Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/HirthikBalaji/ORG_FARMING.git
cd ORG_FARMING
````

### 2. Set up environment

```bash
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```


### 3. Run the server

```bash
python agriculture_server.py
```

Open browser or test API on: [http://localhost:5000](http://localhost:5000)

---

## 📡 API Endpoints

### 🔍 Sensors

* `GET /api/sensors/latest`
  → Get latest sensor data from all probes

* `GET /api/sensors/<probe_id>/history?hours=12`
  → Retrieve history of a probe

### 📤 Commands

* `POST /api/commands`
  → Send a command to a rover
  Example:

  ```json
  {
    "command_type": "irrigate",
    "zone": "Zone A",
    "parameters": { "duration": 10 }
  }
  ```

* `GET /api/commands/history`
  → Get the latest 50 command logs

### 🔧 System

* `GET /api/status`
  → Check system status (probes, rovers, commands)

* `GET /health`
  → Lightweight health check

---

## ⚡ WebSocket Events

* `sensor_data` – emits real-time sensor updates
* `command_completed` – emitted when a command finishes
* `new_command` – emitted on new rover commands
* `request_latest_data` – client can request latest sensor snapshot

---

## 📊 Simulations

### Sensors

* 4 Probes: `Probe_1` to `Probe_4`
* Readings simulated every 10 seconds
* Metrics include: N, P, K, pH, humidity, temperature, soil moisture

### Rovers

* `rover_1`: Irrigation Rover
* `rover_2`: Fertilizer Rover
* Polls for pending commands and marks them completed after execution

---

## 🧱 Database Tables

* **sensor\_data**: Stores readings
* **commands**: Tracks rover command status
* **rovers**: Rover info (can be extended in future)

---

## ✅ Sample Output

**Sensor Data:**

```json
{
  "probe_id": "Probe_2",
  "nitrogen": 42.3,
  "phosphorus": 28.1,
  "temperature": 24.5,
  ...
}
```

**Command Completed:**

```json
{
  "command_id": "abc-123",
  "result": "Successfully executed irrigation in Zone A"
}
```

---

## 📌 Future Enhancements

* Docker containerization
* User authentication for secure access

---

## 📄 License

MIT License
© 2025 Hirthik Balaji

---

## 🙌 Contribute

Feel free to fork, submit issues, or pull requests. Feedback is always welcome!

---

## 📫 Contact

📧 Email: `hirthikbalaji2006@gmail.com`
🔗 GitHub: [@HirthikBalaji](https://github.com/HirthikBalaji)
