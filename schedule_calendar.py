import subprocess
import sys

# 強制的に openpyxl をインストールする命令
try:
    import openpyxl
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
    import openpyxl

import streamlit as st
# ...（以下、元のコードが続く）
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import datetime

# --- 1. 基本設定 ---
st.set_page_config(page_title="My Calendar App", layout="centered")

# --- 2. ファイルの読み込み ---
# 画像、Excel、フォントが同じフォルダにある前提です
try:
    bg_img = Image.open("background_cats.png")
    logo_img = Image.open("ビアンコネーロ@4x-100.jpg")
    font_path = "NotoSansCJKjp-Regular.otf"
    df_schedule = pd.read_excel("schedule_data.xlsx")
    config = pd.read_excel("app_config.xlsx")
except FileNotFoundError as e:
    st.error(f"必要なファイルが見つかりません: {e}")
    st.stop()

# --- 3. サイドバー設定（UI部分） ---
st.sidebar.image(logo_img, width=100)
st.sidebar.title("カレンダー設定")

# 今日の日付をデフォルトに
selected_date = st.sidebar.date_input("日付を選択", datetime.date.today())

# 【修正箇所】value=False にすることで、初期状態のレ点を外しています
is_business_day = st.sidebar.checkbox("営業日（猫足を表示）", value=False)

# --- 4. カレンダー生成ロジック ---
def generate_calendar(date, show_stamp):
    # ベースとなる背景画像を作成
    canvas = bg_img.copy()
    draw = ImageDraw.Draw(canvas)
    
    # 日本語フォントの設定
    try:
        font = ImageFont.truetype(font_path, 40)
        font_small = ImageFont.truetype(font_path, 25)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 日付の描画
    draw.text((50, 50), f"{date.year}年 {date.month}月 {date.day}日", fill="black", font=font)

    # 営業日の場合、猫足スタンプを表示
    if show_stamp:
        try:
            stamp = Image.open("image_0d385a.png").convert("RGBA")
            # スタンプのサイズ調整と合成
            stamp = stamp.resize((100, 100))
            canvas.paste(stamp, (450, 40), stamp)
        except:
            draw.text((450, 50), "🐾", fill="brown", font=font)

    # Excelからその日の予定を検索して表示
    day_str = date.strftime("%Y-%m-%d")
    todays_plan = df_schedule[df_schedule['date'].astype(str) == day_str]
    
    if not todays_plan.empty:
        plan_text = todays_plan.iloc[0]['event']
        draw.text((50, 150), f"予定: {plan_text}", fill="blue", font=font_small)
    else:
        draw.text((50, 150), "予定はありません", fill="gray", font=font_small)

    return canvas

# --- 5. メイン画面表示 ---
st.title("店舗カレンダー")
st.write(f"### {selected_date.strftime('%Y/%m/%d')} の表示")

# カレンダー画像を生成
result_image = generate_calendar(selected_date, is_business_day)

# 画面に表示
st.image(result_image, use_container_width=True)

# ダウンロードボタン
import io
buf = io.BytesIO()
result_image.save(buf, format="PNG")
byte_im = buf.getvalue()
st.download_button(label="画像を保存", data=byte_im, file_name=f"calendar_{selected_date}.png", mime="image/png")