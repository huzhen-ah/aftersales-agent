#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 22:40:54 2026

@author: huzhen
"""

from agentscope.tool import Toolkit


"""
mcp_name = "aftersales_mcp"
mcp_config = HttpMCPConfig(url="http://127.0.0.1:8000/mcp_hz", timeout=130)

mcp_client = MCPClient(
    name=mcp_name,
    mcp_config=mcp_config,
    is_stateful=False
)

skill_path = "./skills/fault-triage"


toolkit = Toolkit(mcps=[mcp_client], skills_or_loaders=[skill_path])    
"""
class ToolkitService:
    def __init__(self, tools, mcps, skills):
        self.tools = tools
        self.mcps = mcps
        self.skills = skills
        
    def build_toolkit(self):
        return Toolkit(tools=self.tools, skills_or_loaders=self.skills, mcps=self.mcps)
    

    

        