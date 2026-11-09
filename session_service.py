#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 15:57:53 2026

@author: huzhen
"""


import asyncio

from agentscope.app.storage import SessionConfig, ChatModelConfig
from uuid import uuid4
from sqlalchemy import text


class SessionService:
    def __init__(self, storage):
        self.storage = storage
        self.lock_prefix = "aftersales:session:"
        
    async def create_session(self, user_id, agent_id, session_name, chat_model_config, state):
        workspace_id = f"workspace:{user_id}:{agent_id}:{uuid4().hex}"
        session_config = SessionConfig(workspace_id=workspace_id, name=session_name, chat_model_config=chat_model_config)
        session = await self.storage.upsert_session(
            user_id = user_id,
            agent_id = agent_id,
            session_id = state.session_id,
            config = session_config,
            state = state
        )
        return session
    
    async def load_session(self, user_id, agent_id, session_id):
        session = await self.storage.get_session(
            user_id = user_id, 
            agent_id = agent_id, 
            session_id = session_id
        )
        if session and session.agent_id != agent_id:
            return None
        return session
    
    async def save_session(self, user_id, agent_id, session_config, state):
        await self.storage.upsert_session(
            user_id = user_id,
            agent_id = agent_id,
            session_id = state.session_id,
            config = session_config,
            state = state
        )
        
    async def delete_session(self, user_id, agent_id, session_id, cutoff_time=None):
        session = await self.load_session(user_id, agent_id, session_id)
        if session is None or session.agent_id != agent_id:
            return False
        
        if cutoff_time is not None and session.updated_at > cutoff_time:
            return False
        
        deleted = await self.storage.delete_session(
            user_id = user_id, 
            agent_id = agent_id, 
            session_id = session_id
        )
        return deleted
    
    
    async def acquire_lock(self, session_id, connection):
        lock_name = self.lock_prefix + f"{session_id}"
        sql = text(
            "SELECT pg_try_advisory_lock(hashtextextended(:lock_name, 0))"
        )
        result = await connection.execute(
            sql,
            {"lock_name":lock_name}
        )
        acquired = result.scalar()
        return acquired
    
    async def release_lock(self, session_id, connection):
        lock_name = self.lock_prefix + f"{session_id}"
        release_sql = text(
            "SELECT pg_advisory_unlock(hashtextextended(:lock_name, 0))"
        )
        result = await connection.execute(
            release_sql,
            {"lock_name": lock_name},
        )
        released = result.scalar()
        return released
    
    async def find_expired_sessions(self, engine, cutoff_time):
        sql = text(
            """
                select id, user_id, agent_id
                from sessions
                where updated_at <= :cutoff_time
                order by updated_at, id
                limit 100
            """
        )
        parameters = {
            "cutoff_time" : cutoff_time
        }
        
        async with engine.connect() as connection:
            result = await connection.execute(sql, parameters)
            rows = result.all()
        ret = []
        for row in rows:
            session_id, user_id, agent_id = row
            sub = {
                    "session_id" : session_id,
                    "user_id" : user_id,
                    "agent_id" : agent_id
                  }
            ret.append(sub)
        return ret
    
    async def delete_sessions(self, engine, cutoff_time):
        ret = await self.find_expired_sessions(engine, cutoff_time)
        for sub in ret:
            session_id = sub["session_id"]
            user_id = sub["user_id"]
            agent_id = sub["agent_id"]
            async with engine.connect() as connection:
                acquired = await self.acquire_lock(session_id, connection)
                if acquired:
                    try:
                        await self.delete_session(user_id, agent_id, session_id, cutoff_time)
                    finally:
                        await self.release_lock(session_id, connection)
                
        
    
    
    

if __name__ == "__main__":
    asyncio.run(get_storage_engine())
