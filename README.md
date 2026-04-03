
# FitPulse - Health Anomaly Detection

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-lightgrey?style=for-the-badge&logo=flask)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**FitPulse** is a web-based health monitoring application designed to track vital signs, visualize health trends, and automatically detect anomalies. Built as an Infosys project, it provides users with actionable insights into their heart rate, daily activity, and sleep patterns.

---

## 📖 Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Dataset](#-dataset)
- [Installation](#-installation)
- [Usage](#-usage)
- [License](#-license)

---

## ✨ Features

- **User Authentication**: Secure registration and login system with password hashing.
- **Data Entry**: Intuitive forms to log Heart Rate, Steps, and Sleep duration.
- **Automated Anomaly Detection**:
  - Calculates health status (Healthy, Warning, Critical) based on input metrics.
  - Visual alerts for abnormal heart rates or sleep deprivation.
- **Interactive Dashboard**:
  - Real-time visualization using HTML5 Canvas (Time vs. Value graphs).
  - Clickable data table rows to highlight specific points on graphs.
- **Data Export**: One-click export of health records to CSV for external analysis.
- **Responsive Design**: Modern dark-themed UI optimized for both desktop and mobile devices.

---

## 🛠 Tech Stack

**Backend:**
- Python 3.x
- Flask (Web Framework)

**Frontend:**
- HTML5, CSS3, JavaScript
- HTML5 Canvas API (for Charts)
- Jinja2 (Templating)

---

## 📁 Project Structure

```text
FitPulse/
│
├── app.py                # Main Flask application logic
├── database.sql          # Database schema
├── health_dataset.csv    # Sample dataset for testing
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
│
├── static/
│   └── style.css         # All CSS styles (Dark Theme)
│
└── templates/
    ├── welcome.html      # Landing page
    ├── login.html        # Login form
    ├── register.html     # Registration form
    ├── home.html         # User home dashboard
    ├── dashboard.html    # Main visualization & data table
    ├── data_entry.html   # Form to add health data
    └── profile.html      # User profile settings
```

---

## 📊 Dataset

This repository includes a sample dataset (`health_dataset.csv`) containing sample health records.

- **File:** `health_dataset.csv`
- **Columns:**
  - `Date`: Timestamp of the entry.
  - `Heart_Rate`: Beats per minute (bpm).
  - `Steps`: Daily step count.
  - `Sleep`: Hours of sleep.
  - `Status`: Calculated health status (Healthy, Warning, Critical).

You can view this file in Excel, Google Sheets, or any text editor.

---

## ⚙️ Installation

Follow these steps to set up the project locally.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/fitpulse.git
cd fitpulse
```

### 2. Set up the Virtual Environment (Optional but recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
Create a `requirements.txt` file with the following content:
```text
Flask
mysql-connector-python
werkzeug
```
Then run:
```bash
pip install -r requirements.txt
```

### 4. Database Setup
1. Create a database in your MySQL client.
2. Run the `database.sql` script to create the necessary tables.
3. Configure your database credentials in `app.py`.

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🚀 Usage

1. **Register**: Create a new account via the "Register" page.
2. **Login**: Access your personalized dashboard.
3. **Add Data**: Click "Add Data" in the navigation bar to log your daily health metrics.
4. **Analyze**: 
   - View your averages on the Dashboard.
   - Observe trends in the Canvas graphs.
   - Click on a row in the table to highlight that data point on the graph.
5. **Export**: Click the "Export" button to download your data as a CSV file.

---

## 📄 License

This project is licensed under the MIT License.

---

**Developed for Infosys springboard internship**
```
