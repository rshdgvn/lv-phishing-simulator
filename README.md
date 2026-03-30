<!-- # LV Phishing Simulator 

**Cybersecurity Project:** A real-time phishing simulation platform to train school staff and improve internal cybersecurity awareness.

This tool allows school administration to deploy simulated phishing drills to employees. Instead of malicious payloads, staff who click a simulated link are redirected to a safe, educational landing page, providing an immediate "teachable moment" on how to spot real cyber threats. Engagement and click rates are tracked via a live dashboard.

## Core Features
* **Real-Time Dashboard:** Track open and click rates seamlessly.
* **Educational Redirects:** Turns a failed phishing test into an immediate learning opportunity for school staff.
* **Unique Token Tracking:** Safely monitors individual employee engagement without exposing sensitive data.
* **Modern UI:** Clean, responsive dashboard built with Tailwind CSS.

## Tech Stack
* **Backend:** Python, FastAPI
* **Frontend:** HTML, Jinja2 Templates, Tailwind CSS
* **Database:** SQLAlchemy (SQLite/PostgreSQL)
* **Real-Time:** WebSockets

--- -->

## Getting Started

Follow these instructions to set up the project on your local machine for development and testing.

### Prerequisites
Make sure you have [Python 3.8+](https://www.python.org/downloads/) installed on your machine.

### Installation

**1. Clone the repository**
```bash
git clone [https://github.com/rshdgvn/lv-phishing-simulator.git](https://github.com/rshdgvn/lv-phishing-simulator.git)
cd lv-phishing-simulator
```

**2. Create and activate a virtual environment**
```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the development server**
```bash
uvicorn app.main:app --reload
```

**5. View the App**
Open your web browser and navigate to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📂 Project Structure

```text
lv-phishing-simulator/
├── app/
│   ├── api/             # API Endpoints & WebSockets
│   ├── models/          # Database schemas
│   ├── services/        # Business logic (Emails, Tokens)
│   ├── templates/       # Jinja2 HTML views
│   └── main.py          # FastAPI application entry point
├── requirements.txt     # Python dependencies
```