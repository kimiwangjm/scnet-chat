#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCNet Chat Skill - 查询SCNet账户信息

功能：
1. 获取SCNet账户的token列表
2. 查询账户余额

环境变量：
- SCNET_ACCESS_KEY: 访问密钥AK
- SCNET_SECRET_KEY: 密钥SK
- SCNET_USER: SCNet用户名
"""

import hmac
import hashlib
import requests
import json
import time
import os
import sys
from typing import Optional, Dict, Any


def escape_json(s: Optional[str]) -> str:
    """转义JSON字符串"""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def generate_signature(access_key: str, timestamp: str, user: str, secret_key: str) -> str:
    """
    生成HMAC-SHA256签名
    
    Args:
        access_key: AK
        timestamp: 时间戳（秒，字符串）
        user: 用户名
        secret_key: SK
    
    Returns:
        签名（小写十六进制字符串）
    """
    escaped_ak = escape_json(access_key)
    escaped_ts = escape_json(timestamp)
    escaped_user = escape_json(user)
    
    data_to_sign = f'{{"accessKey":"{escaped_ak}","timestamp":"{escaped_ts}","user":"{escaped_user}"}}'
    
    signature = hmac.new(
        key=secret_key.encode('utf-8'),
        msg=data_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return signature.lower()


def get_tokens(access_key: str, secret_key: str, user: str) -> Optional[Dict[str, Any]]:
    """
    获取SCNet用户token列表
    
    API: POST https://api.scnet.cn/api/user/v3/tokens
    
    Returns:
        成功返回JSON数据，失败返回None
    """
    timestamp = str(int(time.time()))
    signature = generate_signature(access_key, timestamp, user, secret_key)
    
    tokens_url = "https://api.scnet.cn/api/user/v3/tokens"
    headers = {
        "user": user,
        "accessKey": access_key,
        "signature": signature,
        "timestamp": timestamp
    }
    
    try:
        response = requests.post(tokens_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ 获取token失败: {e}", file=sys.stderr)
        return None


def get_user_info(token: str, cluster_id: str = "") -> Optional[Dict[str, Any]]:
    """
    获取SCNet用户信息（包含账户余额）
    
    尝试多个可能的API端点：
    1. https://api.scnet.cn/ac/openapi/v2/user
    2. https://api.scnet.cn/api/ac/openapi/v2/user
    3. 特定集群的API地址
    
    Args:
        token: 从get_tokens获取的token
        cluster_id: 集群ID（用于构造特定集群的API地址）
    
    Returns:
        成功返回JSON数据，失败返回None
    """
    # 尝试多个可能的API端点
    urls_to_try = [
        "https://www.scnet.cn/ac/openapi/v2/user",
        "https://api.scnet.cn/ac/openapi/v2/user",
    ]
    
    headers = {
        "token": token,
        "Content-Type": "application/json"
    }
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            continue
    
    print(f"❌ 获取用户信息失败: 所有API端点均不可用", file=sys.stderr)
    return None


def print_tokens(data: Dict[str, Any]) -> str:
    return_value = ""
    """格式化打印token列表"""
    if data.get("code") != "0":
        print(f"❌ API返回错误: {data.get('msg', '未知错误')}")
        return
    
    tokens = data.get("data", [])
    if not tokens:
        print("暂无token信息")
        return
    
    print(f"\n📋 获取到 {len(tokens)} 个token:\n")
    print("-" * 60)
    
    for i, token_info in enumerate(tokens, 1):
        cluster_name = token_info.get("clusterName", "未知")
        cluster_id = token_info.get("clusterId", "未知")
        # token_preview = token_info.get("token", "")[:30] + "..." if token_info.get("token") else "无"
        token_preview = token_info.get("token","未知")
        if cluster_name=='ac':
            return_value = token_info.get("token","未知")
        print(f"{i}. 计算中心: {cluster_name}")
        print(f"   集群ID: {cluster_id}")
        print(f"   Token: {token_preview}")
        print("-" * 60)
    return return_value

def print_user_info(data: Dict[str, Any]) -> None:
    """格式化打印用户信息"""
    if data.get("code") != "0":
        print(f"❌ API返回错误: {data.get('msg', '未知错误')}")
        return
    
    user_data = data.get("data", {})
    
    print("\n📊 账户信息:\n")
    print("-" * 40)
    print(f"用户名: {user_data.get('userName', '未知')}")
    print(f"全名: {user_data.get('fullName', '未知')}")
    print(f"账户名: {user_data.get('accountName', '未知')}")
    print(f"账户状态: {user_data.get('accountStatus', '未知')}")
    print(f"所属计算中心: {user_data.get('computerCenter', '未知')}")
    print(f"💰 账户余额: {user_data.get('accountBalance', '0.00')} 元")
    print("-" * 40)


def main():
    """主函数"""
    # 从环境变量读取配置
    access_key = os.environ.get("SCNET_ACCESS_KEY")
    secret_key = os.environ.get("SCNET_SECRET_KEY")
    user = os.environ.get("SCNET_USER")
    
    # 检查必要的环境变量
    if not all([access_key, secret_key, user]):
        print("❌ 错误: 缺少必要的环境变量", file=sys.stderr)
        print("\n请设置以下环境变量:", file=sys.stderr)
        print("  export SCNET_ACCESS_KEY=\"你的AK\"")
        print("  export SCNET_SECRET_KEY=\"你的SK\"")
        print("  export SCNET_USER=\"你的用户名\"")
        sys.exit(1)
    
    # 获取token列表
    print("🔑 正在获取token列表...")
    tokens_data = get_tokens(access_key, secret_key, user)
    
    if not tokens_data:
        sys.exit(1)
    
    token = print_tokens(tokens_data)
    print("AC账户的token:",token)
    print("\n💳 正在查询账户余额...")
    user_info = get_user_info(token)
    if user_info:
        print_user_info(user_info)


if __name__ == "__main__":
    main()
