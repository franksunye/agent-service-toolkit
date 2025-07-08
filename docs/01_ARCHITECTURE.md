# 🏗️ PDME-PoC Agentic 架构文档

## 🎯 项目概述

PDME-PoC (Prompt-Driven Model Evolution PoC) 是一个基于现代 Agentic 架构的智能 SQL 数据库助手。项目采用 **Planning → Tool Selection → Execution → Reflection** 的四阶段工作流程，让 AI Agent 根据用户意图自主选择和组合工具，实现智能的数据库操作和分析。

### 核心特性
- 🧠 **智能工具选择** - Agent 根据用户意图自主选择最合适的工具组合
- ⚡ **动态执行** - 避免硬编码流程，按需调用工具
- 🔧 **Function Calling** - 采用行业标准的工具调用接口
- 📊 **多轮对话** - 支持上下文感知的智能交互
- 🎯 **精准回复** - 基于工具执行结果生成有价值的回复

## 🧠 核心设计理念

### 1. 智能工具选择
- Agent 通过 LLM 分析用户意图，自主决定使用哪些工具
- 支持单工具执行和多工具组合
- 动态调整执行策略，避免硬编码的工具调用序列

### 2. Function Calling 标准
- 采用 OpenAI Function Calling 标准，确保工具调用的一致性
- 结构化的工具定义和参数传递
- 统一的错误处理和结果返回机制

### 3. 状态管理与上下文
- 完整的对话历史记录和工具执行状态跟踪
- 上下文感知的多轮对话支持
- 会话状态持久化，支持复杂的交互场景

## 🔧 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户输入 (prompt.txt)                      │
│                   文件变化触发机制                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              AgenticDatabaseMonitor                         │
│                (文件监控器)                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         AgenticPromptHandler                            │ │
│  │           (事件处理器)                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                AgenticSQLAgent                              │
│                (核心智能代理)                                 │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Planning   │→ │ Tool Select │→ │ Execution   │         │
│  │    阶段     │  │    阶段     │  │    阶段     │         │
│  │ LLM分析意图  │  │ 选择工具组合 │  │ 执行工具调用 │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                           │                 │
│  ┌─────────────┐                         │                 │
│  │ Reflection  │←────────────────────────┘                 │
│  │    阶段     │                                           │
│  │ 整合结果回复 │                                           │
│  └─────────────┘                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    工具层                                    │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   SQLTool   │  │DataAnalysis │  │ 未来扩展... │         │
│  │             │  │    Tool     │  │             │         │
│  │ 数据库操作   │  │ 智能分析     │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                DatabaseClient                               │
│                (SQLite 数据库)                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ • 连接管理 • 事务支持 • 错误处理 • 模式查询              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

- **编程语言**: Python 3.7+
- **AI 模型**: DeepSeek Chat API (支持 Function Calling)
- **数据库**: SQLite 3
- **文件监控**: Watchdog
- **HTTP 客户端**: Requests
- **环境管理**: python-dotenv

## 📁 项目结构

```
PDME-PoC/
├── src/                        # 源代码目录
│   ├── __init__.py             # 包初始化
│   ├── core/                   # 核心模块
│   │   ├── __init__.py         # 核心模块导出
│   │   ├── agentic_agent.py    # AgenticSQLAgent 核心智能代理
│   │   └── database.py         # DatabaseClient 数据库客户端
│   ├── tools/                  # 工具模块
│   │   ├── __init__.py         # 工具模块导出
│   │   ├── sql_tool.py         # SQLTool SQL执行工具
│   │   └── analysis_tool.py    # DataAnalysisTool 数据分析工具
│   └── monitor/                # 监控模块
│       ├── __init__.py         # 监控模块导出
│       └── file_monitor.py     # AgenticDatabaseMonitor 文件监控器
├── tests/                      # 测试目录
│   ├── __init__.py             # 测试包初始化
│   └── test_agentic_agent.py   # Agent 功能测试
├── examples/                   # 示例和演示
│   └── basic_demo.py           # 基础功能演示脚本
├── docs/                       # 文档目录
│   └── ARCHITECTURE.md         # 架构文档 (本文档)
├── data/                       # 数据文件目录
│   └── database.db             # SQLite 数据库文件
├── main.py                     # 主入口文件
├── prompt.txt                  # 用户输入文件 (监控目标)
├── requirements.txt            # Python 依赖配置
└── README.md                   # 项目说明文档
```

### 模块职责说明

#### 核心模块 (src/core/)
- **agentic_agent.py**: 实现 `AgenticSQLAgent` 类，负责四阶段工作流程
- **database.py**: 实现 `DatabaseClient` 类，提供数据库操作接口

#### 工具模块 (src/tools/)
- **sql_tool.py**: 实现 `SQLTool` 类，封装数据库操作功能
- **analysis_tool.py**: 实现 `DataAnalysisTool` 类，提供智能数据分析

#### 监控模块 (src/monitor/)
- **file_monitor.py**: 实现文件监控和事件处理逻辑

## 🔄 核心工作流程

### 四阶段 Agentic 工作流程

#### Phase 1: Planning (规划阶段)
```python
def _planning_phase(self, user_input: str) -> Dict[str, Any]:
```
1. **意图分析**: 使用 LLM 分析用户输入的真实意图
2. **工具选择**: 根据意图和当前数据库状态选择合适的工具
3. **执行规划**: 确定工具调用的顺序和参数
4. **Function Calling**: 生成符合 OpenAI 标准的工具调用指令

**实现细节**:
- 构建包含工具描述的系统提示
- 包含当前数据库状态信息
- 使用 DeepSeek API 进行智能决策
- 返回结构化的工具调用计划

#### Phase 2: Tool Execution (工具执行阶段)
```python
def _execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
```
1. **工具路由**: 根据工具名称路由到对应的工具实例
2. **参数处理**: 解析和验证工具调用参数
3. **安全执行**: 在受控环境中执行工具操作
4. **结果收集**: 收集工具执行结果和状态信息

**支持的工具**:
- `get_database_schema`: 获取数据库结构
- `generate_and_execute_sql`: 生成并执行 SQL
- `analyze_query_results`: 分析查询结果
- `analyze_database_schema`: 分析数据库设计

#### Phase 3: Reflection (反思整合阶段)
```python
def _reflection_phase(self, user_input: str, execution_results: List) -> Dict[str, Any]:
```
1. **结果整合**: 汇总所有工具执行结果
2. **智能分析**: 使用 LLM 分析结果的业务价值
3. **回复生成**: 生成有价值、易理解的最终回复
4. **状态更新**: 更新对话历史和执行状态

#### Phase 4: State Management (状态管理)
```python
self.conversation_state = {
    "messages": [],      # 对话消息历史
    "tool_calls": [],    # 工具调用历史
    "execution_history": []  # 执行结果历史
}
```

## 🛠️ 工具系统详解

### 工具架构设计

项目采用模块化的工具设计，每个工具都是独立的类，实现标准化的接口。工具通过 Function Calling 机制被 Agent 调用。

### 核心工具详解

#### 1. SQLTool (SQL 执行工具)
```python
class SQLTool:
    @staticmethod
    def get_schema() -> str
    @staticmethod
    def execute_sql(sql: str) -> Dict[str, Any]
    @staticmethod
    def list_all_tables() -> List[str]
    @staticmethod
    def get_table_structure(table_name: str) -> List
    @staticmethod
    def get_database_stats() -> Dict[str, Any]
```

**功能特性**:
- 数据库模式查询和表结构分析
- SQL 语句执行 (SELECT, INSERT, UPDATE, DELETE, DDL)
- 事务支持和错误处理
- 数据库统计信息收集

#### 2. DataAnalysisTool (数据分析工具)
```python
class DataAnalysisTool:
    def __init__(self, api_key: str, base_url: str)
    def analyze_data(self, query_result: Dict, context: str) -> str
    def analyze_schema(self, schema_info: str) -> str
```

**功能特性**:
- 基于 LLM 的智能数据分析
- 查询结果的业务洞察生成
- 数据库设计评估和优化建议
- 支持自定义分析上下文

### Function Calling 工具定义

#### 1. get_database_schema
- **功能**: 获取完整的数据库结构信息
- **参数**: 无
- **返回**: 包含所有表结构的详细信息
- **使用场景**: 用户询问数据库结构、表信息

#### 2. generate_and_execute_sql
- **功能**: 根据用户需求生成并执行 SQL 语句
- **参数**:
  - `user_request` (string): 用户的具体需求描述
  - `sql_query` (string): 要执行的 SQL 语句
- **返回**: SQL 执行结果和状态信息
- **使用场景**: 数据查询、修改、DDL 操作

#### 3. analyze_query_results
- **功能**: 分析查询结果并提供业务洞察
- **参数**:
  - `query_result` (object): 查询结果数据
  - `context` (string): 查询的业务上下文
- **返回**: 智能分析报告和建议
- **使用场景**: 需要数据分析和业务建议

#### 4. analyze_database_schema
- **功能**: 分析数据库模式并提供优化建议
- **参数**:
  - `schema_info` (string): 数据库模式信息
- **返回**: 设计评估和优化建议
- **使用场景**: 数据库设计评估、性能优化

## 🎯 实际使用示例

### 文件监控触发机制

用户通过编辑 `prompt.txt` 文件来触发 Agent 处理：

```bash
# 启动监控
python main.py

# 编辑 prompt.txt 文件
echo "数据库里有什么表？" > prompt.txt
```

### 典型使用场景

#### 场景 1: 数据库结构查询
```
用户输入: "数据库里有什么表？"
Agent 工作流程:
  Phase 1 (Planning): 分析意图 → 选择 get_database_schema
  Phase 2 (Execution): 调用 SQLTool.get_schema()
  Phase 3 (Reflection): 整合结果 → 生成友好回复
结果: 返回完整的数据库结构信息和表统计
```

#### 场景 2: 数据查询操作
```
用户输入: "查询所有用户信息"
Agent 工作流程:
  Phase 1 (Planning): 分析需求 → 选择 generate_and_execute_sql
  Phase 2 (Execution): 生成 SQL → 执行查询
  Phase 3 (Reflection): 格式化结果 → 生成报告
结果: 执行 SELECT 查询并返回格式化的数据
```

#### 场景 3: 复合智能分析
```
用户输入: "分析用户年龄分布并给出业务建议"
Agent 工作流程:
  Phase 1 (Planning): 复杂意图分析 → 选择多工具组合
  Phase 2 (Execution):
    1. generate_and_execute_sql (查询年龄数据)
    2. analyze_query_results (智能分析)
  Phase 3 (Reflection): 整合分析结果 → 生成业务洞察
结果: 数据查询 + 统计分析 + 业务建议
```

#### 场景 4: 数据库设计评估
```
用户输入: "评估当前数据库设计是否合理"
Agent 工作流程:
  Phase 1 (Planning): 设计评估需求 → 选择模式分析工具
  Phase 2 (Execution):
    1. get_database_schema (获取完整模式)
    2. analyze_database_schema (设计分析)
  Phase 3 (Reflection): 生成设计评估报告
结果: 数据库设计分析 + 优化建议 + 最佳实践
```

## 🚀 技术实现特点

### 1. 智能决策能力
- **LLM 驱动**: 使用 DeepSeek Chat API 进行智能决策
- **上下文感知**: 基于对话历史和数据库状态进行决策
- **动态适应**: 根据执行结果调整后续策略
- **意图理解**: 深度理解用户的真实需求

### 2. 标准化架构
- **Function Calling**: 严格遵循 OpenAI Function Calling 标准
- **结构化接口**: 统一的工具定义和参数传递格式
- **错误处理**: 标准化的错误处理和状态返回机制
- **API 兼容**: 支持多种 LLM API 提供商

### 3. 高可扩展性
- **模块化设计**: 核心、工具、监控模块完全解耦
- **插件架构**: 新工具可以无缝集成到现有系统
- **配置驱动**: 通过环境变量和配置文件管理系统行为
- **接口标准**: 统一的工具接口便于扩展

### 4. 生产级可靠性
- **事务支持**: 数据库操作支持事务和回滚
- **错误恢复**: 完整的异常处理和错误恢复机制
- **状态管理**: 完整的对话状态和执行历史记录
- **监控日志**: 详细的执行日志和性能监控

### 5. 开发友好
- **类型提示**: 完整的 Python 类型注解
- **文档完善**: 详细的代码注释和架构文档
- **测试覆盖**: 完整的单元测试和集成测试
- **示例丰富**: 多种使用场景的示例代码

## � 核心组件详解

### AgenticSQLAgent (核心智能代理)

```python
class AgenticSQLAgent:
    def __init__(self, api_key: str, base_url: str)
    def process_request(self, user_input: str) -> Dict[str, Any]
    def _planning_phase(self, user_input: str) -> Dict[str, Any]
    def _execute_tool(self, tool_call: Dict) -> Dict[str, Any]
    def _reflection_phase(self, user_input: str, results: List) -> Dict[str, Any]
```

**核心职责**:
- 四阶段工作流程的协调和执行
- LLM API 调用和响应处理
- 工具路由和执行管理
- 对话状态和历史管理

### DatabaseClient (数据库客户端)

```python
class DatabaseClient:
    def __init__(self, db_path: str = "data/database.db")
    def execute_sql(self, sql: str) -> Dict[str, Any]
    def get_schema_info(self) -> str
    def list_tables(self) -> List[str]
    def describe_table(self, table_name: str) -> List[Tuple]
```

**核心特性**:
- SQLite 连接管理和事务支持
- SQL 执行和结果格式化
- 数据库模式查询和分析
- 错误处理和连接池管理

### AgenticDatabaseMonitor (文件监控器)

```python
class AgenticDatabaseMonitor:
    def start(self)
    def stop(self)

class AgenticPromptHandler(FileSystemEventHandler):
    def on_modified(self, event)
    def _process_agentic_prompt(self)
```

**监控机制**:
- 基于 Watchdog 的文件系统监控
- 实时检测 prompt.txt 文件变化
- 自动触发 Agent 处理流程
- 支持热重载和状态恢复

## 🧪 测试和质量保证

### 测试架构

项目包含完整的测试套件，确保系统的可靠性和稳定性：

#### 单元测试 (tests/test_agentic_agent.py)
- **基本功能测试**: 验证 Agent 的核心工作流程
- **工具选择测试**: 验证智能工具选择的准确性
- **错误处理测试**: 验证异常情况的处理能力
- **状态管理测试**: 验证对话状态的正确维护

#### 集成测试 (examples/basic_demo.py)
- **端到端测试**: 完整的用户交互流程测试
- **多场景验证**: 不同使用场景的综合测试
- **性能基准**: 响应时间和资源使用监控

### 质量保证措施

1. **代码规范**: 遵循 PEP 8 Python 编码规范
2. **类型检查**: 完整的类型注解和静态检查
3. **文档覆盖**: 详细的代码注释和 API 文档
4. **错误处理**: 全面的异常处理和错误恢复
5. **日志记录**: 详细的执行日志和调试信息

## �🔮 扩展方向和路线图

### 短期扩展 (1-3 个月)

#### 1. 工具生态扩展
- **数据可视化工具**: 集成 matplotlib/plotly 生成图表
- **导出工具**: 支持 CSV、Excel、JSON 等格式导出
- **备份恢复工具**: 数据库备份和恢复功能

#### 2. 用户体验优化
- **Web 界面**: 基于 FastAPI + React 的 Web 界面
- **实时通知**: WebSocket 实时状态推送
- **历史管理**: 查询历史和结果缓存

### 中期扩展 (3-6 个月)

#### 3. 多数据库支持
- **MySQL/PostgreSQL**: 扩展到主流关系型数据库
- **NoSQL 支持**: MongoDB、Redis 等 NoSQL 数据库
- **云数据库**: AWS RDS、Azure SQL 等云数据库

#### 4. 高级分析功能
- **机器学习集成**: 集成 scikit-learn 进行数据挖掘
- **统计分析**: 高级统计分析和预测功能
- **报告生成**: 自动生成分析报告和仪表板

### 长期扩展 (6+ 个月)

#### 5. 企业级功能
- **权限管理**: 基于角色的访问控制 (RBAC)
- **多租户支持**: 支持多组织和用户隔离
- **审计日志**: 完整的操作审计和合规支持

#### 6. 智能化升级
- **自学习能力**: 基于使用历史优化工具选择
- **预测分析**: 基于历史数据进行趋势预测
- **自动优化**: 数据库性能自动优化建议

## 🎯 项目总结

### 技术创新点

1. **Agentic 架构**: 采用四阶段智能工作流程，实现真正的智能决策
2. **Function Calling**: 严格遵循行业标准，确保工具调用的一致性和可靠性
3. **动态工具选择**: Agent 根据用户意图自主选择工具，避免硬编码流程
4. **上下文感知**: 基于对话历史和数据库状态进行智能决策

### 架构优势

- **高度模块化**: 核心、工具、监控模块完全解耦，易于维护和扩展
- **标准化接口**: 统一的工具接口和错误处理机制
- **生产就绪**: 完整的错误处理、事务支持和监控日志
- **开发友好**: 完善的文档、测试和示例代码

### 适用场景

- **数据分析师**: 快速进行数据查询和分析
- **开发人员**: 数据库操作和模式设计验证
- **业务人员**: 通过自然语言进行数据查询
- **学习研究**: Agentic 架构和 Function Calling 的实践案例

### 部署和使用

```bash
# 1. 环境准备
git clone <repository-url>
cd PDME-PoC
pip install -r requirements.txt

# 2. 配置环境变量
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"

# 3. 启动系统
python main.py

# 4. 开始使用
echo "数据库里有什么表？" > prompt.txt
```

---

**PDME-PoC** 展示了现代 Agentic 架构在数据库操作领域的强大潜力，为智能数据助手的发展提供了坚实的技术基础和实践参考。
