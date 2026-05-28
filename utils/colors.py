"""共通カラーパレット — ブルー系統で統一"""

# 自支店・メイン系列
SELF      = "#1a3a6b"   # 濃紺（自支店・強調）
PRIMARY   = "#2563a8"   # 中青（メイン系列）
MID       = "#4a90d9"   # 青（第3系列）
LIGHT     = "#7fb3e8"   # 薄青（第4系列 / 中央値・比較）
PALE      = "#b8d9f7"   # 淡青（前年・背景比較）

# 他支店・ベンチマーク
OTHER     = "#b0b8c8"   # グレー青（他支店・参照線）
GRAY      = "#d0d0d0"   # 薄グレー

# アラート（青系とは別に維持）
WARNING   = "#e08c00"   # アンバー
CRITICAL  = "#c0392b"   # レッド
OK        = "#27ae60"   # グリーン（正常）

# カテゴリ用シーケンス（最大5区分）
BLUES_5 = [SELF, PRIMARY, MID, LIGHT, PALE]

# plotly に渡す用（color_discrete_sequence）
CATEGORY_SEQ = BLUES_5
