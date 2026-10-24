"""微信公众号消息回调服务（极简版）。

- GET  /wechat：服务器配置验证（签名校验，回显 echostr）
- POST /wechat：消息推送（验签 + XML 解析 + MsgId 去重 + 被动回复）

仅依赖 fastapi、uvicorn、python-dotenv。
"""
import hashlib
import logging
import os
import time
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response

load_dotenv()

TOKEN = os.getenv("WECHAT_TOKEN", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("wechat-bot")

app = FastAPI()

# 模块级 MsgId 去重表：{msg_id: 首次到达时间戳}，防止微信重试导致重复回复
_SEEN = {}
_SEEN_TTL = 300  # 去重窗口（秒）


def check_signature(token, signature, timestamp, nonce):
    """微信签名校验：token/timestamp/nonce 字典序排序后拼接，计算 sha1。"""
    if not (token and signature and timestamp and nonce):
        return False
    raw = "".join(sorted([token, timestamp, nonce]))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest() == signature


def process_message(content, from_user):
    """文本消息处理钩子。

    本期直接返回「收到！」；后续可在此接入印象笔记等逻辑。
    """
    return "收到！"


def build_reply(to_user, from_user, content):
    """构造被动回复 XML。

    to_user:   用户 openid（收到的 FromUserName）
    from_user: 公众号原始 ID（收到的 ToUserName）
    """
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        "</xml>"
    )


def cleanup_seen():
    now = time.time()
    for msg_id in [k for k, v in _SEEN.items() if now - v > _SEEN_TTL]:
        _SEEN.pop(msg_id, None)


@app.get("/wechat")
async def wechat_get(
    signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
    echostr: str = Query(None),
):
    if not check_signature(TOKEN, signature, timestamp, nonce):
        return Response(status_code=403)
    # 原样回显 echostr：纯文本，不加引号/换行/JSON 包装
    return Response(content=echostr or "", media_type="text/plain")


@app.post("/wechat")
async def wechat_post(
    request: Request,
    signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
):
    if not check_signature(TOKEN, signature, timestamp, nonce):
        return Response(status_code=403)

    try:
        root = ET.fromstring(await request.body())

        def get(name):
            el = root.find(name)
            return (el.text or "") if el is not None else ""

        to_user = get("ToUserName")      # 公众号原始 ID
        from_user = get("FromUserName")  # 用户 openid
        msg_type = get("MsgType")
        content = get("Content")
        msg_id = get("MsgId")

        logger.info(
            "MsgType=%s Content=%s OpenId=%s",
            msg_type,
            content[:50],
            from_user[:8],
        )

        # 按 MsgId 去重，避免微信重试造成重复回复
        if msg_id:
            if msg_id in _SEEN:
                logger.info("重复消息 MsgId=%s，忽略", msg_id)
                return Response("success")
            _SEEN[msg_id] = time.time()
            cleanup_seen()

        if msg_type == "text":
            reply_content = process_message(content, from_user)
        else:
            reply_content = "收到（该类型暂不处理）"

        reply = build_reply(from_user, to_user, reply_content)
        return Response(content=reply, media_type="text/xml; charset=utf-8")
    except Exception:
        logger.exception("处理消息时发生异常")
        return Response("success")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
