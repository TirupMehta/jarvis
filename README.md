# Jarvis – AI-Driven Personal Assistant for Desktop Automation

**Author: Tirup Mehta**

Jarvis is an advanced AI-powered personal assistant that tightly integrates with your desktop system to provide a powerful layer of intelligent automation. Unlike traditional assistants, Jarvis is entirely modular, lightning-fast, and fully customizable — with all its functionality packed in a single, clean Python file for simplicity and extensibility. Built with modern AI tools and designed for professional-grade usage, Jarvis sets itself apart by supporting direct integration with state-of-the-art AI models like Google's Gemini and Gemma series.

---

## What Makes Jarvis Unique?

Jarvis isn't just another desktop assistant. It's a fully modular, AI-native solution designed for developers and power users who demand control, flexibility, and intelligence:

* **Single-File Simplicity**: The entire system is written in one well-structured Python file for easy auditing, modification, and deployment.
* **Plug-and-Play AI Core**: Jarvis can be instantly adapted to support different LLMs (Large Language Models). Simply modify a few lines to switch models.
* **Fully Customizable AI Integration**: Swap AI models using your own API keys from Google AI Studio. Jarvis gives you total control over the intelligence driving it.
* **Fast, Lightweight, and Local-Controlled**: No bloated frameworks or hidden backend services — everything runs locally with optional AI-enhanced capabilities.
* **Open Source**: Jarvis is free to use, with no subscriptions, upsells, or locked features. It is — and always will be — entirely open source and community-driven.
* **Future-Proof and Extensible**: Jarvis is designed with a forward-looking architecture — new capabilities can be added with minimal changes, keeping it both lean and powerful.

---

## How to Use Your Own Google API Key and Model

To personalize Jarvis with your preferred Gemini/Gemma AI model:

1. **Get Your API Key from Google AI Studio**

   * Visit [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   * Sign in and generate your API key

2. **Insert Your API Key**

   * Open the `jarvis.py` file
   * Navigate to **line 79** and replace the placeholder string with your API key:

     ```python
     GEMINI_API_KEY = "YOUR_API_KEY_HERE"
     ```

3. **Change the Model Name**

   * On **line 88**, you can change the model name to any of the currently supported Gemini or Gemma models:

     ```python
     model_name = 'gemma-3n-e4b-it'
     ```

   **Supported Model Names (as of now):**

   * gemini-2.5-flash
   * gemini-2.5-pro
   * gemini-2.0-flash
   * gemini-2.0-flash-lite
   * gemini-1.5-pro
   * gemini-1.5-flash
   * gemini-1.5-flash-8b

   These models provide various capabilities like vision understanding, conversational memory, and faster inference depending on your needs.

---

## Key Features

### System Automation

* Launch and terminate applications
* Perform system operations: shutdown, restart, and sleep
* Media control: volume, playback, track skip

### Productivity Suite

* Multi-timer support
* In-session note-taking
* Clipboard read/write utilities
* Automated typing in other windows

### Information Access

* Live system monitoring (CPU, RAM)
* Network diagnostics
* Date/time queries
* Real-time weather and web search

### File Operations

* Directory listing and navigation
* Folder creation and file launching

### Utility Functions

* Calculator
* Random number/dice/coin
* Jokes and casual interaction

---

## Upcoming Features

Jarvis is actively evolving. Here's a preview of what’s coming soon:

* **Voice Interaction Support**: Engage with Jarvis through natural voice commands using speech recognition and real-time audio feedback.
* **Custom Action Pipelines**: Define complex multi-step tasks using plain language — from opening apps to performing data lookups.
* **Context-Aware Conversations**: Jarvis will retain context over longer interactions to support more intelligent, memory-based responses.
* **Plugin System**: Allow third-party developers to extend Jarvis with installable modules for specialized use cases.
* **Cloud-Syncable Notes & Timers**: Seamless syncing between devices through optional encrypted cloud integration.
* **Desktop Widget Mode**: Persistent minimal UI widget on your desktop for glanceable information and quick interaction.

---

## Technology Stack

* Python 3.11+
* Google Generative AI SDK
* Tkinter (for GUI)
* psutil
* subprocess, platform, datetime, os, sys

---

## Installation

```bash
git clone https://github.com/tirupmehta/jarvis-ai-assistant.git
cd jarvis-ai-assistant
pip install -r requirements.txt
python jarvis.py
```

---

## Usage

Jarvis supports both CLI and a simple graphical interface. Interact with it naturally using phrases like:

* "Start a timer for 10 minutes"
* "Open YouTube"
* "Check RAM usage"
* "What's the weather in New York?"
* "Search Google for neural networks"

---

## Vision

Jarvis represents the convergence of AI, automation, and desktop control in one fluid experience. Its minimal design and maximal capability reflect a future where users interact with their systems intelligently, not mechanically.

---

## Credits

Jarvis is developed and maintained by **Tirup Mehta**. Inspired by the next generation of personal computing, built with the capabilities of modern **Artificial Intelligence**.

---

## License

MIT License. See LICENSE for full terms.

---

## Contributing

Pull requests and ideas are welcome. Please open an issue to start the conversation or contribute directly by forking the project.

---

**Jarvis is not another assistant — it’s your personalized command hub, powered by AI and engineered for control.**
