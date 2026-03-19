#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCNet Chat Skill - 查询SCNet账户信息、作业信息和文件管理

功能：
1. 获取SCNet账户的token列表
2. 查询账户余额
3. 查询实时作业列表
4. 查询历史作业列表
5. 文件管理（列表、创建目录、上传、下载、删除等）
6. 作业管理（提交作业、删除作业、查询队列等）

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
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

# ============== 基础认证和通用方法 ==============

def escape_json(s: Optional[str]) -> str:
    """转义JSON字符串"""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def generate_signature(access_key: str, timestamp: str, user: str, secret_key: str) -> str:
    """生成HMAC-SHA256签名"""
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
    """获取SCNet用户token列表"""
    timestamp = str(int(time.time()))
    signature = generate_signature(access_key, timestamp, user, secret_key)
    tokens_url = "https://api.scnet.cn/api/user/v3/tokens"
    headers = {"user": user, "accessKey": access_key, "signature": signature, "timestamp": timestamp}
    try:
        response = requests.post(tokens_url, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 获取token失败: {e}")
        return None


def get_center_info(token: str) -> Optional[Dict[str, Any]]:
    """获取授权区域信息"""
    urls = ["https://www.scnet.cn/ac/openapi/v2/center", "https://api.scnet.cn/ac/openapi/v2/center"]
    headers = {"token": token, "Content-Type": "application/json"}
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    return None


def get_hpc_url(center_info: Dict[str, Any]) -> Optional[str]:
    """获取hpcUrl（作业服务地址）"""
    if center_info.get("code") != "0":
        return None
    data = center_info.get("data", {})
    for url_info in data.get("hpcUrls", []):
        if url_info.get("enable") == "true":
            return url_info.get("url")
    return None


def get_efile_url(center_info: Dict[str, Any]) -> Optional[str]:
    """获取efileUrl（文件服务地址）"""
    if center_info.get("code") != "0":
        return None
    data = center_info.get("data", {})
    for url_info in data.get("efileUrls", []):
        if url_info.get("enable") == "true":
            return url_info.get("url")
    return None


def get_home_path(center_info: Dict[str, Any]) -> Optional[str]:
    """获取用户家目录"""
    if center_info.get("code") != "0":
        return None
    data = center_info.get("data", {})
    return data.get("clusterUserInfo", {}).get("homePath")


def get_user_info(token: str) -> Optional[Dict[str, Any]]:
    """获取用户信息（包含账户余额）"""
    urls = ["https://www.scnet.cn/ac/openapi/v2/user", "https://api.scnet.cn/ac/openapi/v2/user"]
    headers = {"token": token, "Content-Type": "application/json"}
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    return None


# ============== 作业操作方法 ==============

def get_cluster_info(hpc_url: str, token: str) -> Optional[Dict[str, Any]]:
    """查询集群信息"""
    url = f"{hpc_url}/hpc/openapi/v2/cluster"
    headers = {"token": token, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.json()
    except:
        return None


def query_user_queues(hpc_url: str, token: str, username: str, scheduler_id: str) -> Optional[Dict[str, Any]]:
    """
    查询用户可访问队列
    
    API: GET /hpc/openapi/v2/queuenames/users/{username}
    """
    url = f"{hpc_url}/hpc/openapi/v2/queuenames/users/{username}"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"strJobManagerID": scheduler_id}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 查询队列失败: {e}")
        return None


def submit_job(hpc_url: str, token: str, scheduler_id: str, job_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    提交作业
    
    API: POST /hpc/openapi/v2/apptemplates/BASIC/BASE/job
    """
    url = f"{hpc_url}/hpc/openapi/v2/apptemplates/BASIC/BASE/job"
    headers = {"token": token, "Content-Type": "application/json"}
    
    # 构建请求体
    payload = {
        "strJobManagerID": scheduler_id,
        "mapAppJobInfo": {
            "GAP_CMD_FILE": job_config.get("cmd", "sleep 300"),
            "GAP_NNODE": str(job_config.get("nnodes", 1)),
            "GAP_NODE_STRING": job_config.get("node_string", ""),
            "GAP_SUBMIT_TYPE": job_config.get("submit_type", "cmd"),
            "GAP_JOB_NAME": job_config.get("job_name", "SCNetJob"),
            "GAP_WORK_DIR": job_config.get("work_dir", "~"),
            "GAP_QUEUE": job_config.get("queue", "debug"),
            "GAP_NPROC": str(job_config.get("nproc", 1)),
            "GAP_PPN": str(job_config.get("ppn", "")),
            "GAP_NGPU": str(job_config.get("ngpu", "")),
            "GAP_NDCU": str(job_config.get("ndcu", "")),
            "GAP_WALL_TIME": job_config.get("wall_time", "01:00:00"),
            "GAP_EXCLUSIVE": str(job_config.get("exclusive", "")),
            "GAP_APPNAME": job_config.get("appname", "BASE"),
            "GAP_MULTI_SUB": str(job_config.get("multi_sub", "")),
            "GAP_STD_OUT_FILE": job_config.get("stdout", f"{job_config.get('work_dir', '~')}/std.out.%j"),
            "GAP_STD_ERR_FILE": job_config.get("stderr", f"{job_config.get('work_dir', '~')}/std.err.%j"),
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 提交作业失败: {e}")
        return None


def delete_job(hpc_url: str, token: str, scheduler_id: str, username: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    删除作业
    
    API: DELETE /hpc/openapi/v2/jobs
    """
    url = f"{hpc_url}/hpc/openapi/v2/jobs"
    headers = {"token": token, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "jobMethod": "5",
        "strJobInfoMap": f"{scheduler_id},{username}:{job_id}:"
    }
    try:
        response = requests.delete(url, headers=headers, data=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 删除作业失败: {e}")
        return None


def query_job_detail(hpc_url: str, token: str, scheduler_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    查询作业详情
    
    API: GET /hpc/openapi/v2/jobs/{job_id}
    """
    url = f"{hpc_url}/hpc/openapi/v2/jobs/{job_id}"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"strJobManagerID": scheduler_id}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 查询作业详情失败: {e}")
        return None


def query_jobs(hpc_url: str, token: str, cluster_id: str, start: int = 0, limit: int = 100) -> Optional[Dict[str, Any]]:
    """查询实时作业列表"""
    url = f"{hpc_url}/hpc/openapi/v2/jobs"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"strClusterIDList": cluster_id, "start": start, "limit": limit}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    except:
        return None


def query_history_jobs(hpc_url: str, token: str, cluster_id: str, start_time: str, end_time: str,
                       start: int = 0, limit: int = 100) -> Optional[Dict[str, Any]]:
    """查询历史作业列表"""
    url = f"{hpc_url}/hpc/openapi/v2/historyjobs"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {
        "strClusterNameList": cluster_id,
        "startTime": start_time,
        "endTime": end_time,
        "timeType": "CUSTOM",
        "isQueryByQueueTime": "false",
        "start": start,
        "limit": limit
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    except:
        return None


# ============== 文件操作方法 ==============

def list_files(efile_url: str, token: str, path: Optional[str] = None, limit: int = 100) -> Optional[Dict[str, Any]]:
    """查询文件列表"""
    url = f"{efile_url}/openapi/v2/file/list"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"limit": limit, "start": 0, "order": "asc", "orderBy": "name"}
    if path:
        params["path"] = path
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.json()
    except:
        return None


def create_folder(efile_url: str, token: str, path: str, create_parents: bool = True) -> bool:
    """创建文件夹"""
    url = f"{efile_url}/openapi/v2/file/mkdir"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"path": path, "createParents": str(create_parents).lower()}
    try:
        response = requests.post(url, headers=headers, params=params, timeout=30)
        result = response.json()
        return result.get("code") == "0" or result.get("code") == "911021"
    except:
        return False


def create_file(efile_url: str, token: str, file_path: str) -> bool:
    """创建空文件"""
    url = f"{efile_url}/openapi/v2/file/touch"
    headers = {"token": token, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {"fileAbsolutePath": file_path}
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        result = response.json()
        return result.get("code") == "0" or result.get("code") == "911021"
    except:
        return False


def upload_file(efile_url: str, token: str, local_path: str, remote_path: str, cover: str = "cover") -> bool:
    """上传文件"""
    url = f"{efile_url}/openapi/v2/file/upload"
    headers = {"token": token}
    try:
        with open(local_path, 'rb') as f:
            files = {"file": (os.path.basename(local_path), f)}
            data = {"path": remote_path, "cover": cover}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=300)
            return response.json().get("code") == "0"
    except:
        return False


def download_file(efile_url: str, token: str, remote_path: str, local_path: str) -> bool:
    """下载文件"""
    url = f"{efile_url}/openapi/v2/file/download"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"path": remote_path}
    try:
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=300)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        return False
    except:
        return False


def delete_file(efile_url: str, token: str, path: str, recursive: bool = False) -> bool:
    """删除文件/文件夹"""
    url = f"{efile_url}/openapi/v2/file/remove"
    headers = {"token": token, "Content-Type": "application/json"}
    params = {"paths": path, "recursive": str(recursive).lower()}
    try:
        response = requests.post(url, headers=headers, params=params, timeout=30)
        return response.json().get("code") == "0"
    except:
        return False


def check_file_exists(efile_url: str, token: str, path: str) -> bool:
    """检查文件是否存在"""
    url = f"{efile_url}/openapi/v2/file/exist"
    headers = {"token": token, "Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(url, headers=headers, data={"path": path}, timeout=30)
        result = response.json()
        return result.get("code") == "0" and result.get("data", {}).get("exist", False)
    except:
        return False


# ============== SCNet客户端类 ==============

class SCNetClient:
    """SCNet统一客户端"""
    
    def __init__(self, access_key: str, secret_key: str, user: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.user = user
        self.tokens_data = None
        self._tokens_cache = {}
        self._center_info_cache = {}
        self._hpc_url_cache = {}
        self._efile_url_cache = {}
        self._home_path_cache = {}
    
    def init_tokens(self) -> bool:
        """初始化token列表"""
        self.tokens_data = get_tokens(self.access_key, self.secret_key, self.user)
        if self.tokens_data and self.tokens_data.get("code") == "0":
            for token_info in self.tokens_data.get("data", []):
                name = token_info.get("clusterName", "")
                self._tokens_cache[name] = token_info.get("token", "")
            return True
        return False
    
    def get_token(self, cluster_name: str) -> Optional[str]:
        """获取指定计算中心的token"""
        return self._tokens_cache.get(cluster_name)
    
    def _get_center_info(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """获取计算中心信息（带缓存）"""
        if cluster_name in self._center_info_cache:
            return self._center_info_cache[cluster_name]
        token = self.get_token(cluster_name)
        if not token:
            return None
        info = get_center_info(token)
        if info:
            self._center_info_cache[cluster_name] = info
        return info
    
    def get_hpc_url(self, cluster_name: str) -> Optional[str]:
        """获取hpcUrl（作业服务）"""
        if cluster_name in self._hpc_url_cache:
            return self._hpc_url_cache[cluster_name]
        info = self._get_center_info(cluster_name)
        url = get_hpc_url(info) if info else None
        if url:
            self._hpc_url_cache[cluster_name] = url
        return url
    
    def get_efile_url(self, cluster_name: str) -> Optional[str]:
        """获取efileUrl（文件服务）"""
        if cluster_name in self._efile_url_cache:
            return self._efile_url_cache[cluster_name]
        info = self._get_center_info(cluster_name)
        url = get_efile_url(info) if info else None
        if url:
            self._efile_url_cache[cluster_name] = url
        return url
    
    def get_home_path(self, cluster_name: str) -> Optional[str]:
        """获取家目录"""
        if cluster_name in self._home_path_cache:
            return self._home_path_cache[cluster_name]
        info = self._get_center_info(cluster_name)
        path = get_home_path(info) if info else None
        if path:
            self._home_path_cache[cluster_name] = path
        return path
    
    def find_cluster_by_name(self, name_hint: str) -> Optional[str]:
        """根据名称提示查找计算中心"""
        name_hint = name_hint.lower()
        for cluster_name in self._tokens_cache.keys():
            if name_hint in cluster_name.lower():
                return cluster_name
        return None
    
    def get_scheduler_id(self, cluster_name: str) -> Optional[str]:
        """获取调度器ID"""
        hpc_url = self.get_hpc_url(cluster_name)
        token = self.get_token(cluster_name)
        if not hpc_url or not token:
            return None
        cluster_info = get_cluster_info(hpc_url, token)
        if cluster_info and cluster_info.get("code") == "0":
            clusters = cluster_info.get("data", [])
            if clusters:
                return str(clusters[0].get("id", ""))
        return None
    
    # ============== 账户操作 ==============
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        if not self.tokens_data:
            if not self.init_tokens():
                return None
        first_token = list(self._tokens_cache.values())[0] if self._tokens_cache else None
        if first_token:
            return get_user_info(first_token)
        return None
    
    # ============== 作业操作 ==============
    
    def get_user_queues(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """获取用户可访问队列"""
        hpc_url = self.get_hpc_url(cluster_name)
        token = self.get_token(cluster_name)
        scheduler_id = self.get_scheduler_id(cluster_name)
        if not hpc_url or not token or not scheduler_id:
            return None
        return query_user_queues(hpc_url, token, self.user, scheduler_id)
    
    def submit_job(self, cluster_name: str, job_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提交作业"""
        hpc_url = self.get_hpc_url(cluster_name)
        token = self.get_token(cluster_name)
        scheduler_id = self.get_scheduler_id(cluster_name)
        if not hpc_url or not token or not scheduler_id:
            return None
        return submit_job(hpc_url, token, scheduler_id, job_config)
    
    def delete_job(self, cluster_name: str, job_id: str) -> Optional[Dict[str, Any]]:
        """删除作业"""
        hpc_url = self.get_hpc_url(cluster_name)
        token = self.get_token(cluster_name)
        scheduler_id = self.get_scheduler_id(cluster_name)
        if not hpc_url or not token or not scheduler_id:
            return None
        return delete_job(hpc_url, token, scheduler_id, self.user, job_id)
    
    def get_job_detail(self, cluster_name: str, job_id: str) -> Optional[Dict[str, Any]]:
        """查询作业详情"""
        hpc_url = self.get_hpc_url(cluster_name)
        token = self.get_token(cluster_name)
        scheduler_id = self.get_scheduler_id(cluster_name)
        if not hpc_url or not token or not scheduler_id:
            return None
        return query_job_detail(hpc_url, token, scheduler_id, job_id)
    
    def get_all_jobs(self, days: int = 7) -> Dict[str, Any]:
        """获取所有计算中心的作业"""
        if not self.tokens_data:
            if not self.init_tokens():
                return {"active_jobs": [], "history_jobs": []}
        
        all_active = []
        all_history = []
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        for cluster_name, token in self._tokens_cache.items():
            hpc_url = self.get_hpc_url(cluster_name)
            if not hpc_url:
                continue
            
            cluster_info = get_cluster_info(hpc_url, token)
            if not cluster_info or cluster_info.get("code") != "0":
                continue
            
            for cluster in cluster_info.get("data", []):
                scheduler_id = str(cluster.get("id", ""))
                if not scheduler_id:
                    continue
                
                jobs_data = query_jobs(hpc_url, token, scheduler_id)
                if jobs_data and jobs_data.get("code") == "0":
                    for job in jobs_data.get("data", {}).get("list", []):
                        job["_cluster_name"] = cluster_name
                        all_active.append(job)
                
                history_data = query_history_jobs(hpc_url, token, scheduler_id, start_str, end_str)
                if history_data and history_data.get("code") == "0":
                    for job in history_data.get("data", {}).get("list", []):
                        job["_cluster_name"] = cluster_name
                        all_history.append(job)
        
        return {"active_jobs": all_active, "history_jobs": all_history}
    
    # ============== 文件操作 ==============
    
    def list_dir(self, cluster_name: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """列出目录"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return None
        return list_files(efile_url, token, path)
    
    def mkdir(self, cluster_name: str, path: str, create_parents: bool = True) -> bool:
        """创建目录"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return create_folder(efile_url, token, path, create_parents)
    
    def touch(self, cluster_name: str, file_path: str) -> bool:
        """创建空文件"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return create_file(efile_url, token, file_path)
    
    def upload(self, cluster_name: str, local_path: str, remote_path: str) -> bool:
        """上传文件"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return upload_file(efile_url, token, local_path, remote_path)
    
    def download(self, cluster_name: str, remote_path: str, local_path: str) -> bool:
        """下载文件"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return download_file(efile_url, token, remote_path, local_path)
    
    def remove(self, cluster_name: str, path: str, recursive: bool = False) -> bool:
        """删除文件/目录"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return delete_file(efile_url, token, path, recursive)
    
    def exists(self, cluster_name: str, path: str) -> bool:
        """检查文件是否存在"""
        efile_url = self.get_efile_url(cluster_name)
        token = self.get_token(cluster_name)
        if not efile_url or not token:
            return False
        return check_file_exists(efile_url, token, path)


# ============== 自然语言意图解析 ==============

class IntentParser:
    """自然语言意图解析器"""
    
    CLUSTER_KEYWORDS = {
        "昆山": "华东一区【昆山】",
        "华东一区": "华东一区【昆山】",
        "哈尔滨": "东北一区【哈尔滨】",
        "东北": "东北一区【哈尔滨】",
        "东北一区": "东北一区【哈尔滨】",
        "乌镇": "华东三区【乌镇】",
        "华东三区": "华东三区【乌镇】",
        "西安": "西北一区【西安】",
        "西北": "西北一区【西安】",
        "西北一区": "西北一区【西安】",
        "雄衡": "华北一区【雄衡】",
        "华北": "华北一区【雄衡】",
        "华北一区": "华北一区【雄衡】",
        "山东": "华东四区【山东】",
        "华东四区": "华东四区【山东】",
        "四川": "西南一区【四川】",
        "西南": "西南一区【四川】",
        "西南一区": "西南一区【四川】",
        "核心": "核心节点【分区一】",
        "核心节点": "核心节点【分区一】",
        "分区一": "核心节点【分区一】",
        "分区二": "核心节点【分区二】",
    }
    
    @classmethod
    def parse_cluster(cls, text: str) -> Optional[str]:
        """从文本中解析计算中心名称"""
        text_lower = text.lower()
        for keyword, cluster_name in cls.CLUSTER_KEYWORDS.items():
            if keyword in text_lower:
                return cluster_name
        return None
    
    @classmethod
    def parse_path(cls, text: str) -> Optional[str]:
        """从文本中解析路径"""
        patterns = [
            r'(/public/home/[^\s\,\;\,]+)',
            r'(/work/home/[^\s\,\;\,]+)',
            r'(/home/[^\s\,\;\,]+)',
            r'(~/[^\s\,\;\,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def parse_local_path(cls, text: str) -> Optional[str]:
        """从文本中解析本地路径"""
        patterns = [
            r'(/Users/[^\s\,\;\,]+)',
            r'(~/[^\s\,\;\,]+)',
            r'(\.[^\s\,\;\,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def is_account_query(cls, text: str) -> bool:
        """是否是查询账户信息"""
        keywords = ["余额", "账户", "account", "balance", "多少钱", "欠费"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_job_query(cls, text: str) -> bool:
        """是否是查询作业"""
        keywords = ["查询作业", "查看作业", "作业状态", "job list", "作业列表"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_job_submit(cls, text: str) -> bool:
        """是否是提交作业"""
        keywords = ["提交作业", "submit", "提交任务", "运行作业", "跑作业"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_job_delete(cls, text: str) -> bool:
        """是否是删除作业"""
        keywords = ["删除作业", "cancel", "terminate", "停止作业", "取消作业"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_file_list(cls, text: str) -> bool:
        """是否是列出文件"""
        keywords = ["列出", "显示", "查看", "ls", "list", "目录", "文件列表"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_mkdir(cls, text: str) -> bool:
        """是否是创建目录"""
        keywords = ["创建文件夹", "创建目录", "mkdir", "新建文件夹", "新建目录"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_upload(cls, text: str) -> bool:
        """是否是上传"""
        keywords = ["上传", "upload", "发送文件", "传到"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_download(cls, text: str) -> bool:
        """是否是下载"""
        keywords = ["下载", "download", "下载到", "拉取"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_delete(cls, text: str) -> bool:
        """是否是删除"""
        keywords = ["删除", "remove", "delete", "rm", "删掉"]
        return any(kw in text.lower() for kw in keywords)
    
    @classmethod
    def is_create_file(cls, text: str) -> bool:
        """是否是创建文件"""
        keywords = ["创建文件", "新建文件", "touch", "生成文件"]
        return any(kw in text.lower() for kw in keywords)


# ============== 作业提交向导 ==============

class JobSubmitWizard:
    """作业提交向导"""
    
    DEFAULTS = {
        "nnodes": "1",
        "ppn": "1",
        "wall_time": "01:00:00",
        "work_dir": "~/claw_workspace",
        "submit_type": "cmd",
        "appname": "BASE",
    }
    
    def __init__(self, client: SCNetClient, cluster_name: str):
        self.client = client
        self.cluster_name = cluster_name
        self.job_config = {}
    
    def get_available_queues(self) -> List[Dict[str, Any]]:
        """获取可用队列"""
        result = self.client.get_user_queues(self.cluster_name)
        if result and result.get("code") == "0":
            return result.get("data", [])
        return []
    
    def build_job_config(self, **kwargs) -> Dict[str, Any]:
        """构建作业配置"""
        config = self.DEFAULTS.copy()
        config.update(kwargs)
        
        # 确保工作目录存在
        work_dir = config.get("work_dir", "~/claw_workspace")
        if work_dir.startswith("~"):
            home = self.client.get_home_path(self.cluster_name) or "/public/home/yiziqinx"
            work_dir = work_dir.replace("~", home)
            config["work_dir"] = work_dir
        
        # 设置输出文件路径
        config["stdout"] = config.get("stdout", f"{work_dir}/std.out.%j")
        config["stderr"] = config.get("stderr", f"{work_dir}/std.err.%j")
        
        return config
    
    def preview_job_config(self, config: Dict[str, Any]) -> str:
        """预览作业配置"""
        lines = [
            "📋 作业配置预览:",
            "-" * 40,
            f"作业名称: {config.get('job_name', '未设置')}",
            f"运行命令: {config.get('cmd', '未设置')}",
            f"节点数: {config.get('nnodes', 1)}",
            f"每节点核数: {config.get('ppn', 1)}",
            f"运行时长: {config.get('wall_time', '01:00:00')}",
            f"队列: {config.get('queue', '未设置')}",
            f"工作目录: {config.get('work_dir', '~')}",
            f"标准输出: {config.get('stdout', '')}",
            f"错误输出: {config.get('stderr', '')}",
            "-" * 40,
        ]
        return "\n".join(lines)
    
    def submit(self, config: Dict[str, Any]) -> Optional[str]:
        """提交作业"""
        result = self.client.submit_job(self.cluster_name, config)
        if result and result.get("code") == "0":
            return result.get("data")
        return None


# ============== 主函数和测试 ==============

def main():
    """主函数"""
    access_key = os.environ.get("SCNET_ACCESS_KEY")
    secret_key = os.environ.get("SCNET_SECRET_KEY")
    user = os.environ.get("SCNET_USER")
    
    if not all([access_key, secret_key, user]):
        print("❌ 错误: 缺少必要的环境变量")
        print("\n请设置以下环境变量:")
        print("  export SCNET_ACCESS_KEY=\"你的AK\"")
        print("  export SCNET_SECRET_KEY=\"你的SK\"")
        print("  export SCNET_USER=\"你的用户名\"")
        sys.exit(1)
    
    client = SCNetClient(access_key, secret_key, user)
    
    print("🔑 正在初始化SCNet客户端...")
    if not client.init_tokens():
        print("❌ 初始化失败")
        sys.exit(1)
    
    print(f"✅ 已连接到 {len(client._tokens_cache)} 个计算中心")


if __name__ == "__main__":
    main()
