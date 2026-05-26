import datetime
import pandas as pd
import requests
import streamlit as st
from geopy.geocoders import Nominatim

# ==========================================
# 画面の基本設定
# ==========================================
st.set_page_config(page_title="登山お天気計画アプリ", page_icon="⛰️", layout="centered")

st.title("お天気計画アプリ")
st.write("山名を入力するだけで、過去70年の気象データと自動取得した標高から、山頂の天気を一発比較します。")

# ==========================================
# 入力エリア
# ==========================================
st.header("1. 条件を入力")

# 場所の入力
place_input = st.text_input("調べたい山や場所の名前", value="")

# 【変更】期間指定の入力（カレンダーで範囲を選択できるようにします）
st.write("📅 調べたい期間（開始日と終了日）を選んでください：")
today = datetime.date.today()
date_range = st.date_input(
    "検索期間",
    value=(today, today + datetime.timedelta(days=6)),  # 初期値は今日から1週間
)

# 計算開始ボタン
if st.button("過去の天気を計算・比較する", type="primary"):
    
    # 期間が正しく選択されているかチェック（開始と終了の両方が選ばれるまで待つ）
    if len(date_range) != 2:
        st.warning("開始日と終了日の両方を選択してください。")
        st.stop()
        
    start_date_input, end_date_input = date_range

    # ==========================================
    # 座標の自動取得
    # ==========================================
    with st.spinner(f"『{place_input}』の座標を検索中..."):
        try:
            geolocator = Nominatim(user_agent="my_climbing_weather_app_v7")
            location = geolocator.geocode(place_input)

            if location is None:
                st.error(f"『{place_input}』が見つかりませんでした。別の名前で試してください。")
                st.stop()
                
            latitude = location.latitude
            longitude = location.longitude
            
        except Exception as e:
            st.error(f"場所の検索エラー: {e}")
            st.stop()

    # ==========================================
    # 気象データと「標高」の取得 (過去70年分)
    # ==========================================
    with st.spinner("過去70年分の気象データと標高をダウンロード中..."):
        start_date = "1940-01-01"
        end_date = (pd.to_datetime("today") - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,precipitation_sum,sunshine_duration&timezone=Asia%2FTokyo"

        try:
            response = requests.get(url)
            res_json = response.json()
            df = pd.DataFrame(res_json["daily"])
            
            if "elevation" in res_json:
                elevation = float(res_json["elevation"])
            else:
                elevation = 0.0
                
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
            st.stop()

    # データの整形
    df["年月日"] = pd.to_datetime(df["time"])
    df["最高気温"] = df["temperature_2m_max"]
    df["降水量"] = df["precipitation_sum"]
    df["日照時間"] = [
        d / 3600 if d is not None else 0 for d in df["sunshine_duration"]
    ]
    df["晴れカウント"] = ((df["降水量"] < 1.0) & (df["日照時間"] >= 4.0)).astype(int)
    df["月"] = df["年月日"].dt.month
    df["日"] = df["年月日"].dt.day

    # 統計（平均）を計算
    calendar_stats = (
        df.groupby(["月", "日"])
        .agg(
            晴れ確率_割=("晴れカウント", "mean"),
            平均最高気温_平地=("最高気温", "mean"),
            平均日照時間=("日照時間", "mean"),
        )
        .reset_index()
    )
    calendar_stats["晴れ確率(%)"] = calendar_stats["晴れ確率_割"] * 100
    calendar_stats["山頂の予想最高気温"] = calendar_stats["平均最高気温_平地"] - (0.6 * (elevation / 100))

    # スコア計算
    def calculate_climbing_score(row):
        base_score = row["晴れ確率(%)"] * 1.5 + row["平均日照時間"] * 5
        mountain_temp = row["山頂の予想最高気温"]
        if 10 <= mountain_temp <= 18:
            base_score += 20
        elif mountain_temp < 5:
            base_score -= 20
        return base_score

    calendar_stats["登山おすすめスコア"] = calendar_stats.apply(calculate_climbing_score, axis=1)

    # ==========================================
    # 【変更】指定された期間の日付リストを作成して比較
    # ==========================================
    st.header("2. 比較結果")
    st.success(f"📍 {location.address}")
    st.info(f"⛰️ この場所の標高は **{elevation:.0f} m**")

    # 指定された開始日から終了日までの全日付を生成
    target_dates = pd.date_range(start=start_date_input, end=end_date_input)
    results_list = []

    for d in target_dates:
        stats = calendar_stats[
            (calendar_stats["月"] == d.month) & (calendar_stats["日"] == d.day)
        ]
        if not stats.empty:
            row = stats.iloc[0]
            # 曜日も分かると便利なので追加
            weekday_str = ["月", "火", "水", "木", "金", "土", "日"][d.weekday()]
            
            results_list.append(
                {
                    "日程": f"{d.month}月{d.day}日({weekday_str})",
                    "晴れ確率": f"{row['晴れ確率(%)']:.1f}%",
                    "平地の気温": f"{row['平均最高気温_平地']:.1f}度",
                    "⛰️山頂の気温": f"{row['山頂の予想最高気温']:.1f}度",
                    "平均日照時間": f"{row['平均日照時間']:.1f}時間",
                    "スコア": row["登山おすすめスコア"],
                }
            )

    if not results_list:
        st.error("選択された期間のデータが見つかりませんでした。")
        st.stop()

    res_df = pd.DataFrame(results_list)
    
    # 最もスコアが高い日を特定
    best_idx = res_df["スコア"].idxmax()
    best_date = res_df.loc[best_idx, "日程"]

    st.balloons()
    st.markdown(
        f"### 指定期間の中で一番おすすめは **【{best_date}】** です！"
    )

    st.subheader("📊 期間内の詳細データ一覧")
    # スコア列も含めて表示すると、なぜその日がお勧めなのか分かりやすくなります
    st.table(res_df[["日程", "晴れ確率", "平地の気温", "⛰️山頂の気温", "平均日照時間"]])

    # 動的なアドバイス
    best_mountain_temp = res_df.loc[best_idx, "⛰️山頂の気温"]
    temp_val = float(str(best_mountain_temp).replace("度", ""))

    st.info("ℹ️ **おすすめ日の装備アドバイス**")
    if temp_val < 10:
        st.warning(f"⚠️ 山頂は {temp_val:.1f}度 とかなり寒くなる予想です。防寒着（フリースやレインウェア）を必ずザックに入れておきましょう！")
    elif 10 <= temp_val <= 18:
        st.success(f"✨ 山頂は {temp_val:.1f}度 と、登るには最高のコンディションです！快適な山行を楽しんでください。")
    else:
        st.warning(f"☀️ 山頂でも {temp_val:.1f}度 と暑くなりそうです。水分をいつもより多めに持ち、熱中症に注意してください。")