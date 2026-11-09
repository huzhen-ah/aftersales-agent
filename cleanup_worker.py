#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 10:51:47 2026

@author: huzhen
"""

from datetime import datetime, timedelta, timezone
from storage_engine_service import get_storage_engine
from session_service import SessionService
from memory_service import MemoryService
import asyncio
from apscheduler.schedulers.blocking import BlockingScheduler
import os

llm_api_key = os.getenv("DEEPSEEK_API_KEY") or input("请输入DEEPSEEK_API_KEY:").strip()


async def cleanup_sessions_once():
    storage, engine = await get_storage_engine()
    try:
        async with storage:
            session_service = SessionService(storage)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cutoff_time = now - timedelta(days=3)
            print("开始sessions清理，截止时间：", cutoff_time)
            await session_service.delete_sessions(engine, cutoff_time)
            print("本批sessions清理结束")
    finally:
        await engine.dispose()

def run_session_cleanup():
    asyncio.run(cleanup_sessions_once())
    
async def cleanup_users_once():
    storage, engine = await get_storage_engine()
    memory_service = None
    try:
        memory_service = MemoryService(llm_api_key)
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff_time = now - timedelta(days=7)
        print("开始users清理，截止时间：", cutoff_time)
        await memory_service.delete_memories(engine, cutoff_time)
        print("本批user清理结束")
    finally:
        if memory_service:
            memory_service.memory_client.close()
        await engine.dispose()
        
def run_users_cleanup():
    asyncio.run(cleanup_users_once())
    
    
if __name__ == "__main__":
    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_session_cleanup,
        trigger="interval",
        minutes=1,
        next_run_time=datetime.now(timezone.utc),
        max_instances=1,
        coalesce=True,
    )
    
    scheduler.add_job(
        run_users_cleanup,
        trigger="interval",
        minutes=10,
        next_run_time=datetime.now(timezone.utc),
        max_instances=1,
        coalesce=True,
        
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown(wait=True)
