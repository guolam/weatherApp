import pandas as pd
import requests
import streamlit as st
from geopy.geocoders import Nominatim

# ==========================================
# 画面の基本設定
# ==========================================
st.set_page_config(page_title="登山お天気計画アプリ", page_icon="⛰️", layout="centered")

st.title("⛰️ 登山特化型・お天気計画アプリ")
st.write("過去10年の気象データから、複数の候補日でどこが一番安全・快適かを比較します。")

# ==========================================
# 入力エリア（サイドバーとメイン画面）
# ==========================================
st.header("1. 条件を入力")

# 場所の入力
place_input = st.text_input("調べたい山や場所の名前", value="英彦山")

# 複数日付の入力
st.write("📅 比較したい日付を最大3つ選んでください：")
col1, col2, col3 = st.columns(3)
with col1:
    date1 = st.date_input("候補日 1", value=pd.to_datetime("2026-05-30"))
with col2:
    date2 = st.date_input("候補日 2", value=pd.to_datetime("2026-05-31"))
with col3:
    date3 = st.date_input("候補日 3", value=pd.to_datetime("2026-06-06"))

# 計算開始ボタン
if st.button("過去の天気を計算・比較する", type="primary"):

    # ==========================================
    # 座標の取得（シンプルに日本語のまま渡す！）
    # ==========================================
    with st.spinner(f"『{place_input}』の座標を検索中..."):
        try:
            # 新しい識別名で検索ツールを起動
            geolocator = Nominatim(user_agent="my_climbing_weather_app_v4")
            # 変換を挟まず、入力された文字をそのまま渡す
            location = geolocator.geocode(place_input)

            if location is None:
                st.error(
                    f"『{place_input}』が見つかりませんでした。別の名前（例: 福岡県、英彦山など）で試してください。"
                )
                st.stop()
                
            latitude = location.latitude
            longitude = location.longitude
            
        except Exception as e:
            st.error(f"座標取得エラー: {e}")
            st.stop()

    # ==========================================
    # 気象データの取得 (過去10年分)
    # ==========================================
    with st.spinner("過去10年分のデータをダウンロード中..."):
        start_date = "2016-01-01"
        end_date = "2026-05-01"
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,precipitation_sum,sunshine_duration&timezone=Asia%2FTokyo"

        try:
            response = requests.get(url)
            df = pd.DataFrame(response.json()["daily"])
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
    df["晴れカウント"] = (df["降水量"] == 0).astype(int)
    df["月"] = df["年月日"].dt.month
    df["日"] = df["年月日"].dt.day

    # 統計（平均）を計算
    calendar_stats = (
        df.groupby(["月", "日"])
        .agg(
            晴れ確率_割=("晴れカウント", "mean"),
            平均最高気温=("最高気温", "mean"),
            平均日照時間=("日照時間", "mean"),
        )
        .reset_index()
    )
    calendar_stats["晴れ確率(%)"] = calendar_stats["晴れ確率_割"] * 100

    # スコア計算
    calendar_stats["登山おすすめスコア"] = (
        calendar_stats["晴れ確率(%)"] * 1.5 + calendar_stats["平均日照時間"] * 5
    )

    # ==========================================
    # 複数日の比較処理
    # ==========================================
    st.header("2. 比較結果")
    st.success(f"📍 {location.address}（緯度: {latitude:.2f}, 経度: {longitude:.2f}）")

    target_dates = [date1, date2, date3]
    results_list = []

    for d in target_dates:
        stats = calendar_stats[
            (calendar_stats["月"] == d.month) & (calendar_stats["日"] == d.day)
        ]
        if not stats.empty:
            row = stats.iloc[0]
            results_list.append(
                {
                    "日程": f"{d.month}月{d.day}日",
                    "晴れ確率": f"{row['晴れ確率(%)']:.1f}%",
                    "平均最高気温": f"{row['平均最高気温']:.1f}度",
                    "平均日照時間": f"{row['平均日照時間']:.1f}時間",
                    "スコア": row["登山おすすめスコア"],
                }
            )

    res_df = pd.DataFrame(results_list)
    best_idx = res_df["スコア"].idxmax()
    best_date = res_df.loc[best_idx, "日程"]

    st.balloons()  # お祝い風船
    st.markdown(
        f"### 🏆 過去の統計上、一番おすすめなのは **【{best_date}】** です！"
    )

    st.subheader("📊 詳細な比較データ")
    st.table(res_df[["日程", "晴れ確率", "平均最高気温", "平均日照時間"]])

    st.info(
        "💡 **山の注意点:** 気温は平地のものです。標高が1000m上がると気温は約6度下がりますので、防寒着の準備を忘れずに！"
    )