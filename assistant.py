#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 16:27:42 2026

@author: huzhen
"""

from agentscope.agent import Agent
from agentscope.message import UserMsg
from agentscope.state import AgentState
import asyncio
from agentscope.middleware import MiddlewareBase, TracingMiddleware
from agentscope.permission import PermissionBehavior, PermissionDecision
from tool_call_limit import ToolCallLimitMiddleware




class HumanReviewMiddleware(MiddlewareBase):
    async def on_check_permission(self, agent, input_kwargs, next_handler):
        decision = await next_handler(**input_kwargs)
        if decision.behavior != PermissionBehavior.ASK:
            return decision
        
        tool = input_kwargs["tool"]
        print("tool.name to review: ",tool.name)
        print("tool.args: ", input_kwargs["tool_input"])
        
        answer = await asyncio.to_thread(
            input,
            "是否允许执行？输入 y 批准， 其余拒绝: "
        )
        approved = answer.strip().lower() == "y"
        
        permission_decision = PermissionDecision(
            behavior = PermissionBehavior.ALLOW if approved else PermissionBehavior.DENY,
            message = "用户批准执行" if approved else "用户拒绝执行"
        )

        return permission_decision
   

class Assistant:
    def __init__(self, 
                 user_id, 
                 agent_id, 
                 session_id, 
                 agent_name, 
                 session_name, 
                 system_prompt, 
                 session_service,
                 memory_service, 
                 model_service, 
                 toolkit_service, 
                 tool_name_2_permision_rules, 
                 react_config, 
                 tool_call_max_counts,
                 storage, 
                 engine
    ):
        self.user_id = user_id
        self.agent_id = agent_id
        self.session_id = session_id
        self.agent_name = agent_name
        self.session_name = session_name
        self.system_prompt = system_prompt
        self.session_service = session_service
        self.memory_service = memory_service
        self.model_service = model_service
        self.toolkit_service = toolkit_service
        self.tool_name_2_permision_rules = tool_name_2_permision_rules
        self.react_config = react_config
        self.tool_call_max_counts = tool_call_max_counts
        self.storage = storage
        self.engine = engine
        
    async def acquire_user_lock(self, connection):
        
        return await self.memory_service.acquire_lock(self.user_id, connection)
    
    async def release_user_lock(self, connection):
        return await self.memory_service.release_lock(self.user_id, connection)
        
    async def acquire_session_lock(self, connection):
        return await self.session_service.acquire_lock(self.session_id, connection)
    
    async def release_session_lock(self, connection):
        
        return await self.session_service.release_lock(self.session_id, connection)
            
    
    async def reply(self, question):
        async with self.engine.connect() as connection:
            user_lock_acquired = False
            session_lock_acquired = False
            model = None
            state = None
            try:
                user_lock_acquired = await self.acquire_user_lock(connection)
                if not user_lock_acquired:
                    print("用户正在使用")
                    return {"dialog": False, "reply": None}
                if self.session_id is None:
                    state = AgentState()
                    self.session_id = state.session_id
                
                session_lock_acquired = await self.acquire_session_lock(connection)
                if not session_lock_acquired:
                    print("session正在使用中")
                    return {"dialog": False, "reply": None}
                
                if state:
                    model, chat_model_config = await self.model_service.build_default_model(self.user_id)
                    
                    session = await self.session_service.create_session(self.user_id, self.agent_id, self.session_name, chat_model_config, state)
                else:
                    session = await self.session_service.load_session(self.user_id, self.agent_id, self.session_id)
                    if session is None:
                        print("获取不到session")
                        return {"dialog": False, "reply": None}
                if question == "/delete":
                    await self.session_service.delete_session(self.user_id, self.agent_id, self.session_id)
                    print("session已删除")
                    return {"dialog": False, "reply": None}
                
                if not model:
                
                    model = await self.model_service.build_model(self.user_id, session.config.chat_model_config)
                
                for tool_name in self.tool_name_2_permision_rules:
                    session.state.permission_context.ask_rules[tool_name] = self.tool_name_2_permision_rules[tool_name]
                agent = Agent(
                    name = self.agent_name,
                    system_prompt = self.system_prompt,
                    model = model,
                    toolkit = self.toolkit_service.build_toolkit(),
                    middlewares = [
                        TracingMiddleware(),
                        self.memory_service.create_memory_middleware(self.user_id, self.agent_id),
                        ToolCallLimitMiddleware(self.tool_call_max_counts),
                        HumanReviewMiddleware()
                    ],
                    state = session.state,
                    react_config = self.react_config
                )
                
                
                user_message = UserMsg(name="user", content=question)
                reply = await agent.reply(user_message)
                await self.session_service.save_session(self.user_id, self.agent_id, session.config, agent.state)
                return {"dialog":True,"reply":reply}
                
            finally:
                if session_lock_acquired:
                    await self.release_session_lock(connection)
                if user_lock_acquired:
                    await self.release_user_lock(connection)
                if model:
                    await model.client.close()
                    
    
    
        
        