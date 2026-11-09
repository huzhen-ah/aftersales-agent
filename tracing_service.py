#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 23:25:34 2026

@author: huzhen
"""
import base64
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter




def get_langfuse_connection():
    # 供采集器和本地体验入口共用连接配置，密钥只留在服务端。
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if not public_key or not secret_key:
        raise RuntimeError("请先填写 start_aftersales.sh 中的 Langfuse 密钥，再通过脚本启动。")

    # Langfuse 使用 Basic Auth：将“公钥:私钥”进行 Base64 编码。
    credentials = f"{public_key}:{secret_key}"
    auth_token = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("ascii")
    
    # HTTP 请求头：认证信息，以及 Langfuse v4 接收模式。
    headers = {
        "Authorization": f"Basic {auth_token}",
        "x-langfuse-ingestion-version": "4",
    }
    
    return "http://127.0.0.1:13000", headers


def setup_tracing():
    # 提供 Tracer，并管理采集配置。
    provider = TracerProvider()

    base_url, headers = get_langfuse_connection()

    # 将 Span 发送到本机 Langfuse 的轨迹接收接口。
    exporter = OTLPSpanExporter(
        endpoint=f"{base_url}/api/public/otel/v1/traces",
        headers=headers,
    )

    # 在后台分批处理已经结束的 Span。
    processor = BatchSpanProcessor(exporter)

    # 把处理器注册到 provider。
    provider.add_span_processor(processor)

    # 供 AgentScope 的轨迹中间件获取 Tracer。
    trace.set_tracer_provider(provider)
    

    return provider