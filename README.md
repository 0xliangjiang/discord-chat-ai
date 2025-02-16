# Discord Chat AI

一个基于 GPT 的智能 Discord 聊天机器人，支持多账号、代理和自然对话。

## 特性

- 🤖 基于 GPT-4o mini 模型的智能对话
- 👥 支持多账号同时在线
- 🔄 随机化发言顺序和延时
- 🌐 支持代理配置
- 🎯 自然的对话风格
- 🔒 安全的配置管理

## 安装

1. 克隆仓库
```bash
git clone https://github.com/0xliangjiang/discord-chat-ai.git
cd discord-chat-ai
```

2. 安装依赖
```bash
pip install requests
```

## 配置

1. 创建 `data.txt` 文件，按以下格式添加 Discord 账号信息：
```
TOKEN----http://user:pass@ip:port
TOKEN  # 不使用代理的账号
```

2. 在 `ai.py` 中配置以下参数：
```python
# Discord 频道 ID
channel_list = ["YOUR_CHANNEL_ID"]

# GPT API Key
GPT_API_KEY = "YOUR_GPT_API_KEY"

# 延时范围（秒）
DELAY_RANGES = [
    (300, 350),  # 5-6分钟
]
```

## 使用

运行机器人：
```bash
python ai.py
```

## 功能说明

- **多账号支持**：可同时运行多个 Discord 账号
- **代理支持**：每个账号可配置独立的代理
- **智能对话**：使用 GPT 模型生成自然的对话内容
- **随机化**：
  - 账号发言顺序随机
  - 发言间隔时间随机
  - 启动间隔随机
- **安全特性**：
  - 支持代理保护
  - 可配置发言延时
  - 自动过滤敏感内容

## 注意事项

- 请确保遵守 Discord 的服务条款
- 合理配置发言延时，避免触发限制
- 定期更新代理配置
- 请勿用于不当用途

## 联系方式
[https://x.com/0xliangjiang](https://x.com/0xliangjiang)

## 许可证

MIT License

## 免责声明

本项目仅供学习和研究使用，使用本项目产生的任何后果由使用者自行承担。
