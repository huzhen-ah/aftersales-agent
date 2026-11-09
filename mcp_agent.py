#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 09:40:41 2026

@author: huzhen
"""

import os
import asyncio
from storage_engine_service import get_storage_engine
from session_service import SessionService
from memory_service import MemoryService
from model_service import CredentialService, ModelService
from toolkit_service import ToolkitService

from assistant import Assistant
from openai import APITimeoutError, APIConnectionError, APIStatusError
from sqlalchemy.exc import OperationalError
from tracing_service import setup_tracing


from agent_config import (
    base_url,
    model_name,
    user_id,
    agent_id,
    session_id,
    agent_name,
    session_name,
    system_prompt,
    mcp_name,
    mcp_config,
    mcp_client,
    tools,
    mcps,
    skills,
    review_tools,
    tool_name_2_permision_rules,
    reply_timeout,
    react_config,
    model_client_kwargs,
    tool_call_max_counts,
)


async def main():
    api_key = os.getenv("DEEPSEEK_API_KEY") or input("请输入DEEPSEEK_API_KEY:")
    
    storage, engine = await get_storage_engine() 
    memory_service = None
    assistant = None
    tracing_provider = setup_tracing()
    
    try:
        async with storage:
            session_service = SessionService(storage)
            memory_service = MemoryService(api_key)
            credential_service = CredentialService(storage)
            model_service = ModelService(api_key, base_url, model_name, credential_service, model_client_kwargs)
            toolkit_service = ToolkitService(tools, mcps, skills)
            assistant = Assistant(
                user_id = user_id,
                agent_id = agent_id,
                session_id = session_id,
                agent_name = agent_name, 
                session_name = session_name,
                system_prompt = system_prompt, 
                session_service = session_service, 
                memory_service = memory_service, 
                model_service = model_service, 
                toolkit_service = toolkit_service,
                tool_name_2_permision_rules = tool_name_2_permision_rules,
                react_config = react_config,
                tool_call_max_counts = tool_call_max_counts,
                storage = storage, 
                engine = engine
            )
            
            while True:
                question = await asyncio.to_thread(input,"我:")
                question = question.strip()
                if question == "/exit":
                    break
                try:
                    async with asyncio.timeout(reply_timeout):
                        reply = await assistant.reply(question)
                except TimeoutError:
                    print("助手：本次处理超过时间限制，请稍后重试: ")
                    continue
                except APITimeoutError as api_timeout_error:
                    print("api_timeout_error: ", api_timeout_error)
                    continue
                except APIConnectionError as api_connection_error:
                    print("api_connection_error: ", api_connection_error)
                    continue
                except APIStatusError as api_status_error:
                    print("api_status_error: ", api_status_error.status_code)
                    continue
                except OperationalError as error:
                    print("数据库操作失败，本轮会话状态未确认保存：", error)
                    continue
                if reply["dialog"]:
                    print("助手: ", reply["reply"].get_text_content())
                else:
                    break
            
    finally:
        tracing_provider.shutdown()
        if memory_service:
            memory_service.memory_client.close()
        await engine.dispose()
        
        print("数据库连接池资源已释放")
        
                            
                    
            
        
if __name__ == "__main__":
    asyncio.run(main())




