# personal_wx_yinxiang_agent

微信公众号消息回调服务（极简版）。FastAPI + uvicorn，无 Nginx / Docker，uvicorn 直接监听 `0.0.0.0:80`。

## 功能

- `GET /wechat`：服务器配置验证（签名校验通过后原样回显 `echostr`）
- `POST /wechat`：消息推送（验签 + 明文 XML 解析 + MsgId 去重 + 被动回复）
- 文本消息回复「收到！」，非文本消息回复「收到（该类型暂不处理）」
- 处理逻辑封装为 `process_message(content, from_user)` 钩子，方便后续接入印象笔记

## 文件

| 文件 | 说明 |
| --- | --- |
| `app.py` | 单文件服务 |
| `.env` | `WECHAT_TOKEN=syt`（不提交到 git） |
| `requirements.txt` | 依赖：fastapi、uvicorn、python-dotenv |
| `wechat-bot.service` | systemd 单元 |
| `selftest.py` | 自测脚本（仅标准库） |

## 本地运行

```bash
python3.11 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn app:app --host 0.0.0.0 --port 80
```

## 部署（生产，/opt/wechat-bot）

```bash
mkdir -p /opt/wechat-bot
cp app.py .env requirements.txt /opt/wechat-bot/
cd /opt/wechat-bot
python3.11 -m venv venv
venv/bin/pip install -r requirements.txt

cp wechat-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wechat-bot
systemctl status wechat-bot
ss -tlnp | grep :80
```

## 自测

```bash
python3 selftest.py            # 默认 http://127.0.0.1:80
```

## 配置说明

- 回调 URL：`http://8.160.169.97:80/wechat`（注意路径是 `/wechat`，不是 `/wechat/callback`）
- Token：`syt`
- 消息加密方式：明文模式，数据格式 XML
