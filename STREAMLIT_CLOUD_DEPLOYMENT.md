# 🚀 Streamlit Cloud Deployment Guide

## 📋 Quick Start

This project now supports **dual deployment modes**:

1. **Original Mode**: FastAPI backend + Streamlit frontend (existing functionality)
2. **Standalone Mode**: Pure Streamlit Cloud deployment (new capability)

## 🎯 Standalone Streamlit Cloud Deployment

### Option 1: Deploy Standalone Version to Streamlit Cloud

**File to deploy**: `src/streamlit_standalone.py`

#### Step 1: Fork this repository to your GitHub account

#### Step 2: Deploy to Streamlit Cloud
1. Visit [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select your forked repository
4. Set the main file path: `src/streamlit_standalone.py`
5. Configure environment variables (see below)

#### Step 3: Configure Environment Variables in Streamlit Cloud

In the Streamlit Cloud dashboard, add these secrets:

```toml
# Required: At least one LLM API key
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Optional: Additional API keys
OPENAI_API_KEY = "your_openai_api_key_here"
OPENWEATHERMAP_API_KEY = "your_weather_api_key_here"

# Optional: LangSmith tracing
LANGSMITH_API_KEY = "your_langsmith_api_key_here"
LANGSMITH_PROJECT = "sql-agent-standalone"
LANGCHAIN_TRACING_V2 = true

# Application settings
APP_MODE = "standalone"
DATABASE_TYPE = "sqlite"
SQLITE_DB_PATH = "data/checkpoints.db"
```

### Option 2: Deploy Original Version (FastAPI + Streamlit)

Follow the instructions in the main README.md for the traditional deployment approach.

## 🔧 Local Development

### Test Standalone Version Locally

```bash
# Install dependencies
pip install -r requirements-standalone.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run standalone app
streamlit run src/streamlit_standalone.py
```

### Test Original Version Locally

```bash
# Install all dependencies
pip install -r requirements.txt

# Start FastAPI backend
python src/run_service.py

# In another terminal, start Streamlit frontend
streamlit run src/streamlit_app.py
```

## ✨ Features

Both deployment modes support:

- ✅ **SQL Agent**: Intelligent database operations with 4-phase workflow
- ✅ **Research Assistant**: Web search and information gathering
- ✅ **Chatbot**: General conversation capabilities
- ✅ **Multi-model Support**: DeepSeek, OpenAI, and more
- ✅ **Memory Persistence**: Conversation history and context
- ✅ **Streaming Responses**: Real-time response generation
- ✅ **SQL Result Visualization**: Interactive tables and data display

## 🎯 Deployment Comparison

| Feature | Standalone Mode | Original Mode |
|---------|----------------|---------------|
| **Deployment Complexity** | ⭐ Simple | ⭐⭐⭐ Complex |
| **Cost** | 🆓 Free | 💰 Requires backend hosting |
| **Scalability** | ⭐⭐ Good | ⭐⭐⭐ Excellent |
| **Features** | ⭐⭐⭐ Full | ⭐⭐⭐ Full |
| **Maintenance** | ⭐⭐⭐ Easy | ⭐⭐ Moderate |

## 🚨 Important Notes

### For Streamlit Cloud Deployment:
- Use `src/streamlit_standalone.py` as the main file
- Configure environment variables in Streamlit Cloud secrets
- SQLite database will be created automatically
- No backend service required

### For Traditional Deployment:
- Use `src/streamlit_app.py` as the main file
- Requires separate FastAPI backend deployment
- More complex but more scalable

## 🔍 Troubleshooting

### Common Issues:

1. **Missing API Keys**: Ensure DEEPSEEK_API_KEY or OPENAI_API_KEY is set
2. **Import Errors**: Check that all dependencies are installed
3. **Database Issues**: Ensure data directory exists and is writable

### Getting Help:

- Check the logs in Streamlit Cloud dashboard
- Verify environment variables are correctly set
- Test locally first before deploying to cloud

## 🎉 Success!

Once deployed, your SQL Agent will be available at your Streamlit Cloud URL with full functionality including:
- Database schema exploration
- SQL query execution
- Data analysis and insights
- Multi-turn conversations
- Real-time streaming responses

**Enjoy your cloud-deployed SQL Agent! 🚀**
