"""自测脚本：验证 GET/POST /wechat 的签名校验与回复格式。

仅用标准库（urllib），无需额外依赖。

用法：python3 selftest.py [base_url]
默认 base_url = http://127.0.0.1:80
"""
import hashlib
import sys
import time
import urllib.error
import urllib.request

TOKEN = "syt"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:80"


def make_signature(token, timestamp, nonce):
    raw = "".join(sorted([token, timestamp, nonce]))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def http(method, url, data=None):
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    ok = True
    timestamp = str(int(time.time()))
    nonce = "testnonce"
    signature = make_signature(TOKEN, timestamp, nonce)

    # 1. GET 验证：应原样返回 echostr 本身
    echostr = "hello-wechat-123456"
    url = f"{BASE}/wechat?signature={signature}&timestamp={timestamp}&nonce={nonce}&echostr={echostr}"
    status, body = http("GET", url)
    passed = status == 200 and body == echostr
    print(f"[1] GET 验证      -> status={status} body={body!r}  {'PASS' if passed else 'FAIL'}")
    ok &= passed

    # 2. POST 文本消息：应返回格式正确的 XML，Content 为「收到！」
    msg_id = str(int(time.time() * 1000))
    xml = (
        "<xml>"
        "<ToUserName><![CDATA[gh_aedc8c9389a6]]></ToUserName>"
        "<FromUserName><![CDATA[oTestUserOpenId123]]></FromUserName>"
        f"<CreateTime>{timestamp}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        "<Content><![CDATA[你好]]></Content>"
        f"<MsgId>{msg_id}</MsgId>"
        "</xml>"
    ).encode("utf-8")
    url = f"{BASE}/wechat?signature={signature}&timestamp={timestamp}&nonce={nonce}"
    status, body = http("POST", url, data=xml)
    passed = (
        status == 200
        and "<Content><![CDATA[收到！]]></Content>" in body
        and "<ToUserName><![CDATA[oTestUserOpenId123]]></ToUserName>" in body
        and "<FromUserName><![CDATA[gh_aedc8c9389a6]]></FromUserName>" in body
    )
    print(f"[2] POST 文本消息 -> status={status}  {'PASS' if passed else 'FAIL'}")
    if not passed:
        print("    body:", body)
    ok &= passed

    # 3. 错误 signature：应返回 403
    url = f"{BASE}/wechat?signature=wrong&timestamp={timestamp}&nonce={nonce}&echostr={echostr}"
    status, body = http("GET", url)
    passed = status == 403
    print(f"[3] 错误签名      -> status={status}  {'PASS' if passed else 'FAIL'}")
    ok &= passed

    print("ALL PASS" if ok else "SOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
