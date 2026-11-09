#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 09:28:07 2026

@author: huzhen
"""

import os
from mem0 import AsyncMemory
from agentscope.middleware import Mem0Middleware
import aiosqlite
from urllib.parse import unquote
from sqlalchemy import text

class MemoryService:
    def __init__(self, llm_api_key):
        self.memory_client = self.create_memory_client(llm_api_key)
        self.lock_prefix = "aftersales:memory:"
    
    async def delete_memories(self, engine, cutoff_time):
        user_ids = await self.find_expired_users(cutoff_time)
        if not user_ids:
            return
        for user_id in user_ids:
            async with engine.connect() as connection:
                acquired = await self.acquire_lock(user_id, connection)
                if acquired:
                    try:
                        if await self.is_user_expired(user_id, cutoff_time):
                            await self.memory_client.delete_all(user_id=user_id)
                    finally:
                        await self.release_lock(user_id, connection)
        
    def extract_user_id(self, scope):
        if not scope:
            return None
    
        for part in scope.split("&"):
            key, value = part.split("=", 1)
    
            if key == "user_id":
                return unquote(value)
    
        return None

    async def find_expired_users(self, cutoff_time):
        async with aiosqlite.connect(
            "file:./memory/mem0_history.db?mode=ro",
            uri=True,
        ) as connection:
    
            await connection.create_function(
                "extract_user_id", 1, self.extract_user_id,
            )
    
            sql = """
                SELECT extract_user_id(session_scope) AS user_id
                FROM messages
                GROUP BY user_id
                HAVING user_id IS NOT NULL
                   AND MAX(julianday(created_at)) <= julianday(:cutoff_time)
            """
    
            parameters = {"cutoff_time": cutoff_time.isoformat()}
    
            async with connection.execute(sql, parameters) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    
    async def is_user_expired(self, user_id, cutoff_time):
        async with aiosqlite.connect(
            "file:./memory/mem0_history.db?mode=ro",
            uri=True,
        ) as connection:
    
            await connection.create_function(
                "extract_user_id", 1, self.extract_user_id,
            )
    
            sql = """
                SELECT MAX(julianday(created_at)) <= julianday(:cutoff_time)
                FROM messages
                WHERE extract_user_id(session_scope) = :user_id
            """
    
            parameters = {
                "user_id": user_id,
                "cutoff_time": cutoff_time.isoformat(),
            }
    
            async with connection.execute(sql, parameters) as cursor:
                row = await cursor.fetchone()
                return row[0] == 1
        
    async def acquire_lock(self, user_id, connection):
        lock_name = self.lock_prefix + f"{user_id}"
        sql = text(
            "SELECT pg_try_advisory_lock(hashtextextended(:lock_name, 0))"
        )
        result = await connection.execute(
            sql,
            {"lock_name":lock_name}
        )
        acquired = result.scalar()
        return acquired
    
    async def release_lock(self, user_id, connection):
        lock_name = self.lock_prefix + f"{user_id}"
        release_sql = text(
            "SELECT pg_advisory_unlock(hashtextextended(:lock_name, 0))"
        )
        result = await connection.execute(
            release_sql,
            {"lock_name": lock_name},
        )
        released = result.scalar()
        return released
        
    def create_memory_client(self, llm_api_key):
        #llm配置，负责提取记忆，判断新旧记忆如何更新。
        llm_config = {
            "provider" : "deepseek",
            "config" : {
                "model" : "deepseek-flash",
                "api_key" : llm_api_key,
                "deepseek_base_url" : "https://api.deepseek.com"
            }
        }
    
        #负责把提取到的记忆文本转为向量
        embedder_config = {
            "provider" : "ollama",
            "config" : {
                "model" : "qwen3-embedding:0.6b",
                "embedding_dims" : 1024,
                "ollama_base_url" : "http://127.0.0.1:11434"
            }
        }
        
        #负责保存、检索记忆
        vector_store_config = {
            "provider" : "milvus",
            "config" : {
                "url" : "http://127.0.0.1:19530",
                "token" : "",
                "db_name" : "aftersales",
                "collection_name" : "aftersales_user_memory_v1",
                "embedding_model_dims" : 1024,
                "metric_type" : "COSINE"
            }
        }
        
        os.makedirs("./memory", exist_ok=True)
        history_path = "./memory/mem0_history.db"
        
        memory_config = {
            "llm" : llm_config,
            "embedder" : embedder_config,
            "vector_store" : vector_store_config,
            "history_db_path" : history_path,
            "custom_instructions" : "使用中文记录用户明确表达的稳定偏好和长期有效信息。不要把知识库内容、未经确认的推测或临时故障当成用户长期事实。"
        }
        
        memory_client = AsyncMemory.from_config(memory_config)
        return memory_client


    def create_memory_middleware(self, user_id, agent_id):
        memory_middleware = Mem0Middleware(
            client = self.memory_client,
            user_id = user_id,
            agent_id = agent_id,
            mode = "static_control",
            top_k = 3,
            await_write = True
        )
        return memory_middleware
