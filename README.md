# ✅ TrustChain – Verify Skills, Not Just Words.

**TrustChain** helps you prove your real-world skills (like coding!) through AI analysis and blockchain-backed proof. Upload your resume, and get a verified skill report—simple, honest, and trusted.

🎥 [Watch Demo Video](https://your-demo-video-link.com)

---

## 🧠 What It Does (In Simple Words)

1. **Login securely** using your GitHub(Due to limitation, we've used Google).
2. **Upload your resume** (PDF).
3. **AI checks your GitHub** profile, reads your code, and finds your strengths.
4. It generates a **skill verification report** (like: "Python – Strong", "React – Good").
5. That report is saved to the **Walrus decentralized storage**.
6. You (or anyone else) can **view your proof** anytime – verified and tamper-proof.

---

## 🏗️ Project Structure

```
trustchain/
├── frontend/     # Typescript + Vite app
├── backend/      # Django REST API + AI logic
├── .env          # Backend environment variables
```

---

## ⚙️ Setup Instructions

### 1. Backend (Python + Django REST)

> Make sure you have Python 3.9+ and pip installed.

```bash
cd backend
python -m venv env
source env/bin/activate   # on Windows use `env\Scripts\activate`
pip install -r requirements.txt
cp .env.example .env      # Add your GitHub token + OpenAI key here
python manage.py runserver
```

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
cp .env.example .env      # Add Enoki + Google credentials here
npm run dev
```

---

## 🔑 Required .env Variables

### Backend `.env`
```
GITHUB_TOKEN=your_github_pat_here
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend `.env`
```
VITE_APP_ENOKI_PUBLIC_KEY=your_enoki_key
VITE_APP_GOOGLE_CLIENT_ID=your_google_client_id
VITE_APP_NETWORK=testnet
```

---

## 🔁 Flow / Architecture

![alt text](image.png)

- **zkLogin**: Secure, passwordless login using zkProofs.
- **LLMs**: Analyze GitHub repo locally (clone & scan).
- **Walrus**: Decentralized blob storage for verified reports.

---

## 📦 Backend Dependencies (requirements.txt)

```
Django>=4.2
djangorestframework
openai
PyGithub
python-decouple
django-cors-headers
requests
```

---

## 🚀 Why TrustChain?

- ✅ AI-analyzed real skill reports
- 🔒 Secure, blockchain-backed proof
- 📂 Store & share anytime
- 🧠 Perfect for devs, recruiters, or upskilling platforms

---

Made with ❤️ at an international hackathon in Nepal 🇳🇵
