# ⚡ 快速开始指南

## 🎯 5分钟部署到Streamlit Cloud

### 步骤1: 获取API密钥 (2分钟)

访问 [DeepSeek API](https://platform.deepseek.com/) 获取免费API密钥：
1. 注册账户
2. 创建API密钥
3. 复制密钥（格式：`sk-xxx`）

### 步骤2: Fork仓库 (30秒)

1. 访问 [本项目GitHub页面](https://github.com/franksunye/agent-service-toolkit)
2. 点击右上角 **Fork** 按钮
3. Fork到你的GitHub账户

### 步骤3: 部署到Streamlit Cloud (2分钟)

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 使用GitHub账户登录
3. 点击 **"New app"**
4. 选择你Fork的仓库：`your-username/agent-service-toolkit`
5. 设置配置：
   - **Main file path**: `src/streamlit_standalone.py`
   - **Python version**: 3.10
6. 点击 **"Advanced settings"**
7. 在 **Secrets** 区域添加：

```toml
DEEPSEEK_API_KEY = "你的DeepSeek API密钥"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
```

8. 点击 **"Deploy!"**

### 步骤4: 开始使用 (30秒)

部署完成后，你将看到：
- 🎉 应用成功启动
- 💬 SQL Agent欢迎界面
- 🔧 侧边栏设置选项

**试试这些查询**：
- "What tables are available?"
- "Show me all users"
- "Analyze our sales data"

## 🛠️ 本地开发（可选）

如果你想在本地测试：

```bash
# 克隆你的Fork
git clone https://github.com/your-username/agent-service-toolkit.git
cd agent-service-toolkit

# 安装依赖
pip install -r requirements-standalone.txt

# 设置环境变量
echo "DEEPSEEK_API_KEY=你的密钥" > .env

# 运行应用
streamlit run src/streamlit_standalone.py
```

## 🎯 功能特色

### 🤖 SQL Agent
- **智能数据库助手**：4阶段工作流程
- **自然语言查询**：用普通话描述需求
- **数据可视化**：自动生成表格和图表
- **安全保护**：防SQL注入，查询验证

### 🔍 Research Assistant  
- **网络搜索**：实时信息检索
- **智能总结**：自动整理搜索结果
- **多源验证**：交叉验证信息准确性

### 💬 Chatbot
- **通用对话**：日常交流和问答
- **上下文记忆**：记住对话历史
- **多轮对话**：支持复杂交互

## 🔧 高级配置

### 添加更多API密钥

在Streamlit Cloud的Secrets中添加：

```toml
# 可选：OpenAI支持
OPENAI_API_KEY = "你的OpenAI密钥"

# 可选：天气查询
OPENWEATHERMAP_API_KEY = "你的天气API密钥"

# 可选：LangSmith追踪
LANGSMITH_API_KEY = "你的LangSmith密钥"
LANGSMITH_PROJECT = "my-sql-agent"
LANGCHAIN_TRACING_V2 = true
```

### 自定义配置

修改 `.streamlit/config.toml`：

```toml
[theme]
primaryColor = "#FF6B6B"        # 主色调
backgroundColor = "#FFFFFF"     # 背景色
secondaryBackgroundColor = "#F0F2F6"  # 次要背景色
textColor = "#262730"          # 文字颜色
```

## 🚨 故障排除

### 常见问题

**Q: 应用启动失败？**
A: 检查API密钥是否正确设置，确保格式为 `sk-xxx`

**Q: SQL查询没有响应？**  
A: 确认DEEPSEEK_API_KEY有效，检查API配额

**Q: 导入错误？**
A: 确认使用 `src/streamlit_standalone.py` 作为主文件

**Q: 数据库连接失败？**
A: 应用会自动创建SQLite数据库，无需额外配置

### 获取帮助

- 📖 查看 [完整部署指南](STREAMLIT_CLOUD_DEPLOYMENT.md)
- 🔍 查看 [验证报告](DEPLOYMENT_VERIFICATION.md)  
- 💬 在GitHub Issues中提问

## 🎉 成功！

恭喜！你现在拥有了一个功能完整的AI Agent服务，包括：

- ✅ **零成本部署**：完全免费的Streamlit Cloud
- ✅ **生产就绪**：安全、稳定、可扩展
- ✅ **功能完整**：SQL分析、网络搜索、智能对话
- ✅ **易于维护**：简单配置，自动更新

**开始探索你的AI Agent吧！** 🚀
