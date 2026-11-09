#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 16:03:26 2026

@author: huzhen
"""

from agentscope.middleware import MiddlewareBase
from agentscope.permission import PermissionBehavior, PermissionDecision
import json

class ToolCallLimitMiddleware(MiddlewareBase):
    def __init__(self, max_calls):
        self.max_calls = max_calls
        
    async def on_check_permission(self, agent, input_kwargs, next_handler):
        decision = await next_handler(**input_kwargs)
        if decision.behavior != PermissionBehavior.ALLOW:
            return decision
        
        counter = agent.state.middle_context.setdefault("tool_call_limit", {})
        
        if counter.get("reply_id") != agent.state.reply_id:
            counter["reply_id"] = agent.state.reply_id
            counter["counts"] = {}
            
        call_key = json.dumps(
            {
                "name" : input_kwargs["tool"].name,
                "args" : input_kwargs["tool_input"]
            },
            sort_keys=True,
            ensure_ascii=False 
        )
        
        count = counter["counts"].get(call_key, 0)
        if count >= self.max_calls:
            return PermissionDecision(
                behavior = PermissionBehavior.DENY,
                message = "本轮相同工具、相同参数的调用已达到次数限制。请使用已有结果；如无法完成，请说明原因。"
            )
        
        counter["counts"][call_key] = count + 1
        return decision
            