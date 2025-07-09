# 🔍 可观测性、可解释性与可追溯性设计文档

## 🎯 概述

在AI Native项目中，可观测性(Observability)、可解释性(Explainability)和可追溯性(Traceability)是确保系统可靠性、透明度和可维护性的核心要素。本文档分析Agent Service Toolkit的现状并规划未来扩展。

## 📊 现状分析

### 1. 可观测性 (Observability) 现状

#### ✅ 已实现的可观测性功能

**日志系统**:
```python
# 结构化日志配置
def configure_logging():
    log_level = logging.DEBUG if settings.is_dev() else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # 模块级日志控制
    logging.getLogger("core.database").setLevel(log_level)
    logging.getLogger("core.deepseek_client").setLevel(log_level)
    logging.getLogger("agents.sql_agent").setLevel(log_level)
```

**健康检查机制**:
```python
@app.get("/health")
async def health_check():
    health_status = {"status": "ok"}
    
    if settings.LANGFUSE_TRACING:
        try:
            langfuse = Langfuse()
            health_status["langfuse"] = "connected" if langfuse.auth_check() else "disconnected"
        except Exception as e:
            logger.error(f"Langfuse connection error: {e}")
            health_status["langfuse"] = "disconnected"
    
    return health_status
```

**错误处理与追踪**:
```python
# 数据库操作错误分类
except SQLValidationError as e:
    return {"success": False, "error": str(e), "error_type": "VALIDATION_ERROR"}
except sqlite3.Error as e:
    return {"success": False, "error": str(e), "error_type": "DATABASE_ERROR"}
except Exception as e:
    return {"success": False, "error": str(e), "error_type": "UNKNOWN_ERROR"}
```

#### ❌ 缺失的可观测性功能

1. **性能指标收集**: 缺少Prometheus/Grafana集成
2. **分布式追踪**: 缺少请求链路追踪
3. **业务指标监控**: 缺少Agent执行成功率、响应时间等指标
4. **资源使用监控**: 缺少内存、CPU、数据库连接池监控

### 2. 可解释性 (Explainability) 现状

#### ✅ 已实现的可解释性功能

**Agent决策过程记录**:
```python
# SQL Agent的4阶段工作流程
class SQLAgentState(MessagesState, total=False):
    planning_result: Optional[Dict[str, Any]]        # 规划阶段结果
    tool_execution_results: List[Dict[str, Any]]     # 工具执行结果
    database_context: Optional[str]                  # 数据库上下文
    analysis_insights: Optional[str]                 # 分析洞察
```

**工具选择逻辑**:
```python
async def should_use_tools(state: SQLAgentState) -> Literal["tools", "reflection"]:
    """判断是否需要执行工具的决策逻辑"""
    logger.info("🤔 Determining whether to use tools or go to reflection")
    
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info("✅ Going to tools node")
        return "tools"
    else:
        logger.info("⚠️ No tool calls found, going to reflection")
        return "reflection"
```

**安全评估透明度**:
```python
# LlamaGuard安全检查
def check_safety(state: AgentState) -> Literal["unsafe", "safe"]:
    safety: LlamaGuardOutput = state["safety"]
    match safety.safety_assessment:
        case SafetyAssessment.UNSAFE:
            return "unsafe"
        case _:
            return "safe"
```

#### ❌ 缺失的可解释性功能

1. **决策路径可视化**: 缺少Agent决策树/流程图展示
2. **推理过程详细记录**: 缺少LLM推理步骤的详细记录
3. **置信度评估**: 缺少Agent决策的置信度评分
4. **反事实解释**: 缺少"如果...会怎样"的解释机制

### 3. 可追溯性 (Traceability) 现状

#### ✅ 已实现的可追溯性功能

**LangSmith集成**:
```python
# LangSmith追踪配置
LANGCHAIN_TRACING_V2: bool = False
LANGCHAIN_PROJECT: str = "default"
LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
LANGCHAIN_API_KEY: SecretStr | None = None
```

**用户反馈系统**:
```python
@router.post("/feedback")
async def feedback(feedback: Feedback) -> FeedbackResponse:
    """记录用户反馈到LangSmith"""
    client = LangsmithClient()
    client.create_feedback(
        run_id=feedback.run_id,
        key=feedback.key,
        score=feedback.score,
        **feedback.kwargs
    )
```

**会话状态追踪**:
```python
# 会话和用户ID追踪
configurable = {
    "thread_id": thread_id, 
    "model": user_input.model, 
    "user_id": user_id
}
```

**记忆系统追踪**:
```python
# 用户查询历史追踪
async def save_query_to_memory(state: SQLAgentState, config: RunnableConfig, store: BaseStore):
    query_record = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "executed_queries": executed_queries,
        "success": len(executed_queries) > 0
    }
```

#### ❌ 缺失的可追溯性功能

1. **端到端请求追踪**: 缺少完整的请求生命周期追踪
2. **数据血缘关系**: 缺少数据流向和依赖关系追踪
3. **模型版本追踪**: 缺少LLM模型版本和配置变更追踪
4. **审计日志**: 缺少完整的操作审计和合规性日志

## 🚀 未来扩展规划

### 阶段一：增强可观测性 (1-2个月)

#### 1.1 性能监控系统
```python
# Prometheus指标集成
from prometheus_client import Counter, Histogram, Gauge

# 核心业务指标
AGENT_REQUESTS_TOTAL = Counter(
    'agent_requests_total', 
    'Total agent requests', 
    ['agent_id', 'user_id', 'status']
)

AGENT_REQUEST_DURATION = Histogram(
    'agent_request_duration_seconds',
    'Agent request duration',
    ['agent_id', 'phase']
)

ACTIVE_SESSIONS = Gauge(
    'active_sessions_total',
    'Number of active user sessions'
)

LLM_TOKEN_USAGE = Counter(
    'llm_tokens_total',
    'Total LLM tokens consumed',
    ['model', 'type', 'agent_id']
)
```

#### 1.2 分布式追踪
```python
# OpenTelemetry集成
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 追踪Agent执行
@trace.get_tracer(__name__).start_as_current_span("agent_execution")
async def execute_agent_with_tracing(agent_id: str, input_data: dict):
    span = trace.get_current_span()
    span.set_attribute("agent.id", agent_id)
    span.set_attribute("user.id", input_data.get("user_id"))
    
    try:
        result = await agent.ainvoke(input_data)
        span.set_attribute("execution.status", "success")
        return result
    except Exception as e:
        span.set_attribute("execution.status", "error")
        span.set_attribute("error.message", str(e))
        raise
```

#### 1.3 实时监控仪表板
```python
# Grafana仪表板配置
DASHBOARD_METRICS = {
    "agent_performance": {
        "success_rate": "rate(agent_requests_total{status='success'}[5m])",
        "avg_response_time": "avg(agent_request_duration_seconds)",
        "error_rate": "rate(agent_requests_total{status='error'}[5m])"
    },
    "system_health": {
        "memory_usage": "process_resident_memory_bytes",
        "cpu_usage": "rate(process_cpu_seconds_total[5m])",
        "db_connections": "db_connections_active"
    }
}
```

### 阶段二：提升可解释性 (2-3个月)

#### 2.1 决策过程可视化
```python
# Agent决策树记录
class DecisionNode:
    def __init__(self, node_id: str, decision_type: str, input_data: dict):
        self.node_id = node_id
        self.decision_type = decision_type
        self.input_data = input_data
        self.output_data = None
        self.reasoning = None
        self.confidence = None
        self.timestamp = datetime.now()
        self.children = []

class DecisionTracker:
    def __init__(self):
        self.decision_tree = None
        self.current_node = None
    
    def start_decision(self, node_id: str, decision_type: str, input_data: dict):
        node = DecisionNode(node_id, decision_type, input_data)
        if self.decision_tree is None:
            self.decision_tree = node
        else:
            self.current_node.children.append(node)
        self.current_node = node
        return node
    
    def record_decision(self, output_data: dict, reasoning: str, confidence: float):
        if self.current_node:
            self.current_node.output_data = output_data
            self.current_node.reasoning = reasoning
            self.current_node.confidence = confidence
```

#### 2.2 推理过程详细记录
```python
# LLM推理步骤追踪
class ReasoningStep:
    def __init__(self, step_type: str, input_prompt: str, output: str):
        self.step_type = step_type
        self.input_prompt = input_prompt
        self.output = output
        self.timestamp = datetime.now()
        self.token_usage = None
        self.model_config = None

async def track_llm_reasoning(model: BaseChatModel, messages: list, config: dict):
    """追踪LLM推理过程"""
    reasoning_tracker = ReasoningTracker()
    
    # 记录输入
    reasoning_tracker.add_step(
        step_type="input_processing",
        input_prompt=str(messages),
        output=None
    )
    
    # 执行推理
    response = await model.ainvoke(messages, config)
    
    # 记录输出
    reasoning_tracker.add_step(
        step_type="output_generation",
        input_prompt=None,
        output=response.content
    )
    
    return response, reasoning_tracker.get_trace()
```

#### 2.3 置信度评估系统
```python
# 决策置信度评估
class ConfidenceEvaluator:
    def __init__(self):
        self.evaluation_criteria = {
            "data_quality": 0.3,
            "model_certainty": 0.4,
            "historical_accuracy": 0.3
        }
    
    def evaluate_decision_confidence(self, decision_context: dict) -> float:
        """评估决策置信度"""
        scores = {}
        
        # 数据质量评分
        scores["data_quality"] = self._evaluate_data_quality(
            decision_context.get("input_data")
        )
        
        # 模型确定性评分
        scores["model_certainty"] = self._evaluate_model_certainty(
            decision_context.get("model_output")
        )
        
        # 历史准确性评分
        scores["historical_accuracy"] = self._evaluate_historical_accuracy(
            decision_context.get("similar_cases")
        )
        
        # 加权平均
        confidence = sum(
            scores[criterion] * weight 
            for criterion, weight in self.evaluation_criteria.items()
        )
        
        return min(max(confidence, 0.0), 1.0)
```

### 阶段三：完善可追溯性 (3-4个月)

#### 3.1 端到端请求追踪
```python
# 请求生命周期追踪
class RequestTracker:
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = datetime.now()
        self.phases = []
        self.metadata = {}
    
    def start_phase(self, phase_name: str, metadata: dict = None):
        phase = {
            "name": phase_name,
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None,
            "metadata": metadata or {},
            "status": "running"
        }
        self.phases.append(phase)
        return len(self.phases) - 1
    
    def end_phase(self, phase_index: int, status: str = "completed", metadata: dict = None):
        if phase_index < len(self.phases):
            phase = self.phases[phase_index]
            phase["end_time"] = datetime.now()
            phase["duration"] = (phase["end_time"] - phase["start_time"]).total_seconds()
            phase["status"] = status
            if metadata:
                phase["metadata"].update(metadata)
```

#### 3.2 数据血缘关系追踪
```python
# 数据流向追踪
class DataLineageTracker:
    def __init__(self):
        self.lineage_graph = {}
    
    def record_data_transformation(self, 
                                 source_id: str, 
                                 target_id: str, 
                                 transformation_type: str,
                                 metadata: dict):
        """记录数据转换关系"""
        if source_id not in self.lineage_graph:
            self.lineage_graph[source_id] = {"downstream": [], "upstream": []}
        if target_id not in self.lineage_graph:
            self.lineage_graph[target_id] = {"downstream": [], "upstream": []}
        
        transformation = {
            "target": target_id,
            "type": transformation_type,
            "timestamp": datetime.now(),
            "metadata": metadata
        }
        
        self.lineage_graph[source_id]["downstream"].append(transformation)
        self.lineage_graph[target_id]["upstream"].append({
            "source": source_id,
            **transformation
        })
    
    def get_data_lineage(self, data_id: str, direction: str = "both"):
        """获取数据血缘关系"""
        if data_id not in self.lineage_graph:
            return None
        
        lineage = self.lineage_graph[data_id]
        if direction == "upstream":
            return lineage["upstream"]
        elif direction == "downstream":
            return lineage["downstream"]
        else:
            return lineage
```

#### 3.3 审计日志系统
```python
# 审计日志记录
class AuditLogger:
    def __init__(self, storage_backend: str = "database"):
        self.storage_backend = storage_backend
    
    async def log_action(self, 
                        user_id: str,
                        action_type: str,
                        resource_type: str,
                        resource_id: str,
                        details: dict,
                        result: str):
        """记录用户操作审计日志"""
        audit_record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "result": result,
            "ip_address": self._get_client_ip(),
            "user_agent": self._get_user_agent()
        }
        
        await self._store_audit_record(audit_record)
    
    async def query_audit_logs(self, 
                              filters: dict,
                              start_time: datetime = None,
                              end_time: datetime = None):
        """查询审计日志"""
        # 实现审计日志查询逻辑
        pass
```

## 🎯 实施优先级

### 高优先级 (立即实施)
1. **性能监控指标收集** - 基础可观测性
2. **决策过程日志增强** - 提升可解释性
3. **端到端请求ID追踪** - 基础可追溯性

### 中优先级 (3个月内)
1. **分布式追踪系统** - 完整链路追踪
2. **置信度评估机制** - 决策质量评估
3. **数据血缘关系** - 数据流向追踪

### 低优先级 (6个月内)
1. **可视化仪表板** - 用户友好的展示
2. **反事实解释** - 高级可解释性
3. **合规性审计** - 企业级需求

## 📈 成功指标

### 可观测性指标
- 系统可用性 > 99.9%
- 平均响应时间 < 2秒
- 错误率 < 0.1%
- 监控覆盖率 > 95%

### 可解释性指标
- 决策过程记录完整性 > 90%
- 用户满意度评分 > 4.0/5.0
- 决策置信度准确性 > 85%

### 可追溯性指标
- 请求追踪覆盖率 100%
- 审计日志完整性 > 99%
- 数据血缘关系准确性 > 95%

## 🛠️ 技术实现方案

### 1. 可观测性技术栈

#### 监控基础设施
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

#### 指标收集实现
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time

class AgentMetrics:
    def __init__(self):
        # 请求指标
        self.requests_total = Counter(
            'agent_requests_total',
            'Total agent requests',
            ['agent_id', 'user_id', 'status', 'model']
        )

        # 延迟指标
        self.request_duration = Histogram(
            'agent_request_duration_seconds',
            'Agent request duration',
            ['agent_id', 'phase'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        # 资源使用指标
        self.active_sessions = Gauge(
            'agent_active_sessions',
            'Number of active user sessions'
        )

        # Token使用指标
        self.token_usage = Counter(
            'llm_tokens_total',
            'Total LLM tokens consumed',
            ['model', 'type', 'agent_id']
        )

        # 系统信息
        self.system_info = Info(
            'agent_system_info',
            'System information'
        )

    def track_request(self, agent_id: str, user_id: str, model: str):
        """装饰器：追踪请求指标"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    duration = time.time() - start_time
                    self.requests_total.labels(
                        agent_id=agent_id,
                        user_id=user_id,
                        status=status,
                        model=model
                    ).inc()

                    self.request_duration.labels(
                        agent_id=agent_id,
                        phase="total"
                    ).observe(duration)

            return wrapper
        return decorator

# 全局指标实例
metrics = AgentMetrics()
```

### 2. 可解释性技术实现

#### 决策追踪框架
```python
# src/explainability/decision_tracker.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

@dataclass
class DecisionStep:
    step_id: str
    step_type: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DecisionTrace:
    trace_id: str
    agent_id: str
    user_id: str
    request_id: str
    steps: List[DecisionStep] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    final_decision: Optional[Dict[str, Any]] = None

class DecisionTracker:
    def __init__(self):
        self.active_traces: Dict[str, DecisionTrace] = {}

    def start_trace(self, trace_id: str, agent_id: str, user_id: str, request_id: str) -> DecisionTrace:
        """开始决策追踪"""
        trace = DecisionTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            user_id=user_id,
            request_id=request_id
        )
        self.active_traces[trace_id] = trace
        return trace

    def add_step(self, trace_id: str, step: DecisionStep):
        """添加决策步骤"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id].steps.append(step)

    def end_trace(self, trace_id: str, final_decision: Dict[str, Any]):
        """结束决策追踪"""
        if trace_id in self.active_traces:
            trace = self.active_traces[trace_id]
            trace.end_time = datetime.now()
            trace.final_decision = final_decision

            # 保存到存储
            self._save_trace(trace)

            # 清理内存
            del self.active_traces[trace_id]

    def _save_trace(self, trace: DecisionTrace):
        """保存决策追踪到存储"""
        # 实现存储逻辑（数据库、文件等）
        pass

# 全局决策追踪器
decision_tracker = DecisionTracker()
```

#### 推理过程记录
```python
# src/explainability/reasoning_recorder.py
class ReasoningRecorder:
    def __init__(self):
        self.recordings = {}

    async def record_llm_interaction(self,
                                   interaction_id: str,
                                   model_name: str,
                                   input_messages: List[Any],
                                   output_message: Any,
                                   config: Dict[str, Any]):
        """记录LLM交互详情"""
        recording = {
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "input": {
                "messages": [self._serialize_message(msg) for msg in input_messages],
                "config": config
            },
            "output": {
                "content": output_message.content,
                "tool_calls": getattr(output_message, 'tool_calls', []),
                "usage_metadata": getattr(output_message, 'usage_metadata', {})
            },
            "reasoning_analysis": await self._analyze_reasoning(input_messages, output_message)
        }

        self.recordings[interaction_id] = recording
        await self._store_recording(recording)

    async def _analyze_reasoning(self, input_messages: List[Any], output_message: Any) -> Dict[str, Any]:
        """分析推理过程"""
        analysis = {
            "input_complexity": self._assess_input_complexity(input_messages),
            "output_confidence": self._assess_output_confidence(output_message),
            "reasoning_chain": self._extract_reasoning_chain(output_message),
            "decision_factors": self._identify_decision_factors(input_messages, output_message)
        }
        return analysis

    def _assess_input_complexity(self, messages: List[Any]) -> float:
        """评估输入复杂度"""
        total_length = sum(len(str(msg.content)) for msg in messages)
        complexity_score = min(total_length / 1000, 1.0)  # 标准化到0-1
        return complexity_score

    def _assess_output_confidence(self, message: Any) -> float:
        """评估输出置信度"""
        # 基于输出长度、工具调用数量等因素评估
        content_length = len(str(message.content))
        tool_calls_count = len(getattr(message, 'tool_calls', []))

        # 简单的置信度计算逻辑
        confidence = 0.5 + (content_length / 2000) * 0.3 + (tool_calls_count > 0) * 0.2
        return min(confidence, 1.0)
```

### 3. 可追溯性技术实现

#### 分布式追踪集成
```python
# src/tracing/tracer.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

class TracingManager:
    def __init__(self, service_name: str = "agent-service-toolkit"):
        self.service_name = service_name
        self.tracer_provider = None
        self.tracer = None
        self._setup_tracing()

    def _setup_tracing(self):
        """设置分布式追踪"""
        # 配置追踪提供者
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)

        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=14268,
        )

        # 添加批处理span处理器
        span_processor = BatchSpanProcessor(jaeger_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        # 获取追踪器
        self.tracer = trace.get_tracer(self.service_name)

        # 自动仪表化
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor.instrument()

    def trace_agent_execution(self, agent_id: str, user_id: str):
        """Agent执行追踪装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(
                    f"agent_execution_{agent_id}",
                    attributes={
                        "agent.id": agent_id,
                        "user.id": user_id,
                        "service.name": self.service_name
                    }
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("execution.status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("execution.status", "error")
                        span.set_attribute("error.message", str(e))
                        span.record_exception(e)
                        raise
            return wrapper
        return decorator

# 全局追踪管理器
tracing_manager = TracingManager()
```

#### 审计日志实现
```python
# src/auditing/audit_logger.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json

class AuditEventType(Enum):
    USER_LOGIN = "user_login"
    AGENT_INVOCATION = "agent_invocation"
    TOOL_EXECUTION = "tool_execution"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class AuditEvent:
    event_id: str
    event_type: AuditEventType
    user_id: str
    timestamp: datetime
    resource_type: str
    resource_id: str
    action: str
    result: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

class AuditLogger:
    def __init__(self, storage_backend: str = "database"):
        self.storage_backend = storage_backend

    async def log_event(self, event: AuditEvent):
        """记录审计事件"""
        # 序列化事件
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "result": event.result,
            "details": json.dumps(event.details),
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "session_id": event.session_id
        }

        # 存储到后端
        await self._store_event(event_data)

        # 实时告警检查
        await self._check_alerts(event)

    async def _store_event(self, event_data: Dict[str, Any]):
        """存储审计事件"""
        if self.storage_backend == "database":
            # 存储到数据库
            pass
        elif self.storage_backend == "elasticsearch":
            # 存储到Elasticsearch
            pass

    async def _check_alerts(self, event: AuditEvent):
        """检查是否需要告警"""
        # 实现告警逻辑
        if event.event_type == AuditEventType.ERROR_OCCURRED:
            # 错误事件告警
            pass
        elif event.result == "failure":
            # 失败操作告警
            pass

# 全局审计日志器
audit_logger = AuditLogger()
```

## 🔧 集成示例

### Agent执行完整追踪示例
```python
# src/agents/traced_sql_agent.py
from uuid import uuid4
from src.monitoring.metrics import metrics
from src.explainability.decision_tracker import decision_tracker
from src.tracing.tracer import tracing_manager
from src.auditing.audit_logger import audit_logger, AuditEvent, AuditEventType

@metrics.track_request("sql_agent", "user_123", "deepseek-chat")
@tracing_manager.trace_agent_execution("sql_agent", "user_123")
async def enhanced_sql_agent_execution(state: SQLAgentState, config: RunnableConfig):
    """增强的SQL Agent执行，包含完整的可观测性"""

    # 生成追踪ID
    trace_id = str(uuid4())
    request_id = config.get("request_id", str(uuid4()))
    user_id = config["configurable"]["user_id"]

    # 开始决策追踪
    decision_trace = decision_tracker.start_trace(
        trace_id=trace_id,
        agent_id="sql_agent",
        user_id=user_id,
        request_id=request_id
    )

    # 记录审计事件
    await audit_logger.log_event(AuditEvent(
        event_id=str(uuid4()),
        event_type=AuditEventType.AGENT_INVOCATION,
        user_id=user_id,
        timestamp=datetime.now(),
        resource_type="agent",
        resource_id="sql_agent",
        action="execute",
        result="started",
        details={"trace_id": trace_id, "request_id": request_id}
    ))

    try:
        # 执行原有的SQL Agent逻辑
        result = await original_sql_agent_execution(state, config)

        # 结束决策追踪
        decision_tracker.end_trace(trace_id, {
            "final_result": "success",
            "output_messages": len(result.get("messages", []))
        })

        # 记录成功审计事件
        await audit_logger.log_event(AuditEvent(
            event_id=str(uuid4()),
            event_type=AuditEventType.AGENT_INVOCATION,
            user_id=user_id,
            timestamp=datetime.now(),
            resource_type="agent",
            resource_id="sql_agent",
            action="execute",
            result="success",
            details={"trace_id": trace_id, "output_length": len(str(result))}
        ))

        return result

    except Exception as e:
        # 记录错误审计事件
        await audit_logger.log_event(AuditEvent(
            event_id=str(uuid4()),
            event_type=AuditEventType.ERROR_OCCURRED,
            user_id=user_id,
            timestamp=datetime.now(),
            resource_type="agent",
            resource_id="sql_agent",
            action="execute",
            result="error",
            details={"trace_id": trace_id, "error": str(e)}
        ))

        raise
```

---

*本文档为AI Native项目的可观测性、可解释性和可追溯性提供全面的设计指导和实施路线图。*
