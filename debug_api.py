#!/usr/bin/env python3
"""
DeepSeek R1 API 连接测试脚本
用于验证 API 配置是否正确
"""

import asyncio
import os
import httpx
import json

# DeepSeek R1 配置
API_KEY = os.environ.get("API_KEY", "sk-48e606513d554bc9bbca0bb6dfa650d7")
API_BASE_URL = os.environ.get(
    "API_BASE_URL", "https://api.deepseek.com/v1/chat/completions"
)
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-reasoner")

async def test_api_connection():
    """测试 DeepSeek R1 API 连接"""
    
    if not API_KEY:
        print("❌ 错误：未设置 API_KEY 环境变量")
        print("请设置：export API_KEY='your_api_key_here'")
        return False
    
    print(f"🔧 配置信息：")
    print(f"   API Base URL: {API_BASE_URL}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   API Key: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY) > 12 else '***'}")
    print()
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user", 
                "content": "你好，请简单回复'测试成功'"
            }
        ],
        "max_tokens": 50
    }
    
    try:
        print("🔄 正在测试 API 连接...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                API_BASE_URL, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                print(f"✅ API 连接成功！")
                print(f"📝 回复内容: {content}")
                return True
            else:
                print("❌ API 响应格式异常")
                print(f"响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
                return False
                
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"错误详情: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 DeepSeek R1 API 连接测试")
    print("=" * 40)
    
    success = await test_api_connection()
    
    print("=" * 40)
    if success:
        print("🎉 配置正确！现在可以运行 test.py 进行完整测试")
    else:
        print("💡 请检查配置并重试")

if __name__ == "__main__":
    asyncio.run(main()) 