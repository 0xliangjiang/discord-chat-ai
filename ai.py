import requests
import json
import random
import time
import logging
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

# 读取配置文件
def read_config():
    tokens = []
    try:
        with open('data.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 解析token和代理信息
                    parts = line.split('----')
                    token = parts[0].strip()
                    proxy = parts[1].strip() if len(parts) > 1 else None
                    tokens.append((token, proxy))
        return tokens
    except Exception as e:
        logging.error(f"读取配置文件失败: {e}")
        return []

# 获取指定频道的名称
def get_channel_name(auth, channel_id):
    url = f"https://discord.com/api/v10/channels/{channel_id}"
    headers = {
        "Authorization": auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
    }

    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            channel_info = res.json()
            channel_name = channel_info.get("name", "未知频道")
            logging.info(f"频道 {channel_id} 的名称是: {channel_name}")
            return channel_name
        else:
            logging.error(f"获取频道 {channel_id} 名称失败，状态码: {res.status_code}")
            return f"获取频道名称失败，状态码: {res.status_code}"
    except requests.exceptions.RequestException as e:
        logging.error(f"请求频道 {channel_id} 名称时发生错误: {e}")
        return f"请求错误: {e}"

        

# 获取指定频道的历史消息内容
def get_context(auth, chanel_id):
    header = {
        "Authorization": auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
    }
    url = f"https://discord.com/api/v10/channels/{chanel_id}/messages?limit=20"
    try:
        res = requests.get(url=url, headers=header)
        if res.status_code == 200:
            result = json.loads(res.content)
            result_list = [
                context['content'] for context in result
                if all(char not in context['content'] for char in ['<', '@', 'http', '?', '0x'])
            ]
            if result_list:

                return result_list
            else:
                logging.info("没有找到有效的消息。")
                
        else:
            logging.error(f"获取消息失败，状态码: {res.status_code}")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"请求错误: {e}")
        

# 向GPT-4o mini模型发送请求并生成响应
def generate_response(messages, api_key, channel_name):
    gpt_api_url = "https://geekai.dev/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 根据频道名称选择语言
    is_english = '🇺🇸' in channel_name or 'english' in channel_name.lower()
    
    # 创建一个更自然的prompt
    if is_english:
        prompt = f"""You are a regular user in a Discord chat. Reply naturally to messages. Remember:

1. Keep replies short and casual, not formal
2. Don't use any punctuation
3. Limit responses to 10 words or less
4. Use casual internet language occasionally but naturally
5. Don't be overly enthusiastic maintain a casual tone
6. Not every message needs to be serious occasional jokes are fine
7. Avoid robotic or formulaic responses
8. Respond to context naturally don't force conversation
9. Avoid any sensitive or inappropriate words
10. Match the chat atmosphere blend in with others

Remember you're just a regular user keep it simple and natural

Current chat history: {messages}"""
    else:
        prompt = f"""你现在是一个Discord群聊中的普通用户，你需要用最自然的方式回复消息。请注意：

1. 回复要像真实用户一样简短随意，不要太正式
2. 不要使用任何标点符号
3. 每次回复限制在10个字以内
4. 可以偶尔使用网络用语 但要自然
5. 不要过分热情 保持随意的语气
6. 不要每句话都很认真 可以偶尔调侃
7. 避免使用机器人式的固定句式
8. 根据上下文自然接话 不要刻意引导话题
9. 不要使用任何敏感词或不当用语
10. 模仿当前聊天氛围 融入群众

记住你只是一个普通用户 用最简单自然的方式回应即可

当前聊天记录：{messages}"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        response = requests.post(gpt_api_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            gpt_response = response.json()
            return gpt_response['choices'][0]['message']['content'].strip()
        else:
            logging.error(f"GPT-4o mini API 请求失败，状态码: {response.status_code}")
            return ""
    except requests.exceptions.RequestException as e:
        logging.error(f"请求 GPT-4o mini 时发生错误: {e}")
        return ""

class DiscordBot(threading.Thread):
    def __init__(self, token, proxy, channel_list, min_delay, max_delay, gpt_api_key):
        super().__init__()
        self.token = token
        self.proxy = proxy
        self.channel_list = channel_list
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.gpt_api_key = gpt_api_key
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
        }
        self.proxies = None
        if proxy:
            self.proxies = {
                'http': proxy,
                'https': proxy
            }
            logging.info(f"Token {self.token[:6]}... 使用代理: {proxy}")
        else:
            logging.info(f"Token {self.token[:6]}... 不使用代理")

    def run(self):
        while True:
            try:
                for channel_id in self.channel_list:
                    messages = self.get_context(channel_id)
                    if messages and messages != ["获取消息失败"]:
                        self.process_channel(channel_id)
                    else:
                        logging.info(f"Token {self.token[:6]}... 没有获取到有效的消息，继续重试...")
            except Exception as e:
                logging.error(f"Token {self.token[:6]}... 运行出错: {e}")
                continue

    def get_context(self, channel_id):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=20"
        try:
            res = requests.get(url=url, headers=self.headers, proxies=self.proxies)
            if res.status_code == 200:
                result = json.loads(res.content)
                result_list = [
                    context['content'] for context in result
                    if all(char not in context['content'] for char in ['<', '@', 'http', '?', '0x'])
                ]
                return result_list
            else:
                logging.error(f"Token {self.token[:6]}... 获取消息失败，状态码: {res.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Token {self.token[:6]}... 请求错误: {e}")
            return None

    def process_channel(self, channel_id):
        try:
            channel_name = get_channel_name(self.token, channel_id)
            messages = self.get_context(channel_id)
            
            if messages:
                messages_text = " ".join(messages)
                gpt_response = generate_response(messages_text, self.gpt_api_key, channel_name)
                print(gpt_response)

                msg = {
                    "content": gpt_response,
                    "nonce": f"82329451214{random.randrange(0, 1000)}33232234",
                    "tts": False,
                }
                
                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                res = requests.post(url=url, headers=self.headers, data=json.dumps(msg), proxies=self.proxies)

                if res.status_code in [200, 201]:
                    logging.info(f"Token {self.token[:6]}... 成功向频道 {channel_name} 发送消息: {msg['content'][:50]}...")
                else:
                    logging.error(f"Token {self.token[:6]}... 向频道 {channel_name} 发送消息失败，状态码: {res.status_code}")

                sleeptime = random.randrange(self.min_delay, self.max_delay)
                logging.info(f"Token {self.token[:6]}... 将休眠 {sleeptime} 秒")
                time.sleep(sleeptime)

        except Exception as e:
            logging.error(f"Token {self.token[:6]}... 处理频道 {channel_id} 时出错: {e}")

# 主程序入口
if __name__ == "__main__":
    print("\n=== Discord AI Chat Bot 配置 ===")
    
    # 让用户选择频道
    print("\n可用的频道:")
    channels = {
        "1": ("1325903171176108163", "🇺🇸⎮english"),
        "2": ("1275205888977801339", "🇨🇳⎮chinese"),
    }
    
    for num, (id, name) in channels.items():
        print(f"{num}. {name} (ID: {id})")
    
    while True:
        channel_choice = input("\n请选择频道编号 (多个频道用逗号分隔，例如: 1,2): ").strip()
        try:
            selected_channels = [channels[num.strip()][0] for num in channel_choice.split(",") if num.strip() in channels]
            if selected_channels:
                break
            print("无效的选择，请重试")
        except:
            print("无效的输入，请重试")
    
    # 固定延时范围
    min_delay, max_delay = 300, 360  # 5-6分钟
    DELAY_RANGES = [(min_delay, max_delay)]
    
    # GPT API配置
    GPT_API_KEY = "sk-xxxx"
    
    # 读取配置文件中的token和代理信息
    token_configs = read_config()
    
    if not token_configs:
        logging.error("没有找到有效的token配置")
        exit(1)
    
    # 显示配置信息
    print("\n=== 配置信息 ===")
    selected_channel_names = [name for num, (_, name) in channels.items() if channels[num][0] in selected_channels]
    print(f"选择的频道: {', '.join(selected_channel_names)}")
    print(f"延时范围: {min_delay}-{max_delay}秒")
    print(f"账号数量: {len(token_configs)}")
    proxy_count = sum(1 for _, proxy in token_configs if proxy)
    print(f"代理使用: {proxy_count}个账号使用代理, {len(token_configs) - proxy_count}个账号不使用代理")
    
    confirm = input("\n确认启动? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消启动")
        exit(0)
    
    # 显示日志信息
    logging.info(f"共加载 {len(token_configs)} 个账号配置")
    logging.info(f"其中 {proxy_count} 个账号使用代理, {len(token_configs) - proxy_count} 个账号不使用代理")
    
    # 随机打乱token顺序
    random.shuffle(token_configs)
    
    # 创建并启动机器人线程
    bots = []
    for i, (token, proxy) in enumerate(token_configs):
        # 随机选择一个延时范围
        min_delay, max_delay = random.choice(DELAY_RANGES)
        bot = DiscordBot(token, proxy, selected_channels, min_delay, max_delay, GPT_API_KEY)
        bot.start()
        bots.append(bot)
        logging.info(f"启动机器人 Token: {token[:6]}... 延时范围: {min_delay}-{max_delay}秒")
        
        # 在启动下一个机器人之前随机等待一段时间
        if i < len(token_configs) - 1:  # 如果不是最后一个机器人
            startup_delay = random.randint(5, 15)
            logging.info(f"等待 {startup_delay} 秒后启动下一个机器人...")
            time.sleep(startup_delay)
    
    print("\n机器人已启动，按 Ctrl+C 停止")
    
    # 等待所有线程结束
    try:
        for bot in bots:
            bot.join()
    except KeyboardInterrupt:
        print("\n正在停止所有机器人...")
        # 这里可以添加清理代码
        exit(0)
