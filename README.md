# ⛰️ 登山お天気計画アプリ

山名を入力するだけで、過去70年以上の気象データと標高情報から、  
「登山におすすめの日」を自動で比較・提案してくれる Streamlit アプリです。

デプロイ先：

https://weatherapp-arsw4doe4d3kgn5cnhurrc.streamlit.app/

---

## アプリ概要

このアプリでは、入力した山や場所について以下を自動で取得・分析します。

- 地名から緯度・経度を自動取得
- 過去70年以上の気象データを取得
- 標高データを取得
- 山頂の予想気温を計算
- 晴れやすさ・日照時間・気温から「登山おすすめスコア」を算出

指定期間の中で、最も登山に適した日を表示します。

---

## 使用技術

- Python
- Streamlit
- Pandas
- Requests
- Geopy
- Open-Meteo API

---

## 必要ライブラリ

以下をインストールしてください。

```bash
pip install streamlit pandas requests geopy

```