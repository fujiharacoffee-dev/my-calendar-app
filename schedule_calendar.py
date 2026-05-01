import pandas as pd
import streamlit as st
from PIL import Image
import datetime

# ページの設定
st.set_page_config(page_title="店舗カレンダー", layout="centered")

# ロゴの表示
try:
    logo = Image.open("ビアンコネーロ@4x-100.jpg")
    st.image(logo, width=150)
except:
    pass

st.title("店舗カレンダー")

# 背景画像の設定
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://raw.githubusercontent.com/fujiharacoffee-dev/my-calendar-app/main/background_cats.png");
        background-size: cover;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# データの読み込み
try:
    # Excelファイルの読み込み
    df = pd.read_excel("schedule_data.xlsx")
    
    # 【修正ポイント】Excelの項目名「日付」を使用
    df['日付'] = pd.to_datetime(df['日付'])

    # サイドバーで月を選択
    today = datetime.date.today()
    target_month = st.sidebar.selectbox(
        "表示する月を選択",
        range(1, 13),
        index=today.month - 1
    )

    # 表示中の日付（2026/05/01など）を表示
    st.subheader(f"{today.strftime('%Y/%m/%d')} の表示")

    # データのフィルタリング
    month_df = df[df['日付'].dt.month == target_month].sort_values('日付')

    if not month_df.empty:
        for index, row in month_df.iterrows():
            # Excelの項目名「日付」「タイトル」「時間」「詳細」に合わせて表示
            date_str = row['日付'].strftime('%m/%d')
            with st.expander(f"{date_str} : {row['タイトル']}"):
                st.write(f"**時間:** {row['時間']}")
                st.write(f"**詳細:** {row['詳細']}")
    else:
        st.info(f"{target_month}月の予定はありません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")