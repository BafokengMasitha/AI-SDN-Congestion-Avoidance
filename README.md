🚦 AI-SDN Congestion Avoidance 🧠📡
An AI-enhanced Software-Defined Networking (SDN) system that uses Unsupervised Machine Learning (Isolation Forest) to detect and help mitigate network congestion. This project combines intelligent traffic monitoring with a dynamic SDN environment.

🌟 Features
🧠 Isolation Forest ML Model for anomaly detection in network flow data

📈 Flow-based Feature Monitoring to detect congestion risks in real time

💡 Ryu SDN Controller for flow rule management and decision making

🧪 Mininet Topology for virtual network testing

🗃️ Offline Model Training with PCA visualization

🔄 Joblib Serialization to save and reuse the trained model

🛠️ Future Integration: Real-time congestion reaction & automated rerouting

🧠 How It Works
Flow data is captured from the SDN environment (e.g., using Mininet or real switches).

Selected flow features (e.g., packet lengths, byte rates, durations) are normalized.

An Isolation Forest model is trained offline on historical data to detect "normal" vs "anomalous" flows.

The model flags abnormal traffic patterns that may indicate congestion, DDoS, or link failures.

These anomalies can then trigger automated decisions in the Ryu controller (e.g., rerouting or throttling).

🛠️ Technologies & Tools
Python – ML training, visualization, and integration

Scikit-learn – Isolation Forest, PCA

Joblib – Save/load ML models

Mininet – Network emulation

Ryu – OpenFlow SDN controller

Matplotlib & Seaborn – Visualization

Pandas & NumPy – Data processing

⚙️ How to Run
1. Clone the Repository
git clone https://github.com/yourusername/AI-SDN-Congestion-Avoidance.git
cd AI-SDN-Congestion-Avoidance

2. Set Up Python Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. Train or Load the ML Model
Use model/isolationForest.ipynb to train the model on flow data
Or load the pre-trained isolation_forest_model.joblib

4. Run the Ryu Controller
ryu-manager ryu_app/simple_switch_13.py

6. Launch Mininet Topology
sudo mn --custom topology/topo_2sw_2host.py --topo mytopo --controller=remote --mac --link tc

📊 Model Insights
Type: Unsupervised Learning (Isolation Forest)

Input: 13 flow-based features (duration, bytes/sec, packet length, etc.)

Output: anomaly or normal label

Evaluation: PCA used for 2D visual inspection (unsupervised evaluation)

🔭 Future Extensions
Real-time packet inspection & stat extraction

Automatic flow redirection or throttling

Extension to multi-domain SDNs

