import os
import calendar
from datetime import date
from io import BytesIO
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- 基本設定 ---
st.set_page_config(page_title="猫カフェ・カレンダーメーカー", layout="wide")
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DATA_FILE = os.path.join(APP_DIR, "schedule_data.xlsx")
CONFIG_FILE = os.path.join(APP_DIR, "app_config.xlsx")
BG_IMAGE_FILE = os.path.join(APP_DIR, "ビアンコネーロ@4x-100.jpg")
STAMP_IMAGE_FILE = os.path.join(APP_DIR, "image_0d385a.png")

# --- データ管理関数 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE)
            # 必要なカラムの欠損補完
            cols = ["id", "日付", "時間", "タイトル", "スタンプ", "サイズ", "位置X", "位置Y"]
            for col in cols:
                if col not in df.columns:
                    df[col] = 100 if col == "サイズ" else 50 if "位置" in col else False if col == "スタンプ" else ""
            return df
        except: pass
    return pd.DataFrame(columns=["id", "日付", "時間", "タイトル", "スタンプ", "サイズ", "位置X", "位置Y"])

def load_config():
    default_conf = {"footer_text": "営業時間...", "footer_font_size": 35, "stamp_size": 100, "title_font_size": 22}
    if os.path.exists(CONFIG_FILE):
        try: return pd.read_excel(CONFIG_FILE).iloc[0].to_dict()
        except: pass
    return default_conf

def save_data(df): df.to_excel(DATA_FILE, index=False)

@st.cache_data
def get_font(size):
    font_path = os.path.join(APP_DIR, "NotoSansCJKjp-Regular.otf")
    if os.path.exists(font_path): return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# --- 画像生成コアロジック ---
def create_calendar_image(year, month, df, config, preview_data=None):
    width, height = 1800, 1400 
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    main_color = (138, 125, 106, 255)

    # 1. 背景描画
    if os.path.exists(BG_IMAGE_FILE):
        try:
            bg = Image.open(BG_IMAGE_FILE).convert("RGBA")
            bg.thumbnail((1100, 1100))
            alpha = ImageEnhance.Brightness(bg.split()[3]).enhance(0.12)
            bg.putalpha(alpha)
            img.paste(bg, (width - bg.width - 40, height - bg.height - 250), bg)
        except: pass

    # 2. ヘッダーテキスト
    draw.text((80, 40), str(month), font=get_font(180), fill=main_color)
    draw.text((320, 110), f"{year} {calendar.month_name[month]}", font=get_font(55), fill=main_color)

    # カレンダー計算
    start_y, cell_w, cell_h = 300, width // 7, 160
    cal = calendar.Calendar(firstweekday=0)
    
    for r, week in enumerate(cal.monthdatescalendar(year, month)):
        for c, d in enumerate(week):
            x, y = c * cell_w, start_y + r * cell_h
            day_str = d.strftime("%Y-%m-%d")
            
            # 枠線と日付の描画
            draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(235, 235, 235, 255))
            d_fill = main_color if d.month == month else (215, 215, 215, 255)
            draw.text((x + 20, y + 15), str(d.day), font=get_font(35), fill=d_fill)

            # --- データの抽出 ---
            is_preview_day = (preview_data and preview_data["日付"] == day_str)
            day_items = df[df["日付"].astype(str) == day_str] if not df.empty else pd.DataFrame()

            # --- 3. 猫足（スタンプ）の描画 ---
            # プレビュー中または保存データにスタンプがある場合
            show_stamp = False
            s_size, pos_x, pos_y = 100, 50, 50
            
            if is_preview_day and preview_data["スタンプ"]:
                show_stamp = True
                s_size, pos_x, pos_y = preview_data["サイズ"], preview_data["位置X"], preview_data["位置Y"]
            elif not day_items.empty:
                stamp_rows = day_items[day_items["スタンプ"] == True]
                if not stamp_rows.empty:
                    show_stamp = True
                    row = stamp_rows.iloc[0]
                    s_size = row.get('サイズ', 100)
                    pos_x = row.get('位置X', 50)
                    pos_y = row.get('位置Y', 50)

            if show_stamp and os.path.exists(STAMP_IMAGE_FILE):
                try:
                    st_img = Image.open(STAMP_IMAGE_FILE).convert("RGBA")
                    st_img = st_img.resize((int(s_size), int(s_size * 0.85)), Image.LANCZOS)
                    # 指定位置（%）に基づいて中心を計算
                    px = int(x + (cell_w * (pos_x / 100)) - (st_img.width // 2))
                    py = int(y + (cell_h * (pos_y / 100)) - (st_img.height // 2))
                    img.paste(st_img, (px, py), st_img)
                except: pass
            
            # --- 4. 文字（時間・タイトル）の描画 ---
            # スタンプの有無に関わらず、文字があれば描画する
            if not day_items.empty:
                curr_ty = y + 65
                for _, row in day_items.iterrows():
                    t_val, title_val = str(row['時間']), str(row['タイトル'])
                    
                    if t_val and t_val not in ["nan", ""]:
                        draw.text((x + 20, curr_ty), t_val, font=get_font(20), fill=(100, 100, 100, 255))
                        curr_ty += 25
                    
                    if title_val and title_val not in ["nan", ""]:
                        t_size = config.get("title_font_size", 22)
                        # 文字色を少し濃くしてスタンプの上でも読みやすくする
                        draw.text((x + 20, curr_ty), title_val[:12], font=get_font(t_size), fill=(50, 50, 50, 255))
                        curr_ty += t_size + 5
                        
    return img.convert("RGB")

# --- メイン UI 処理 ---
df = load_data()
config = load_config()

st.sidebar.title("🐾 予定の編集")

with st.sidebar.expander("📅 予定・スタンプの追加", expanded=True):
    target_date = st.date_input("日付", date.today())
    is_open = st.checkbox("猫足を配置する", value=False)
    
    indiv_s, indiv_x, indiv_y = 100, 50, 50
    if is_open:
        st.caption("スタンプの微調整")
        indiv_s = st.slider("サイズ", 30, 250, 100)
        indiv_x = st.slider("左右位置", 0, 100, 50)
        indiv_y = st.slider("上下位置", 0, 100, 50)
    
    st.divider()
    
    # 時間入力
    time_mode = st.radio("時間入力", ["プルダウン", "自由入力", "なし"], horizontal=True)
    t_input = ""
    if time_mode == "プルダウン":
        h_list = sorted([f"{i:02d}:00" for i in range(8, 23)] + [f"{i:02d}:30" for i in range(8, 23)])
        c1, c2 = st.columns(2)
        t_input = f"{c1.selectbox('開始', h_list, index=10)}-{c2.selectbox('終了', h_list, index=18)}"
    elif time_mode == "自由入力":
        t_input = st.text_input("時間 (例: 13:00-17:00)")
    
    title_input = st.text_input("予定タイトル")
    
    if st.button("カレンダーに反映"):
        new_row = pd.DataFrame([{
            "id": int(pd.Timestamp.now().timestamp()), 
            "日付": target_date.strftime("%Y-%m-%d"), 
            "時間": t_input, 
            "タイトル": title_input, 
            "スタンプ": is_open,
            "サイズ": indiv_s, "位置X": indiv_x, "位置Y": indiv_y
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        st.rerun()

# 削除機能
if not df.empty:
    with st.sidebar.expander("🗑 予定の削除"):
        for idx, row in df.sort_values("日付", ascending=False).iterrows():
            c = st.columns([4, 1])
            label = f"{row['日付']} {'🐾' if row['スタンプ'] else ''} {row['タイトル']}"
            if c[1].button("❌", key=f"del_{row['id']}"):
                df = df[df["id"] != row["id"]]
                save_data(df)
                st.rerun()
            c[0].write(label)

# カレンダー表示エリア
st.title("猫カフェ カレンダーメーカー")
col_y, col_m = st.columns(2)
y_v = col_y.number_input("年", 2024, 2030, date.today().year)
m_v = col_m.selectbox("月", range(1, 13), index=date.today().month-1)

# プレビュー表示用のリアルタイムデータ
preview = {
    "日付": target_date.strftime("%Y-%m-%d"), 
    "スタンプ": is_open, 
    "サイズ": indiv_s, 
    "位置X": indiv_x, 
    "位置Y": indiv_y
}

final_img = create_calendar_image(y_v, m_v, df, config, preview_data=preview)
st.image(final_img, use_container_width=True)

# ダウンロード
buf = BytesIO()
final_img.save(buf, format="JPEG", quality=95)
st.download_button(
    label="🎨 カレンダー画像を保存",
    data=buf.getvalue(),
    file_name=f"calendar_{y_v}_{m_v}.jpg",
    mime="image/jpeg"
)