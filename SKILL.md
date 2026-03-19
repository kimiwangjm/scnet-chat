---
name: scnet-chat
description: 查询SCNet（国家超算互联网平台）账户信息、作业管理和文件管理。支持自然语言意图分析，可灵活组合调用接口实现复杂操作。
---

# SCNet Chat Skill

查询SCNet（国家超算互联网平台）账户信息、作业管理和文件管理。

## 功能

### 1. 账户信息
- **获取Token列表**: 获取用户在所有计算中心的token
- **查询账户余额**: 获取账户余额和用户信息

### 2. 作业管理
- **查询实时作业**: 遍历所有计算中心查询正在运行的作业
- **查询历史作业**: 查询历史作业（可指定天数范围）
- **查询用户可访问队列**: 获取计算中心可用队列列表
- **提交作业**: 提交新作业到指定队列
- **删除作业**: 取消/删除运行中或排队中的作业
- **查询作业详情**: 获取作业的详细信息

### 3. 文件管理
- **查询文件列表**: 列出目录内容
- **创建文件夹**: 支持自动创建父目录
- **创建文件**: 创建空文件
- **上传文件**: 上传本地文件到远程
- **下载文件**: 下载远程文件到本地
- **删除文件**: 删除文件或目录
- **检查文件存在**: 检查文件/目录是否存在

## 环境变量配置

```bash
export SCNET_ACCESS_KEY="你的AK"
export SCNET_SECRET_KEY="你的SK"
export SCNET_USER="你的用户名"
```

### 如何获取凭证

1. 登录SCNet平台: https://www.scnet.cn/
2. 进入个人中心 → API密钥管理
3. 获取Access Key (AK) 和 Secret Key (SK)

## 使用方法

### 方式1：命令行直接运行

```bash
python3 ~/.openclaw/workspace/skills/scnet-chat/scripts/scnet_chat.py
```

### 方式2：作业提交向导

```python
from scnet_chat import SCNetClient, JobSubmitWizard

# 初始化客户端
client = SCNetClient(access_key, secret_key, user)
client.init_tokens()

# 创建作业提交向导
wizard = JobSubmitWizard(client, "华东一区【昆山】")

# 获取可用队列
queues = wizard.get_available_queues()

# 构建并提交作业
job_config = wizard.build_job_config(
    job_name="MyJob",
    cmd="python main.py",
    nnodes="1",
    ppn="4",
    queue="Agent0",
    wall_time="01:00:00"
)

# 预览配置
print(wizard.preview_job_config(job_config))

# 提交作业
job_id = wizard.submit(job_config)
print(f"作业ID: {job_id}")
```

### 方式3：直接调用客户端方法

```python
from scnet_chat import SCNetClient

client = SCNetClient(access_key, secret_key, user)
client.init_tokens()

# 账户信息
account = client.get_account_info()

# 作业操作
queues = client.get_user_queues("华东一区【昆山"]")
job_id = client.submit_job("华东一区【昆山"], {...})
client.delete_job("华东一区【昆山"], job_id)
detail = client.get_job_detail("华东一区【昆山"], job_id)

# 文件操作
client.mkdir("华东一区【昆山"], "/public/home/user/workspace")
client.upload("华东一区【昆山"], "/local/file.txt", "/remote/dir/")
```

## 自然语言意图解析

### 计算中心识别

| 关键词 | 识别为 |
|--------|--------|
| 昆山、华东一区 | 华东一区【昆山】 |
| 哈尔滨、东北、东北一区 | 东北一区【哈尔滨】 |
| 乌镇、华东三区 | 华东三区【乌镇】 |
| 西安、西北、西北一区 | 西北一区【西安】 |
| 雄衡、华北、华北一区 | 华北一区【雄衡】 |
| 山东、华东四区 | 华东四区【山东】 |
| 四川、西南、西南一区 | 西南一区【四川】 |
| 核心、核心节点、分区一 | 核心节点【分区一】 |
| 分区二 | 核心节点【分区二】 |

### 意图识别

| 意图 | 关键词 |
|------|--------|
| 查询账户 | 余额、账户、account、balance、多少钱 |
| 查询作业 | 查询作业、查看作业、作业状态、作业列表 |
| **提交作业** | **提交作业、submit、提交任务、运行作业** |
| **删除作业** | **删除作业、cancel、terminate、停止作业** |
| 列出文件 | 列出、显示、查看、ls、list、目录 |
| 创建目录 | 创建文件夹、创建目录、mkdir |
| 上传文件 | 上传、upload、发送文件 |
| 下载文件 | 下载、download、拉取 |

## 作业提交配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| job_name | 作业名称 | 必填 |
| cmd | 运行命令 | 必填 |
| nnodes | 节点数 | 1 |
| ppn | 每节点核数 | 1 |
| queue | 队列名称 | 必填 |
| wall_time | 最大运行时长 | 01:00:00 |
| work_dir | 工作目录 | ~/claw_workspace |
| nproc | 总核心数 | 1 |
| ngpu | GPU卡数 | - |
| ndcu | DCU卡数 | - |
| stdout | 标准输出文件 | {work_dir}/std.out.%j |
| stderr | 错误输出文件 | {work_dir}/std.err.%j |

## 作业状态说明

| 状态码 | 含义 |
|--------|------|
| statR | 🟢 运行中 |
| statQ | ⏳ 排队中 |
| statH | ⏸️ 保留 |
| statS | ⏸️ 挂起 |
| statE | ❌ 退出 |
| statC | ✅ 完成 |
| statW | ⏳ 等待 |
| statX | ⚠️ 其他 |
| statT | 🛑 终止 |
| statDE | 🗑️ 删除 |

## API 说明

### 作业管理接口

- **查询集群信息**: `GET {hpcUrl}/hpc/openapi/v2/cluster`
- **查询用户可访问队列**: `GET {hpcUrl}/hpc/openapi/v2/queuenames/users/{username}`
- **提交作业**: `POST {hpcUrl}/hpc/openapi/v2/apptemplates/BASIC/BASE/job`
- **删除作业**: `DELETE {hpcUrl}/hpc/openapi/v2/jobs`
- **查询作业详情**: `GET {hpcUrl}/hpc/openapi/v2/jobs/{job_id}`
- **查询实时作业**: `GET {hpcUrl}/hpc/openapi/v2/jobs`
- **查询历史作业**: `GET {hpcUrl}/hpc/openapi/v2/historyjobs`

### 文件管理接口

- **查询文件列表**: `GET {efileUrl}/openapi/v2/file/list`
- **创建文件夹**: `POST {efileUrl}/openapi/v2/file/mkdir`
- **创建文件**: `POST {efileUrl}/openapi/v2/file/touch`
- **上传文件**: `POST {efileUrl}/openapi/v2/file/upload`
- **下载文件**: `GET {efileUrl}/openapi/v2/file/download`
- **删除文件**: `POST {efileUrl}/openapi/v2/file/remove`
- **检查文件存在**: `POST {efileUrl}/openapi/v2/file/exist`

## 文件说明

- `scripts/scnet_chat.py` - 主程序，包含账户、作业、文件管理全部功能
- `scripts/scnet_file.py` - 文件管理模块（独立版本）

## 注意事项

1. 确保网络可以访问各计算中心的API地址
2. AK/SK需要妥善保管，不要泄露
3. token有过期时间，过期后需要重新获取
4. 作业提交前需要确认队列有可用资源
5. 文件操作接口使用efileUrls，作业操作接口使用hpcUrls
6. 账户余额单位为"元"
