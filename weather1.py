import datetime
import pandas as pd
import requests

# ==========================================
# 1. 過去30年分の気象データを取得
# ==========================================
print("過去30年分のデータを取得中...")
latitude = 30.3446  # 屋久島
longitude = 130.5127
start_date = "1996-01-01"
end_date = "2026-05-01"

url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,precipitation_sum,sunshine_duration&timezone=Asia%2FTokyo"

response = requests.get(url)
df = pd.DataFrame(response.json()["daily"])

# データの整形
df["年月日"] = pd.to_datetime(df["time"])
df["最高気温"] = df["temperature_2m_max"]
df["降水量"] = df["precipitation_sum"]
df["日照時間"] = [
    d / 3600 if d is not None else 0 for d in df["sunshine_duration"]
]

# 「雨が降らなかった（降水量0）」なら1、降ったら0にする
df["晴れカウント"] = (df["降水量"] == 0).astype(int)

# ==========================================
# 2. 「月」と「日」でグループ化して30年分の平均を出す
# ==========================================
df["月"] = df["年月日"].dt.month
df["日"] = df["年月日"].dt.day

# 特殊文字（℃など）を左側から排除して集計
calendar_stats = (
    df.groupby(["月", "日"])
    .agg(
        晴れ確率_割=("晴れカウント", "mean"),
        平均最高気温=("最高気温", "mean"),
        平均日照時間=("日照時間", "mean"),
    )
    .reset_index()
)

# 確率をパーセント(%)に変換
calendar_stats["晴れ確率"] = calendar_stats["晴れ確率_割"] * 100

# ==========================================
# 3. 平均的に「いい天気」のスコアを計算
# ==========================================
calendar_stats["天気安定スコア"] = (
    calendar_stats["晴れ確率"] + calendar_stats["平均日照時間"] * 5
)
ranked_calendar = calendar_stats.sort_values(
    by="天気安定スコア", ascending=False
)

# ==========================================
# 4. 結果の出力
# ==========================================
print("\n==========================================")
print("統計結果：過去30年のデータから見る『平均的にいい天気の日』")
print("==========================================\n")

print("--- 年間で最も晴れやすく快適な日 TOP 10 ---")
print(
    ranked_calendar.head(10).to_string(
        index=False,
        columns=["月", "日", "晴れ確率", "平均最高気温", "平均日照時間"],
        formatters={
            "晴れ確率": "{:.1f}%".format,
            "平均最高気温": "{:.1f}度".format,
            "平均日照時間": "{:.1f}時間".format,
        },
    )
)

print("\n------------------------------------------")
# 今日の日付（5月25日）のデータをピンポイントで検索
today = datetime.date.today()
today_stats = calendar_stats[
    (calendar_stats["月"] == today.month) & (calendar_stats["日"] == today.day)
]

if not today_stats.empty:
    row = today_stats.iloc[0]
    print(f"【今日（{today.month}月{today.day}日）の過去30年の統計データ】")
    print(f"・過去30年間の晴れ確率 : {row['晴れ確率']:.1f}%")
    print(f"・平均最高気温         : {row['平均最高気温']:.1f} 度")
    print(f"・平均日照時間         : {row['平均日照時間']:.1f} 時間")
print("------------------------------------------")