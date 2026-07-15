import streamlit as st

# 页面标题
st.title("Streamlit 测试页面")

# 输入框
name = st.text_input("请输入你的姓名：")

# 下拉选择框
grade = st.selectbox("选择年级：", ["大一", "大二", "大三", "大四"])

# 按钮
if st.button("点击打招呼"):
    st.success(f"你好！{name}，你的年级是{grade}")
