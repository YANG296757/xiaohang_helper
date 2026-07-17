import requests
from requests.exceptions import ReadTimeout

# 从config导入全局配置
from src.config import API_URL, MODEL_NAME, API_KEY, REQUEST_TIMEOUT, MAX_RETRY
from src.config import TIMEOUT_TIP, API_FAIL_TIP, FORMAT_ERROR_TIP

def llm_call(sys_prompt, chat_history):
    """
    封装大模型接口请求，支持多轮对话、超时重试、异常捕获
    :param sys_prompt: 系统角色提示词
    :param chat_history: 多轮对话上下文列表
    :return: 模型回答文本/异常提示文案
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [{"role": "system", "content": sys_prompt}]
    messages.extend(chat_history)

    payload = {
        "model": MODEL_NAME,
        "messages": messages
    }

    retry_count = 0
    while retry_count <= MAX_RETRY:
        try:
            resp = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            res_json = resp.json()
            if "choices" in res_json and len(res_json["choices"]) > 0:
                return res_json["choices"][0]["message"]["content"]
            else:
                return FORMAT_ERROR_TIP
        except ReadTimeout:
            retry_count += 1
            if retry_count > MAX_RETRY:
                return TIMEOUT_TIP
        except Exception:
            return API_FAIL_TIP
    return TIMEOUT_TIP