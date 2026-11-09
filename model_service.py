#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 21:20:03 2026

@author: huzhen
"""
import os
from agentscope.credential import OpenAICredential
from agentscope.model import OpenAIChatModel
from agentscope.credential import CredentialFactory
from agentscope.app.storage import ChatModelConfig

class CredentialService:
    def __init__(self, storage):
        self.storage = storage
        
    async def save_credential(self, user_id, model_credential):
        credential_id = await self.storage.upsert_credential(
            user_id = user_id,
            credential_data = model_credential
        )
        return credential_id
    
    async def load_credential(self, user_id, credential_id):
        return await self.storage.get_credential(
            user_id = user_id,
            credential_id = credential_id
        )
        
class ModelService:
    def __init__(self, api_key, base_url, model_name, credential_service, client_kwargs):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or input("请输入DEEPSEEK_API_KEY:")
        self.base_url = base_url
        self.model_name = model_name
        self.credential_service = credential_service
        self.client_kwargs = client_kwargs
        
    async def build_default_model(self, user_id):
        model_credential = OpenAICredential(api_key=self.api_key, base_url=self.base_url)
        model = OpenAIChatModel(
            credential = model_credential,
            model = self.model_name,
            max_retries=0,
            client_kwargs = self.client_kwargs,
            extra_body = {"thinking":{"type":"disabled"}}
        )
        credential_id = await self.credential_service.save_credential(user_id, model_credential)
        chat_model_config = ChatModelConfig(
            type="openai_chat",
            credential_id=credential_id,   # 保存凭证后返回的 ID
            model=self.model_name,
            parameters={},
        )
        return model, chat_model_config
    
    async def build_model(self, user_id, chat_model_config):
        credential_record = await self.credential_service.load_credential(user_id, chat_model_config.credential_id)
        model_credential = CredentialFactory.from_dict(credential_record.data)
        model_class = model_credential.get_chat_model_class()
        model = model_class(
            credential = model_credential,
            model = chat_model_config.model,
            max_retries = 0,
            client_kwargs = self.client_kwargs,
            extra_body = {"thinking":{"type":"disabled"}},
            parameters=model_class.Parameters(
                **chat_model_config.parameters
            )
        )
        return model
    
    
        
        
    
    
        
        