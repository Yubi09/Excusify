# Excusify: AI-Powered Excuse Generator 🚀

Generate believable excuses for any situation, complete with supporting "evidence" in multiple formats. Powered by AI, Excusify is your go-to tool for those "I need an alibi" moments.

## ✨ Key Features

- **Smart Excuse Generation**: Context-aware excuses tailored to your scenario, role, and recipient.
- **Multi-Format Proofs**: Generate supporting documents, including:
  - 📄 Professional doctor's notes (PDF)
  - 💬 Convincing chat screenshots (PNG)
  - 📍 Location history logs (JSON)
- **Enhanced Believability**: Adjustable believability slider and urgency settings for a perfectly crafted excuse.
- **Voice Integration**: 🔊 Text-to-speech playback to practice your delivery and ensure it sounds authentic.
- **Excuse Vault**: Save and manage your most effective alibis for future use.
- **AI Insights Dashboard**: View popular scenarios and top-performing excuses based on anonymized, anonymous user feedback to choose the best approach.

## 🛠️ Technologies

### Backend
- **Python 3.8+**
- **Flask**: Lightweight web framework for the backend.
- **Hugging Face API**: For powerful AI-driven excuse generation. (Mixtral-8x7B-Instruct-v0.1)
- **gTTS**: For text-to-speech conversion.
- **ReportLab**: For creating professional PDF documents.
- **Pillow**: For generating realistic chat screenshots.
- **python-dotenv**: For secure management of API keys.
- **gunicorn**: Reliable server for running Flask apps in production.

### Frontend
- **HTML5, CSS3, JavaScript**: Core technologies for the user interface.
- **Responsive Design**: Ensures a seamless experience across all devices.

## 🚀 Quick Setup

### Prerequisites
- Python 3.8+
- `pip` package manager (included with Python)
- Git for cloning the repository

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Yubi09/Excusify.git
   cd excusify
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```plaintext
   HUGGINGFACE_API_TOKEN="YOUR_HUGGINGFACE_API_TOKEN_HERE"
   ```
   Obtain your API token from [Hugging Face](https://huggingface.co/settings/tokens).


## 🎯 How to Use

1. **Access the Interface**: Navigate to `http://127.0.0.1:5000/`.
2. **Define Your Scenario**: Select Scenario, Role, Recipient, and Urgency. Adjust the Believability slider.
3. **Generate Excuse**: Click "Generate Excuse" to create your alibi.
4. **Practice Delivery**: Use "Speak Excuse" to hear the excuse aloud.
5. **Save Excuse**: Save effective excuses to your vault.
6. **Generate Proof**: Select a proof type (e.g., Doctor's Note) and click "Generate Proof".
7. **Explore Insights**: View popular scenarios and top excuses in the AI Insights dashboard.
8. **Manage Vault**: Re-use or delete saved excuses in the "Saved Excuses" section.


## 🤝 Contributing

I welcome contributions!