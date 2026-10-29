"""リールの色。施術ごとに背景色を変えて、グリッドで見分けやすくする。
bg: 濃い背景 / acc: 強調色(価格など) / tint: 明るい背景"""
PAL = {
    "botox":   dict(bg="#1E2A4A", acc="#FF8A65", tint="#E9EDF6"),   # ネイビー×コーラル
    "jaw":     dict(bg="#33224D", acc="#FFC857", tint="#EEE9F6"),   # パープル×イエロー
    "filler":  dict(bg="#0E4D55", acc="#FFD166", tint="#E2F0F0"),   # ティール×イエロー
    "booster": dict(bg="#5A1F3D", acc="#FF9EC4", tint="#F8E7EF"),   # ワイン×ピンク
    "spot":    dict(bg="#23433A", acc="#F6BD60", tint="#E6EFE9"),   # フォレスト×オレンジ
    "hair":    dict(bg="#3A2E2A", acc="#E9B872", tint="#F2ECE6"),
}
def get(grp):
    return PAL.get(grp, PAL["botox"])
