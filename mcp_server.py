#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 21:25:11 2026

@author: huzhen
"""

from contextlib import asynccontextmanager
import httpx
from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware.error_handling import RetryMiddleware
from json import JSONDecodeError
from pydantic import BaseModel, ValidationError




class RetryableToolError(ToolError):
    pass

class FaultDocument(BaseModel):
    record_id: str
    content: str
    attributes: dict

class RetrieveResult(BaseModel):
    documents: list[FaultDocument]
    
    
    
@asynccontextmanager
async def manage_httpx_client(server: FastMCP):
    async with httpx.AsyncClient() as client:
        yield {"httpx_client":client}
        
        
        
        
mcp = FastMCP(
    name = "售后故障MCP_Server",
    lifespan = manage_httpx_client  
)


mcp.add_middleware(
    RetryMiddleware(
        max_retries=1,
        base_delay=1,
        retry_exceptions=(
            httpx.TimeoutException,
            httpx.ConnectError,
            RetryableToolError
        )
    )
)



@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def search_fault_knowledge(question: str, ctx: Context):
    resources = ctx.request_context.lifespan_context
    client = resources["httpx_client"]
    url = "http://127.0.0.1:8080/retrieve"

    # 指定问题及目标知识库；这里的 user_id 是传给 RAG 的固定配置。
    payload = {
        "question": question,
        "user_id": "user-001",
        "knowledge_base_id": "kb-fault-codes",
    }

    # 等待 RAG 检索结果，单次请求超时为 120 秒。
    try:
        response = await client.post(
            url,
            json=payload,
            timeout=3,
        )
        # HTTP 错误直接抛出，避免把检索服务故障当成“没有查到资料”。
        response.raise_for_status()
    except httpx.TimeoutException as error:
        print("RAG 请求超时：", repr(error))
        raise ToolError(
            "故障知识检索超时，本次查询失败，无法确认是否有适用资料。"
        ) from error
    except httpx.RequestError as error:
        print("RAG 请求失败：", repr(error))
        raise ToolError(
            "故障知识检索请求失败，本次未能取得检索结果。"
        ) from error
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        print("status_code: ",status_code)
        if status_code in (401, 403):
            error_message = (
                "认证或权限错误。不要原样重试，"
                "应由服务维护人员检查凭证和权限。"
            )
        elif status_code in (400, 422):
            error_message = (
                "请求参数错误。不要原样重试，"
                "应检查发送给 RAG 接口的参数是否符合要求。"
            )
        elif status_code == 429:
            error_message = (
                "请求受到限流。不要连续调用，"
                "本次查询暂时无法完成。"
            )
        elif status_code in (502, 503, 504):
            error_message = (
                "检索服务或网关暂时异常。"
                "本次查询失败，不能据此判断没有适用资料。"
            )
            raise RetryableToolError(
                f"HTTP {status_code}：{error_message}"
            ) from error
        else:
            error_message = (
                "检索接口返回异常状态，具体原因尚未确认。"
                "不要猜测原因或连续重复调用。"
            )
        raise ToolError(
            f"HTTP {status_code}：{error_message}"
        ) from error

    # 返回原始 JSON；MCP SDK 和 AgentScope 适配层负责后续协议消息包装。
    try:
        result = response.json()
        RetrieveResult.model_validate(result, strict=True)
    except JSONDecodeError as error:
        raise ToolError("检索服务返回的信息无法被解析为json,本次查询失败") from error
    except ValidationError as error:
        raise ToolError("检索服务返回的字段或类型不符合约定，本次查询失败") from error
    return result

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        path="/mcp_hz"
    )
    
    