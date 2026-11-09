#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 21:20:30 2026

@author: huzhen
"""


from agentscope.app.storage import AsyncSQLAlchemyStorage
from sqlalchemy.ext.asyncio import create_async_engine


async def get_storage_engine():
    database_url = r"postgresql+asyncpg://aftersales_user:YOUR_DATABASE_PASSWORD@127.0.0.1:5432/aftersales_agent"
    engine = create_async_engine(database_url)
    storage = AsyncSQLAlchemyStorage(url=database_url, create_tables=True, engine=engine)
    return storage, engine

