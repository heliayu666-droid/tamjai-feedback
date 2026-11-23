"""UI strings for the standalone page, in three languages."""

THEME_TRAD = {
    "queue": "排隊輪候", "cleanliness": "衛生環境", "service_attitude": "服務態度",
    "taste": "口味品質", "price": "價格性價比", "portion": "分量",
    "opening_hours": "營業時間／結業", "delivery_delay": "外送延誤",
    "delivery_missing": "漏送缺品", "staff_behaviour": "員工行為",
    "menu_availability": "貨品供應", "other": "其他",
}

TRAD = {
    "title": "顧客回饋中心",
    "tabs": ["今日工作", "待回覆", "已處理", "匯入數據", "趨勢分析", "分店表現"],

    "hero_lead": "{pending_neg} 則投訴待跟進 · {backlog} 則擱置超過一週",
    "hero_sub": "最久 {oldest_days} 日 · 集中在 {oldest_platform}",

    "m_complaints": "投訴待回覆", "m_complaints_s": "",
    "m_overweek": "已擱置超過一週", "m_overweek_s": "",
    "m_crisis": "需即時轉交營運", "m_crisis_s": "食安／過敏／法律",
    "m_praise": "正面評價可致謝", "m_praise_s": "",

    "h_by_platform": "各平台尚有幾多待回覆",
    "h_hot": "本週討論重點",
    "tip": "<b>先處理：</b>{backlog} 則擱置超過一週 · {crisis_live} 則食安",
    "waited": "中位已擱 {n} 日", "of_which": "其間投訴 {n} 則",

    "f_platform": "全部平台", "f_kind": "全部性質", "f_theme": "全部主題", "unclassified_option": "未分類",
    "assign": "歸類…",
    "feed_newsrc": "其他平台名稱…", "feed_addplat": "新增平台",
    "feed_platok": "已加入平台「{n}」",
    "feed_dupplat": "該平台已在清單中。", "feed_noplatform": "請先輸入平台名稱。",
    "add_theme": "新增主題分類", "add_theme_ask": "輸入新的主題名稱（例如：湯底濃淡、外卖灑漏）",

    "f_crisis_only": "只看需轉營運", "f_search": "搜尋分店或關鍵字…",
    "kind_all": "全部性質", "kind_neg": "投訴", "kind_pos": "讚好", "kind_neu": "中性",
    "shown": "顯示 {a} / {b} · 已跟進 {c}",

    "score": "優先分", "waiting": "擱置 {n} 日", "reliability": "可靠度",
    "conf": {"high": "高", "medium": "中", "low": "低"},
    "no_store": "未有提及分店", "no_text": "（僅提供評分，未附文字）", "untagged": "未分類",
    "btn_reply": "擬稿回覆", "btn_esc": "轉交營運", "btn_mon": "繼續觀察", "btn_dis": "暫不處理",
    "view_source": "查看原文",
    "badge_crisis": "🔴 需即時轉交營運", "badge_neg": "⚠ 投訴",
    "badge_pos": "✅ 讚好", "badge_neu": "○ 中性",
    "done_reply": "草稿已備妥，請由本人貼上平台", "done_esc": "已列入本週營運簡報",
    "done_mon": "保留於觀察名單", "done_dis": "已標記為暫不處理",
    "demo_note": "演示版不儲存內容，亦不會發布",

    "ins_note": "{written} 則投訴寫明了原因（另有 {silent_negative} 則只給星級）",
    "ins_reasons": "投訴原因分佈",
    "ins_cross": "各平台主要投訴類型",
    "ins_latency": "投訴等待時間",

    "map_h": "各分店投訴比率",
    "map_unlocated": "<b>{unlocated} 則未註明分店</b>（{pct}%），未計入地圖",
    "map_worst": "最需要關注的分店",
    "map_cols": ["分店", "評論數", "投訴", "投訴比率", "最新一則"],
    "ago": "{n} 日前",
    "legend_size": "圓越大＝評論越多", "legend_colour": "顏色越深代表投訴比率越高",

    "updated": "資料更新",
    "lang_label": "語言",
    "unit": "則",
    "all_option": "全部",
    "done_h": "已處理", "done_empty": "尚無處理記錄",
    "more_than": "另有", "clear_done": "清除記錄",
    "clear_confirm": "確定要清除所有處理記錄？這不會影響原始數據。",
    "feed_h": "匯入新數據",
    "feed_intro": "新評論加入待辦佇列 · 資料在本機解析，不會上傳",
    "feed_paste": "直接貼上", "feed_file": "上傳 CSV 檔案",
    "feed_ph": "每行一則：平台,日期,分店,內容\nOpenRice,2026-11-20,Mong Kok,等候一小時才排位…",
    "feed_go": "加入佇列", "feed_tpl": "下載 CSV 範本",
    "feed_ok": "已加入 {n} 則", "feed_none": "未識別到有效行。請確認格式為：平台,日期,分店,內容",
    "feed_empty": "請先貼上內容或選擇檔案。", "feed_nofile": "請選擇一個 CSV 檔案。",
    "feed_note": "格式：平台,日期,分店,內容（首行標題會自動忽略）",

    "brand_short": "譚仔",
    "draft_title": "建議回覆（兩種語氣）",
    "draft_rules": "主題：{n}",
    "v_warm": "親切口語", "v_formal": "正式書面",
    "copy": "複製", "copied": "已複製 ✓", "copy_fail": "請手動選取複製",
    "draft_hint": "複製後由你本人貼上平台",
    "map_note": "數字＝評論數 · 顏色＝投訴比率",
    "map_offline": "地圖需聯網載入，其餘不受影響",
    "legend_size": "圓越大＝評論越多",

    "map_h": "各分店投訴比率",
    "vm_compact": "緊湊", "vm_card": "卡片", "vm_table": "表格",
    "cols": ["平台", "分店", "日期", "優先分", "擱置日", "性質", "內容"],

    "b1": "一週內", "b2": "一至四週", "b3": "一至三個月",
}

EN = {
    "title": "Customer Feedback Centre",
    "tabs": ["Today's Work", "Awaiting Reply", "Handled", "Import Data", "Trends", "Branch Performance"],
    "hero_lead": "{pending_neg} complaints open · {backlog} waiting over a week",
    "hero_sub": "Oldest {oldest_days} days · mostly {oldest_platform}",
    "m_complaints": "Complaints open", "m_complaints_s": "",
    "m_overweek": "Waiting over a week", "m_overweek_s": "",
    "m_crisis": "Needs Operations now", "m_crisis_s": "Food safety, allergy or legal — never drafted",
    "m_praise": "Praise to acknowledge", "m_praise_s": "",
    "h_by_platform": "Open items by platform",
    "h_hot": "This week's themes",
    "tip": "<b>Priority:</b> {backlog} open over a week · {crisis_live} food-safety",
    "waited": "Median wait {n} days", "of_which": "{n} complaints among them",
    "f_platform": "All platforms", "f_kind": "All types", "f_theme": "All themes", "unclassified_option": "Uncategorised",
    "assign": "Categorise…",
    "feed_newsrc": "Other platform name…", "feed_addplat": "Add platform",
    "feed_platok": "Added platform \"{n}\" — now selectable below.",
    "feed_dupplat": "That platform is already listed.", "feed_noplatform": "Type a platform name first.",
    "add_theme": "Add a theme category", "add_theme_ask": "New theme name (e.g. broth strength, spillage)",

    "f_crisis_only": "Only items needing Operations", "f_search": "Search branch or keyword…",
    "kind_neg": "Complaint", "kind_pos": "Praise", "kind_neu": "Neutral",
    "shown": "Showing {a} of {b} items · {c} actioned this session",
    "score": "Priority", "waiting": "{n} days open", "reliability": "Read confidence",
    "conf": {"high": "High", "medium": "Medium", "low": "Low"},
    "no_store": "Branch not named", "no_text": "(rating only, no text)", "untagged": "Uncategorised",
    "btn_reply": "Draft reply", "btn_esc": "Escalate", "btn_mon": "Monitor", "btn_dis": "Dismiss",
    "view_source": "View source",
    "badge_crisis": "🔴 Needs Operations", "badge_neg": "⚠ Complaint",
    "badge_pos": "✅ Praise", "badge_neu": "○ Neutral",
    "done_reply": "Draft ready — post it yourself", "done_esc": "Added to this week's Operations brief",
    "done_mon": "Kept on watch list", "done_dis": "Marked as not acting",
    "demo_note": "Demo only: nothing stored, nothing published",
    "ins_note": "{written} complaints stated a reason ({silent_negative} were star-only)",
    "ins_reasons": "Stated complaint reasons",
    "ins_cross": "Main complaint types by platform",
    "ins_latency": "Complaint waiting time",
    "map_h": "Complaint rate by branch",
    "map_unlocated": "<b>{unlocated} posts name no branch</b> ({pct}%), excluded from the map",
    "map_worst": "Branches needing attention",
    "map_cols": ["Branch", "Reviews", "Complaints", "Complaint rate", "Latest"],
    "ago": "{n} days ago",
    "legend_size": "Larger circle = more reviews", "legend_colour": "Darker = higher complaint rate",
    "updated": "Data updated",
    "lang_label": "Language",
    "kind_all": "All types",
    "unit": "posts",
    "all_option": "All",
    "done_h": "Handled", "done_empty": "Nothing actioned yet. Items you act on in Awaiting Reply appear here.",
    "more_than": "Plus another", "clear_done": "Clear this session's log",
    "clear_confirm": "Clear all handling records? Original data is unaffected.",
    "feed_h": "Import new data",
    "feed_intro": "Add fresh public comments to the queue. Parsed locally; nothing is uploaded to any server.",
    "feed_paste": "Paste directly", "feed_file": "Upload CSV file",
    "feed_ph": "One row per line: platform,date,branch,text\nOpenRice,2026-11-20,Mong Kok,Waited an hour for a table…",
    "feed_go": "Add to queue", "feed_tpl": "Download CSV template",
    "feed_ok": "Added {n} comments to the queue.", "feed_none": "No valid rows found. Expected: platform,date,branch,text",
    "feed_empty": "Paste text or choose a file first.", "feed_nofile": "Please choose a CSV file.",
    "feed_note": "Format: platform,date(YYYY-MM-DD),branch,comment. A header row is ignored automatically.",

    "brand_short": "Tam Jai",
    "draft_title": "Suggested reply (two tones)",
    "draft_rules": "Generated from brand-voice rules · themes: {n}",
    "v_warm": "Warm / conversational", "v_formal": "Formal / written",
    "copy": "Copy", "copied": "Copied ✓", "copy_fail": "Select and copy manually",
    "draft_hint": "Copy it, then post it yourself",
    "map_note": "Number = reviews · colour = complaint rate",
    "map_offline": "Map tiles need a network connection. Other sections are unaffected.",
    "legend_size": "Larger circle = more reviews",

    "map_h": "Complaint rate by branch",
    "vm_compact": "Compact", "vm_card": "Cards", "vm_table": "Table",
    "cols": ["Platform", "Branch", "Date", "Priority", "Days open", "Type", "Text"],
    "b1": "Within a week", "b2": "One to four weeks", "b3": "One to three months",
}

def _build_langs():
    """Generate Simplified Chinese from Traditional using a vetted conversion table.

    An earlier version used a hand-written 128-character map. It silently produced mixed
    script — 待回覆 became 待回复 while 繼續觀察 stayed untouched — which is worse than not
    offering the option at all.
    """
    try:
        from zhconv import convert
    except ImportError:
        return {"zh-Hant": TRAD, "en": EN}     # degrade to two languages, never fake it

    def conv(v):
        if isinstance(v, str):
            return convert(v, "zh-hans")
        if isinstance(v, list):
            return [convert(x, "zh-hans") for x in v]
        if isinstance(v, dict):
            return {k: convert(x, "zh-hans") for k, x in v.items()}
        return v

    hans = {k: conv(v) for k, v in TRAD.items()}
    return {"zh-Hant": TRAD, "zh-Hans": hans, "en": EN}


LANGS = _build_langs()
