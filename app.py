import streamlit as st
import requests
import time
from pathlib import Path
# 捕获超时专用异常
from requests.exceptions import ReadTimeout

# ===================== 全局配置常量（结构优化：统一管理） =====================
# API配置
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "deepseek-ai/DeepSeek-V4-Pro"
API_KEY = "sk-rmnuzjfjyewewssshwbcjjszhpeqpxmakgyaenguiqmwablv"
REQUEST_TIMEOUT = 30
MAX_RETRY = 2  # 超时最大重试次数

# 提示词配置
ROLE_PROMPTS = {
    "新生": "你像热心的大二学长，语气详细、口语化、多给鼓励。涉及金钱/转账无条件提示「先联系辅导员核实」",
    "在校生": "你像办事老司机学长，语气简洁。优先给：① 地点 ② 电话 ③ 所需材料 ④ 办结时间",
    "教师": "你面向教师，语气专业礼貌。优先给：① 政策依据 ② 办事窗口 ③ 联系人",
}

ALIAS_DICT = """【同义词表】
- "学校" "航院" "ZUA" "郑航" ≈ 郑州航空工业管理学院
- "新校区" "龙湖" "新校" ≈ 龙子湖校区
- "卡" "饭卡" "校卡" ≈ 校园一卡通
- "保安" "门卫" "校警" ≈ 保卫处
- "迁户口" "落户" ≈ 户籍迁入/迁出
- "调宿舍" "换宿舍" ≈ 宿舍调整申请
- "证明" "在读证明" ≈ 在校学籍证明
"""

# 提示文案常量
TIMEOUT_TIP = "请求超时啦！当前网络或接口响应较慢，已自动重试，若多次失败请稍后再试"
API_FAIL_TIP = "接口调用失败，请检查网络或API密钥配置"
FORMAT_ERROR_TIP = "大模型返回数据格式异常，无法生成回答"

# 标签页分类问题
TAB_QUESTIONS = {
    "新生指南": [
        "报到那天先去哪？",
        "学费什么时候交？",
        "宿舍是 4 人间还是 6 人间？",
        "军训需要准备哪些物品？"
    ],
    "办事流程": [
        "怎么开在读证明？",
        "校园卡丢了怎么补？",
        "转专业怎么申请？",
        "图书馆开放和闭馆时间？"
    ],
    "应急防骗": [
        "有人冒充辅导员要钱怎么办？",
        "遇到电信诈骗该向谁求助？",
        "校园内物品丢失去哪里报备？",
        "心理不舒服怎么联系学校心理咨询中心？"
    ]
}

PHONE_QUERY = "请列出郑州航院校园相关联系电话（电话黄页）"

# ===================== 工具函数（增加文档注释，提升可读性） =====================
def load_school_info():
    """
    读取data文件夹下所有md校园资料
    返回值：拼接后的全部校园文本，无文件夹则返回空提示
    """
    data_path = Path("data")
    if not data_path.exists():
        return "暂无校园资料文件"
    content_list = []
    for file in sorted(data_path.glob("*.md")):
        file_text = file.read_text(encoding="utf-8")
        content_list.append(f"=== {file.name} ===\n{file_text}")
    return "\n\n".join(content_list)


def get_system_prompt(role, info):
    """
    根据用户身份拼接系统提示词，内置回答硬性规则
    :param role: 用户身份 新生/在校生/教师
    :param info: 读取到的校园md资料
    :return: 完整系统prompt字符串
    """
    base_prompt = f"""你是郑州航院校园信息助手「小航」。
# 身份语气规则
{ROLE_PROMPTS[role]}
# 词汇同义词映射
{ALIAS_DICT}
# 强制回答规则
1. 仅能依靠下方校园资料作答，无相关内容统一回复：我没收录，建议拨打 0371-61911000 总值班室
2. 禁止编造电话、地址、费用、人名等信息
3. 涉及转账、收费，必须提醒先联系辅导员，谨防诈骗
4. 心理危机问题统一提供心理援助热线+辅导员告知建议
5. 无法查询个人教务、一卡通、财务隐私信息
6. 回答末尾标注【来源:文件名】

【学校资料】
{info}
"""
    return base_prompt


def llm_call(sys_prompt, chat_history):
    """
    调用硅基流动大模型接口，支持多轮对话历史，增加超时重试、异常捕获
    :param sys_prompt: 系统提示词
    :param chat_history: 列表，存储多轮user/assistant对话记录
    :return: 模型回答文本 / 异常提示文本
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    # 构造完整消息队列：系统提示词 + 全部历史对话
    messages = [{"role": "system", "content": sys_prompt}]
    messages.extend(chat_history)

    payload = {
        "model": MODEL_NAME,
        "messages": messages
    }

    # 超时重试逻辑
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
            # 判断返回数据合法性
            if "choices" in res_json and len(res_json["choices"]) > 0:
                return res_json["choices"][0]["message"]["content"]
            else:
                return FORMAT_ERROR_TIP
        except ReadTimeout:
            retry_count += 1
            if retry_count > MAX_RETRY:
                return TIMEOUT_TIP
            st.warning(f"第{retry_count}次超时，正在重试...")
        except Exception:
            return API_FAIL_TIP
    return TIMEOUT_TIP


# ===================== 页面初始化 =====================
if "question" not in st.session_state:
    st.session_state.question = ""
# 【按照课件修改】history存储：time、role、question、answer
if "history" not in st.session_state:
    st.session_state.history = []
# 【新增】真正用于多轮对话上下文存储
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
# 记录上一次选中身份，切换身份清空对话上下文
if "last_identity" not in st.session_state:
    st.session_state.last_identity = ""

# ===================== 页面主体渲染 =====================
st.title("小航｜郑州航院校园信息AI助手")
identity = st.radio("请选择你的身份", ["新生", "在校生", "教师"])

# 切换身份 → 清空多轮对话记忆（重要：不同身份提示词不一样）
if identity != st.session_state.last_identity:
    st.session_state.chat_messages = []
    # 判断：不是页面首次加载才弹出提示
    if st.session_state.last_identity != "":
        st.info("身份已切换，对话上下文已重置！")
    st.session_state.last_identity = identity

# ============【分类标签页推荐问题】============
st.markdown("**✨试试这些问题：**")
tab1, tab2, tab3 = st.tabs(["新生指南", "办事流程", "应急防骗"])

# 新生指南标签
with tab1:
    q_list = TAB_QUESTIONS["新生指南"]
    cols = st.columns(2)
    for idx, question in enumerate(q_list):
        with cols[idx % 2]:
            if st.button(question, key=f"tab_new_{idx}"):
                st.session_state["question"] = question
                st.rerun()

# 办事流程标签
with tab2:
    q_list = TAB_QUESTIONS["办事流程"]
    cols = st.columns(2)
    for idx, question in enumerate(q_list):
        with cols[idx % 2]:
            if st.button(question, key=f"tab_service_{idx}"):
                st.session_state["question"] = question
                st.rerun()

# 应急防骗标签
with tab3:
    q_list = TAB_QUESTIONS["应急防骗"]
    cols = st.columns(2)
    for idx, question in enumerate(q_list):
        with cols[idx % 2]:
            if st.button(question, key=f"tab_safe_{idx}"):
                st.session_state["question"] = question
                st.rerun()
# =================================================================

# 电话黄页快捷按钮
st.markdown("")
st.markdown("**📞兜底快捷查询**")
phone_col, _, _, _ = st.columns(4)
if phone_col.button("电话黄页"):
    st.session_state["question"] = PHONE_QUERY
    st.rerun()

# 用户输入框
user_input = st.text_input("输入你想咨询的校园问题：", value=st.session_state["question"])

# 查询提交逻辑
if st.button("发起查询"):
    # 去除首尾空格后判断
    clean_input = user_input.strip()
    if not clean_input:
        st.warning("请输入有效的校园问题！")
    else:
        start_time = time.time()
        with st.spinner("小航正在思考..."):
            school_data = load_school_info()
            full_sys_prompt = get_system_prompt(identity, school_data)
            # 将本轮用户问题加入对话上下文
            st.session_state.chat_messages.append({"role": "user", "content": clean_input})
            # 调用接口（携带全部历史对话）
            answer_result = llm_call(full_sys_prompt, st.session_state.chat_messages)

        end_time = time.time()
        cost_time = round(end_time - start_time, 1)

        # 区分正常回答和异常提示，不同样式展示
        if TIMEOUT_TIP in answer_result or API_FAIL_TIP in answer_result or FORMAT_ERROR_TIP in answer_result:
            st.error(f"提示：{answer_result}")
        else:
            st.success(f"**回答：** {answer_result}")
            # AI回复正常 → 存入多轮对话
            st.session_state.chat_messages.append({"role": "assistant", "content": answer_result})
            # =========【课件要求：保存完整问答记录（包含answer）】=========
            st.session_state.history.append({
                "time": time.strftime("%H:%M:%S"),
                "role": identity,
                "question": clean_input,
                "answer": answer_result
            })
        # 展示接口耗时（实习必做交互优化）
        st.caption(f"本次提问耗时：{cost_time} 秒")
        st.session_state["question"] = ""

# 问答历史区域 + 导出对话 + 清空按钮
st.divider()
col_his, col_export, col_clear = st.columns([3, 1, 1])
with col_his:
    st.subheader("📜问答历史")
with col_export:
    # 课件：导出对话txt
    if st.session_state.get("history"):
        text = ""
        for item in st.session_state["history"]:
            text += f"[{item['time']}] {item['role']} 提问：{item['question']}\n"
            text += f"回答：{item['answer']}\n"
            text += "---\n"
        st.download_button(
            label="导出对话记录",
            data=text,
            file_name=f"小航对话记录_{time.strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
with col_clear:
    if st.button("清空历史"):
        st.session_state.history = []
        st.session_state.chat_messages = []  # 同时清空多轮对话上下文
        st.rerun()

# 【课件标准渲染代码：倒序展示，同时输出提问+回答】
if st.session_state.history:
    for item in reversed(st.session_state["history"]):
        st.write(f"[{item['time']}] {item['role']} 提问：{item['question']}")
        st.write(f"回答：{item['answer']}")
        st.caption("————————————————")
else:
    st.caption("暂无问答历史记录")
