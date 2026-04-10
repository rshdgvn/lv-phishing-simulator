# Phishing Simulator

The **Phishing Simulator** is an internal cybersecurity platform developed by the **AIM Cybersecurity Committee**. It is designed to conduct authorized, educational phishing drills to assess and elevate institutional cybersecurity awareness. 

By simulating real-world phishing attacks in a safe, controlled environment, the platform identifies vulnerabilities and delivers immediate educational feedback to users who interact with the simulated threats.

---

## How It Works

The simulation lifecycle follows four simple phases:

1. **Deploy:** Administrators queue targets and deploy simulated phishing emails designed to mimic legitimate institutional communications.
2. **Simulate:** Targets who fail to spot the red flags and click the email link are routed to a convincing replica of the LMS login portal.
3. **Track:** The backend silently logs target engagement across three stages: `Sent` (delivered), `Clicked` (link accessed), and `Attempted Login` (credentials submitted).
4. **Educate:** If a user submits their credentials, the system intercepts the action—**without saving the password**—and instantly redirects them to a Phishing Awareness Page to explain the red flags they missed.

---

## Key Features

* **Real-Time Analytics Dashboard:** Multi-column UI to monitor Total Sent, Click Rates, and Attempted Login Rates live.
* **Target Management:** Easily add, manage, and remove targets for specific campaigns.
* **Live WebSocket Integration:** Dashboard statistics and target statuses update the exact second a user interacts with the simulation.
* **Zero-Knowledge Credential Handling:** Built with strict privacy. The platform measures the *act* of a login attempt without ever logging, storing, or transmitting actual passwords.

---

<!-- ## Interface & Simulation Examples

### 1. Admin Dashboard
*The central control hub for managing targets, deploying campaigns, and viewing real-time statistics.*
![Admin Dashboard Screenshot](path/to/your/admin-dashboard-screenshot.png)

### 2. Simulated Target Comparison (Fake vs. Real LMS)
*A side-by-side look at the authentic LMS portal versus our simulated phishing page. The simulation mimics the visual design but contains subtle red flags (like the URL) to test vigilance.*

**Legitimate LMS Login:**
![Real LMS Screenshot](path/to/your/real-lms-screenshot.png)
*The authentic portal with the correct, secure institutional domain.*

**Simulated Phishing LMS Login:**
![Fake LMS Screenshot](path/to/your/fake-lms-screenshot.png)
*The simulated portal used in the drill. Notice the deliberate URL mismatch—the primary indicator users should identify.*

### 3. Phishing Awareness & Education Page
*The educational landing page shown immediately to users who "fell" for the simulation, explaining how to spot actual threats.*
![Awareness Page Screenshot](path/to/your/awareness-page-screenshot.png)

--- -->

## Technology Stack

* **Backend:** FastAPI (Python)
* **Database & ORM:** Supabase (PostgreSQL), SQLAlchemy
* **Frontend:** HTML5, Vanilla CSS, JavaScript (CSS Grid/Flexbox)
* **Real-time Comms:** WebSockets

---

## Important Disclaimer & Ethics Statement

**AUTHORIZED DRILLS ONLY.** This platform was developed **strictly for educational and administrative purposes** by the AIM Cybersecurity Committee. 

* Passwords or sensitive credentials submitted to the simulated login pages are **NOT** stored, logged, or transmitted anywhere. The system only registers a boolean flag (`compromised: true`) to calculate vulnerability metrics.
* Misuse of this software for malicious purposes, unauthorized credential harvesting, or targeting individuals outside of an approved institutional cybersecurity drill is strictly prohibited.
