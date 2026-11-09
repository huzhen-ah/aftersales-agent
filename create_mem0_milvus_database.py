#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 10:15:31 2026

@author: huzhen
"""

from pymilvus import MilvusClient

# 连接本机 Milvus。
client = MilvusClient(
    uri="http://127.0.0.1:19530",
    token="",
)

# 创建数据库。
client.create_database(db_name="aftersales")

# 列出数据库，确认创建结果。
print(client.list_databases())

client.close()