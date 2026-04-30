import os
import calendar
from datetime import date, time
from io import BytesIO
import requests

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ================================
# 基本設定 & パス
# ================================
st.set_page_config(page_title="FUJIHARACOFFEEカレンダー", layout="wide")

APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DATA_FILE = os.path.join(APP_DIR, "schedule_data.xlsx")
CONFIG_FILE = os.path.join(APP_DIR, "app_config.xlsx")

BG_IMAGE_FILE = os.path.join(APP_DIR, "ビアンコネーロ@4x-100.jpg")
STAMP_IMAGE_FILE = os.path.join(APP_DIR, "image_0d385a.png")
FOOTER_PAW_FILE = os.path.join(APP_DIR, "image_0d385a.png")

# ================================
# データ管理
# ================================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE)
            for col in ["id", "日付", "時間", "タイトル", "スタンプ"]:
                if col not in df.columns: df[col] = "" if col != "スタンプ" else False
            return df
        except: pass
    return pd.DataFrame(columns=["id", "日付", "時間", "タイトル", "スタンプ"])

def load_config():
    default_conf = {
        "footer_text": "営業時間\n月〜金 13:00〜17:00\n(土曜日はカレンダーをご確認ください。)\n※イベントによって営業時間が変わります", 
        "footer_font_size": 35,
        "stamp_size": 100,
        "title_font_size": 22
    }
    if os.path.exists(CONFIG_FILE):
        try:
            saved_conf = pd.read_excel(CONFIG_FILE).iloc[0].to_dict()
            for key, value in default_conf.items():
                if key not in saved_conf: saved_conf[key] = value
            return saved_conf
        except: pass
    return default_conf

def save_data(df): df.to_excel(DATA_FILE, index=False)
def save_config(config_dict): pd.DataFrame([config_dict]).to_excel(CONFIG_FILE, index=False)

@st.cache_data
def get_font(size):
    font_path = os.path.join(APP_DIR, "NotoSansCJKjp-Regular.otf")
    if os.path.exists(font_path): return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# ================================
# 画像生成ロジック
# ================================
def create_calendar_image(year, month, df, config):
    width, height = 1800, 1400 
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    main_color = (138, 125, 106, 255)

    if os.path.exists(BG_IMAGE_FILE):
        try:
            bg = Image.open(BG_IMAGE_FILE).convert("RGBA")
            bg.thumbnail((1100, 1100))
            alpha = ImageEnhance.Brightness(bg.split()[3]).enhance(0.12)
            bg.putalpha(alpha)
            img.paste(bg, (width - bg.width - 40, height - bg.height - 250), bg)
        except: pass

    draw.text((80, 40), str(month), font=get_font(180), fill=main_color)
    draw.text((320, 110), f"{year} {calendar.month_name[month]}", font=get_font(55), fill=main_color)

    start_y, cell_w, cell_h = 300, width // 7, 160
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for i, d_label in enumerate(days):
        lbl_c = (255, 99, 71, 255) if i == 6 else (123, 104, 238, 255) if i == 5 else (176, 164, 148, 255)
        draw.text((i * cell_w + 45, start_y - 60), d_label, font=get_font(30), fill=lbl_c)

    cal = calendar.Calendar(firstweekday=0)
    last_y = 300
    for r, week in enumerate(cal.monthdatescalendar(year, month)):
        for c, d in enumerate(week):
            x, y = c * cell_w, start_y + r * cell_h
            last_y = max(last_y, y + cell_h)
            draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(235, 235, 235, 255))
            d_fill = main_color if d.month == month else (215, 215, 215, 255)
            draw.text((x + 20, y + 15), str(d.day), font=get_font(35), fill=d_fill)

            day_str = d.strftime("%Y-%m-%d")
            day_items = df[df["日付"] == day_str] if not df.empty else pd.DataFrame()

            if not day_items.empty and any(day_items["スタンプ"] == True) and os.path.exists(STAMP_IMAGE_FILE):
                try:
                    s_size = config.get("stamp_size", 100)
                    st_img = Image.open(STAMP_IMAGE_FILE).convert("RGBA")
                    st_img = st_img.resize((int(s_size), int(s_size * 0.85)), Image.LANCZOS)
                    img.paste(st_img, (int(x + cell_w//2 - s_size//2), int(y + cell_h//2 - (s_size*0.85)//2)), st_img)
                except: pass

            curr_ty = y + 65
            if not day_items.empty:
                for _, row in day_items.iterrows():
                    t_val, title_val = str(row['時間']), str(row['タイトル'])
                    if t_val and t_val != "nan":
                        draw.text((x + 20, curr_ty), t_val, font=get_font(20), fill=(100, 100, 100, 255))
                        curr_ty += 25
                    if title_val and title_val != "nan":
                        t_f_size = config.get("title_font_size", 22)
                        draw.text((x + 20, curr_ty), title_val[:12], font=get_font(t_f_size), fill=(60, 60, 60, 255))
                        curr_ty += t_f_size + 5

    footer_y, f_size = last_y + 60, config.get("footer_font_size", 35)
    lines = config.get("footer_text", "").split("\n")
    for i, line in enumerate(lines):
        line_y = footer_y + (i * (f_size + 15))
        if i == 0 and os.path.exists(FOOTER_PAW_FILE):
            try:
                paw_img = Image.open(FOOTER_PAW_FILE).convert("RGBA")
                icon_h = int(f_size * 1.5)
                icon_w = int(paw_img.width * (icon_h / paw_img.height))
                paw_img = paw_img.resize((icon_w, icon_h), Image.LANCZOS)
                img.paste(paw_img, (80, line_y - 10), paw_img)
                draw.text((80 + icon_w + 20, line_y), line, font=get_font(f_size + 5), fill=(0, 0, 0, 255))
            except: pass
        else:
            draw.text((80, line_y), line, font=get_font(f_size), fill=(0, 0, 0, 255))

    return img.convert("RGB")

# ================================
# メイン UI
# ================================
df = load_data()
config = load_config()

st.sidebar.title("🐾 設定・追加")

with st.sidebar.expander("🎨 見た目の調整"):
    config["stamp_size"] = st.slider("猫足の大きさ", 50, 150, int(config["stamp_size"]))
    config["title_font_size"] = st.slider("タイトル文字サイズ", 15, 40, int(config["title_font_size"]))
    config["footer_font_size"] = st.slider("脚注文字サイズ", 20, 100, int(config["footer_font_size"]))
    if st.button("設定を保存"): save_config(config); st.success("保存完了")

with st.sidebar.expander("📅 予定の追加", expanded=True):
    target_date = st.date_input("日付", date.today())
    is_open = st.checkbox("営業日（猫足を表示）", value=True)
    
    # --- 時間設定のプルダウン化 ---
    time_mode = st.radio("入力方法", ["プルダウンで選択", "自由入力", "指定なし"], horizontal=True)
    
    if time_mode == "プルダウンで選択":
        h_list = [f"{i:02d}:00" for i in range(8, 23)] + [f"{i:02d}:30" for i in range(8, 23)]
        h_list.sort()
        
        col_start, col_end = st.columns(2)
        start_t = col_start.selectbox("開始時間", h_list, index=h_list.index("13:00"))
        end_t = col_end.selectbox("終了時間", h_list, index=h_list.index("17:00"))
        t_input = f"{start_t}-{end_t}"
    elif time_mode == "自由入力":
        t_input = st.text_input("時間を入力 (例: 13:00-17:00)")
    else:
        t_input = ""
        
    title_input = st.text_input("予定タイトル")
    
    if st.button("カレンダーに追加"):
        new_row = pd.DataFrame([{"id": int(pd.Timestamp.now().timestamp()), "日付": target_date.strftime("%Y-%m-%d"), "時間": t_input, "タイトル": title_input, "スタンプ": is_open}])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df); st.rerun()

# 削除・メイン表示
if not df.empty:
    with st.sidebar.expander("🗑 予定の削除"):
        for idx, row in df.sort_values("日付").iterrows():
            c = st.columns([3, 1])
            if c[1].button("❌", key=f"del_{row['id']}"):
                df = df[df["id"] != row["id"]]; save_data(df); st.rerun()
            c[0].write(f"{row['日付']} {row['タイトル']}")

st.title("FUJIHARACOFFEEカレンダー")
c1, c2 = st.columns(2)
y_v = c1.number_input("年", 2024, 2030, 2026)
m_v = c2.selectbox("月", range(1, 13), index=date.today().month - 1)

final_img = create_calendar_image(y_v, m_v, df, config)
st.image(final_img, use_container_width=True)

buf = BytesIO()
final_img.save(buf, format="JPEG", quality=95)
st.download_button("🎨 画像をダウンロード", buf.getvalue(), f"calendar_{y_v}_{m_v}.jpg", "image/jpeg")