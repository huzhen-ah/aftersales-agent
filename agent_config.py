"""终端和网页入口共用的 Agent 配置；此文件不打开数据库、不读取终端输入。"""

from agentscope.mcp import MCPClient, HttpMCPConfig
from agentscope.permission import PermissionRule, PermissionBehavior
from agentscope.agent import ReActConfig

base_url = "https://api.deepseek.com"
model_name = "deepseek-flash"
#user_id, agent_id, session_id, agent_name, session_name, system_prompt, model, toolkit, middlewares, storage, engine
user_id = "hz_001"
agent_id = "agent_001"
session_id = None
agent_name = "售后故障咨询agent"
session_name = "售后电器故障咨询session"

system_prompt = (
    "你是家电售后坐席助手。"
    "根据用户任务和可用 Skill 的描述，判断是否存在适用的 Skill；"
    "存在时先读取完整说明，并按照其中的流程处理。"
    "处理过程中，根据需要调用工具。"
    "没有适用 Skill 时，根据任务需要和工具说明处理。"
    "缺少必要信息时向用户询问，不编造资料或工具结果。"
)



mcp_name = "aftersales_mcp"
mcp_config = HttpMCPConfig(url="http://127.0.0.1:8000/mcp_hz", timeout=130)

mcp_client = MCPClient(
    name=mcp_name,
    mcp_config=mcp_config,
    is_stateful=False
)

tools = []
mcps = [mcp_client]
skills = ["./skills/fault-triage"]



review_tools = [
    "mcp__aftersales_mcp__search_fault_knowledge",
]

tool_name_2_permision_rules = {}
for tool_name in review_tools:
    tool_name_2_permision_rules[tool_name] = [
        PermissionRule(
            tool_name=tool_name,
            rule_content=None,
            behavior=PermissionBehavior.ASK,
            source="userSettings",
        )
    ]

reply_timeout = 120
react_config = ReActConfig(
    max_iters=8,
    interruption_raise_cancelled_error=True
)
model_client_kwargs = {
    "timeout" : 60,
    "max_retries" : 2
}

tool_call_max_counts = 2

