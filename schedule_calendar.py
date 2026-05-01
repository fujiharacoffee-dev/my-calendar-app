import os
import calendar
from datetime import date
from io import BytesIO
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- 基本設定 ---
st.set_page_config(page_title="FUJIHARACOFFEEカレンダー", layout="wide")
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DATA_FILE = os.path.join(APP_DIR, "schedule_data.xlsx")
CONFIG_FILE = os.path.join(APP_DIR, "config.xlsx") # コメント保存用
BG_IMAGE_FILE = os.path.join(APP_DIR, "ビアンコネーロ@4x-100.jpg")
STAMP_IMAGE_FILE = os.path.join(APP_DIR, "image_0d385a.png")

COLOR_MAP = {
    "標準（黒・グレー）": {"time": (100, 100, 100, 255), "title": (50, 50, 50, 255)},
    "赤色": {"time": (200, 50, 50, 255), "title": (200, 0, 0, 255)},
    "青色": {"time": (50, 50, 200, 255), "title": (0, 0, 200, 255)},
    "緑色": {"time": (50, 150, 50, 255), "title": (0, 120, 0, 255)},
    "茶色": {"time": (120, 80, 50, 255), "title": (100, 60, 30, 255)},
}

# --- データ管理 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE)
            return df
        except: pass
    return pd.DataFrame(columns=["id", "日付", "時間", "タイトル", "スタンプ", "サイズ", "位置X", "位置Y", "文字サイズ", "色設定"])

def save_data(df):
    df.to_excel(DATA_FILE, index=False)

# コメント設定の保存・読込
def load_config():
    if os.path.exists(CONFIG_FILE):
        try: return pd.read_excel(CONFIG_FILE).iloc[0].to_dict()
        except: pass
    return {"comment": "", "font_size": 40}

def save_config(conf):
    pd.DataFrame([conf]).to_excel(CONFIG_FILE, index=False)

@st.cache_data
def get_font(size):
    font_path = os.path.join(APP_DIR, "NotoSansCJKjp-Regular.otf")
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# --- 画像生成ロジック ---
def create_calendar_image(year, month, df, config, preview_data=None):
    width, height = 1800, 1550 # コメント欄のために高さを少し拡張
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    main_color = (138, 125, 106, 255)

    # 背景
    if os.path.exists(BG_IMAGE_FILE):
        try:
            bg = Image.open(BG_IMAGE_FILE).convert("RGBA")
            bg.thumbnail((1100, 1100))
            alpha = ImageEnhance.Brightness(bg.split()[3]).enhance(0.12)
            bg.putalpha(alpha)
            img.paste(bg, (width - bg.width - 40, height - bg.height - 350), bg)
        except: pass

    # 月・年
    draw.text((80, 40), str(month), font=get_font(180), fill=main_color)
    draw.text((320, 110), f"{year} {calendar.month_name[month]}", font=get_font(55), fill=main_color)

    # カレンダー本体
    start_y, cell_w, cell_h = 300, width // 7, 160
    cal = calendar.Calendar(firstweekday=0)
    for r, week in enumerate(cal.monthdatescalendar(year, month)):
        for c, d in enumerate(week):
            x, y = c * cell_w, start_y + r * cell_h
            day_str = d.strftime("%Y-%m-%d")
            draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(235, 235, 235, 255))
            d_fill = main_color if d.month == month else (215, 215, 215, 255)
            draw.text((x + 20, y + 15), str(d.day), font=get_font(35), fill=d_fill)
            
            day_items = df[df["日付"].astype(str) == day_str] if not df.empty else pd.DataFrame()
            
            # 猫足描画
            show_stamp = False
            s_size, pos_x, pos_y = 100, 50, 50
            if preview_data and preview_data["日付"] == day_str and preview_data["スタンプ"]:
                show_stamp, s_size, pos_x, pos_y = True, preview_data["サイズ"], preview_data["位置X"], preview_data["位置Y"]
            elif not day_items.empty:
                stamps = day_items[day_items["スタンプ"] == True]
                if not stamps.empty:
                    show_stamp, s_size, pos_x, pos_y = True, stamps.iloc[0].get('サイズ', 100), stamps.iloc[0].get('位置X', 50), stamps.iloc[0].get('位置Y', 50)
            
            if show_stamp and os.path.exists(STAMP_IMAGE_FILE):
                st_img = Image.open(STAMP_IMAGE_FILE).convert("RGBA").resize((int(s_size), int(s_size*0.85)), Image.LANCZOS)
                img.paste(st_img, (int(x+(cell_w*pos_x/100)-st_img.width//2), int(y+(cell_h*pos_y/100)-st_img.height//2)), st_img)

            # テキスト描画
            if not day_items.empty:
                curr_ty = y + 65
                for _, row in day_items.iterrows():
                    colors = COLOR_MAP.get(row.get('色設定', "標準（黒・グレー）"), COLOR_MAP["標準（黒・グレー）"])
                    t_size = row.get('文字サイズ', 22)
                    if str(row['時間']) not in ["nan", ""]:
                        draw.text((x+20, curr_ty), str(row['時間']), font=get_font(int(t_size*0.8)), fill=colors["time"])
                        curr_ty += int(t_size*0.8)+5
                    if str(row['タイトル']) not in ["nan", ""]:
                        draw.text((x+20, curr_ty), str(row['タイトル'])[:12], font=get_font(int(t_size)), fill=colors["title"])
                        curr_ty += int(t_size)+5

    # --- 下部コメント欄 (猫足固定配置) ---
    footer_y = height - 120
    if os.path.exists(STAMP_IMAGE_FILE):
        footer_stamp = Image.open(STAMP_IMAGE_FILE).convert("RGBA").resize((80, 70), Image.LANCZOS)
        img.paste(footer_stamp, (80, footer_y - 10), footer_stamp)
    
    if config["comment"]:
        draw.text((180, footer_y), config["comment"], font=get_font(config["font_size"]), fill=(80, 70, 60, 255))

    return img.convert("RGB")

# --- UI ---
df = load_data()
conf = load_config()

st.title("🐾 FUJIHARACOFFEEカレンダー")

# サイドバー：コメント設定
with st.sidebar.expander("📝 下部コメント欄の設定", expanded=False):
    conf["comment"] = st.text_input("コメント内容", value=conf["comment"])
    conf["font_size"] = st.slider("コメントの文字サイズ", 20, 100, conf["font_size"])
    if st.button("コメントを保存"):
        save_config(conf)
        st.success("コメントを保存しました")

# サイドバー：予定追加
with st.sidebar.expander("📅 予定・猫足の追加", expanded=True):
    target_date = st.date_input("日付を選択", date.today())
    is_open = st.checkbox("猫足を配置する", value=False)
    indiv_s, indiv_x, indiv_y = 100, 50, 50
    t_font_size, selected_color, t_input, title_input = 22, "標準（黒・グレー）", "", ""

    if is_open:
        indiv_s = st.slider("サイズ", 30, 250, 100)
        indiv_x = st.slider("横位置", 0, 100, 50)
        indiv_y = st.slider("縦位置", 0, 100, 50)
    else:
        t_font_size = st.slider("文字サイズ", 10, 60, 22)
        selected_color = st.selectbox("文字の色", list(COLOR_MAP.keys()))
        time_mode = st.radio("入力形式", ["プルダウン", "自由入力", "なし"], horizontal=True)
        if time_mode == "プルダウン":
            h_list = sorted([f"{i:02d}:00" for i in range(8, 23)] + [f"{i:02d}:30" for i in range(8, 23)])
            sc1, sc2 = st.columns(2)
            t_input = f"{sc1.selectbox('開始', h_list, index=10)}-{sc2.selectbox('終了', h_list, index=18)}"
        elif time_mode == "自由入力": t_input = st.text_input("時間帯を入力")
        title_input = st.text_input("予定のタイトル")

    if st.button("保存して更新"):
        new_row = pd.DataFrame([{"id": int(pd.Timestamp.now().timestamp()), "日付": target_date.strftime("%Y-%m-%d"), "時間": t_input, "タイトル": title_input, "スタンプ": is_open, "サイズ": indiv_s, "位置X": indiv_x, "位置Y": indiv_y, "文字サイズ": t_font_size, "色設定": selected_color}])
        df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.rerun()

# 削除
if not df.empty:
    with st.sidebar.expander("🗑 削除"):
        for idx, row in df.sort_values("日付", ascending=False).iterrows():
            c = st.columns([4, 1])
            if c[1].button("❌", key=f"del_{row['id']}"):
                df = df[df["id"] != row["id"]]; save_data(df); st.rerun()
            c[0].write(f"{row['日付']} {'🐾' if row['スタンプ'] else ''} {row['タイトル']}")

# カレンダー表示
col_y, col_m = st.columns(2)
y_v, m_v = col_y.number_input("年", 2024, 2030, date.today().year), col_m.selectbox("月", range(1, 13), index=date.today().month-1)
preview = {"日付": target_date.strftime("%Y-%m-%d"), "スタンプ": is_open, "サイズ": indiv_s, "位置X": indiv_x, "位置Y": indiv_y}
final_img = create_calendar_image(y_v, m_v, df, conf, preview_data=preview)
st.image(final_img, use_container_width=True)

buf = BytesIO()
final_img.save(buf, format="JPEG", quality=95)
st.download_button("🎨 カレンダー画像を保存", buf.getvalue(), f"fujihara_cal_{y_v}_{m_v}.jpg", "image/jpeg")