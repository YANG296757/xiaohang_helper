import streamlit as st
import requests
from pathlib import Path

# ========== 配置信息 ==========
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Qwen/Qwen2.5-7B-Instruct"
API_KEY = "sk-rmnuzjfjyewewssshwbcjjszhpeqpxmakgyaenguiqmwablv"

# 三套身份提示词
SYSTEM_PROMPTS = {
    "新生": "你是【小航】郑州航院校园AI助手，专门解答新生报到、宿舍、选课、校园设施问题，回答简洁易懂。",
    "在校生": "你是【小航】郑州航院校园AI助手，解答在校学生课程、社团、考试、食堂、实训相关问题。",
    "教师": "你是【小航】郑州航院校园AI助手，面向教师，解答教务安排、场地申请、科研相关校园问题。"
}

# 推荐问题列表
suggest_questions = [
    "学校宿舍怎么样",
    "学校食堂有几个",
    "新生报到流程是什么",
    "图书馆开放时间",
    "校园快递站位置"
]

# 读取data目录所有md文档
def load_context():
    md_files = Path("data").glob("*.md")
    context = ""
    for file in md_files:
        context += file.read_text(encoding="utf-8") + "\n"
    return context

# 调用硅基流动API
def llm_call(sys_prompt, user_q, doc_ctx):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt + "\n参考资料：" + doc_ctx},
            {"role": "user", "content": user_q}
        ]
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"请求异常：{str(e)}，检查网络/API密钥余额。"

# 初始化会话变量，存放输入框内容
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

# =========页面渲染=========
st.title("小航｜郑州航院校园信息AI助手")
identity = st.radio("请选择你的身份", ["新生", "在校生", "教师"])

st.markdown("**📌推荐咨询问题（点击方框按钮快速填充）**")
# 分成3列摆放方框按钮
col1, col2, col3 = st.columns(3)
# 第一行3个按钮
if col1.button(suggest_questions[0]):
    st.session_state.user_query = suggest_questions[0]
if col2.button(suggest_questions[1]):
    st.session_state.user_query = suggest_questions[1]
if col3.button(suggest_questions[2]):
    st.session_state.user_query = suggest_questions[2]

col4, col5, _ = st.columns(3)
# 第二行剩下2个按钮
if col4.button(suggest_questions[3]):
    st.session_state.user_query = suggest_questions[3]
if col5.button(suggest_questions[4]):
    st.session_state.user_query = suggest_questions[4]

# 输入框，同步按钮选中内容
user_input = st.text_input("输入你想咨询的校园问题：", value=st.session_state.user_query)

if st.button("发起查询") and user_input:
    with st.spinner("正在查询资料并生成回答..."):
        docs = load_context()
        answer = llm_call(SYSTEM_PROMPTS[identity], user_input, docs)
        st.markdown(f"**回答：** {answer}")
