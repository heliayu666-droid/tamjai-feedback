"""Rule-based labelling engine.

This is C1 (sentiment + theme), C2 (priority) and C3 (crisis check) from PRD §5,
implemented as deterministic rules rather than LLM calls — which is exactly what the
PRD claims: batched, offline, reproducible, and explainable on screen.

The theme list is CLOSED by design (11 tags). Anything that fits none goes to "other"
for weekly human review, never into an invented tag.
"""
import re

# ---------------------------------------------------------------- themes (closed list)
THEMES = {
    "queue": [
        r"排隊", r"排咗", r"等位", r"輪候", r"冇枱", r"無枱", r"冇座位", r"等咗?[一二三四五六七八九十半0-9]+.*(個?鐘|分鐘|min)",
        r"waiting", r"queue", r"wait(ed)? .{0,12}(min|hour|long)", r"no seat", r"table .{0,8}empty",
        r"人龍", r"迫到", r"爆場", r"唔夠位",
    ],
    "cleanliness": [
        r"dirty", r"unclean", r"髒", r"污糟", r"蟻", r"蟑螂", r"蒼蠅", r"塵", r"油積",
        r"筷.{0,4}(霉|毛|脏)", r"紙巾盒", r"台面", r"枱面", r"卫生", r"衛生",
    ],
    "service_attitude": [
        r"態度", r"服務員.{0,6}(唔理|冇理|冷淡|惡|黑面|當唔到)", r"staff.{0,14}(rude|unhelpful|ignor|attitude)",
        r"冇人理", r"無人理", r"唔睬", r"差勁嘅服務", r"service was (bad|poor|terrible)",
        r"客服", r"職員", r"店員.{0,6}(態|唔)", r"callous",
    ],
    "taste": [
        r"好味", r"唔好味", r"難食", r"好食", r"好吃", r"湯底", r"濃(淡|度)", r"太鹹", r"太淡",
        r"味精", r"鮮味", r"tasty", r"delicious", r"yummy", r"nicely flavou", r"flavour",
        r"味道", r"米線.{0,6}(腍|爛|硬|彈)", r"生麵", r"求其",
    ],
    # Bare "平" matches "平時" (usually) and "平價" (good value); bare "貴" appears inside
    # "寶貴" and "難得臨貴". Require the evaluative forms instead.
    "price": [
        r"太貴", r"過貴", r"好貴", r"貴得離譜", r"加價", r"唔抵", r"不值", r"性價比",
        r"抵食", r"昂貴", r"expensive", r"overpriced", r"price[y]? (rise|hike)",
        r"价钱.{0,4}贵", r"價格.{0,4}貴", r"value for money",
    ],
    "portion": [
        r"分量", r"份量大?", r"太少", r"唔够", r"不够", r"small portion", r"portion size",
        r"肉少", r"餸少", r"得幾件", r"唔飽", r"吃不饱", r"scant",
    ],
    "opening_hours": [
        r"結業", r"倒閉", r"收市", r"關埋", r"開到", r"營業時間", r"closing", r"shut down",
        r"permanently closed", r"gone", r"執笠", r"冇開", r"装修", r"翻新",
    ],
    "delivery_delay": [
        r"外賣.{0,10}(慢|遲|耐|凍|凉)", r"送得?(慢|遲)", r"遲到", r"delivery.{0,14}(late|slow|cold)",
        r"took .{0,10}(hour|long)", r"逾時", r"超時", r"延誤", r"等了?[一二三]個鐘.*外卖",
    ],
    # Delivery themes require explicit delivery or order context. A bare "少咗" also occurs
    # inside "妖左我" and "少辣" (mild spice), and a bare "缺" inside "缺點". An earlier
    # version using those loose forms produced 1,472 false delivery complaints on dine-in reviews.
    "delivery_missing": [
        r"外賣.{0,14}(漏|少咗|冇|缺|忘|無)", r"(漏送|漏咗|少了|漏了).{0,6}(餐具|湯|汤|酱|醬|飯|饭|料|飲品)",
        r"missing item", r"forgot to (include|add)", r"incomplete order", r"wrong item sent",
        r"冇附.{0,6}(餐具|湯|酱)", r"冇餐具", r"少咗[一二三四]樣嘢",
        r"(order|delivery) .{0,12}was (incomplete|missing|wrong)",
    ],
    "staff_behaviour": [
        r"員工", r"同事.{0,6}(态度|態度|唔)", r"manager", r"店长", r"店長", r"worker",
        r"discriminat", r"歧視", r"吼", r"鬧(?:客|人)", r"粗言",
    ],
    "menu_availability": [
        r"售罄", r"卖晒", r"賣晒", r"冇[晒煞]", r"sold out", r"run out", r"断货", r"失蹤",
        r"下架", r"停產", r"限量", r"搶完", r"新品.{0,6}(試|食)",
    ],
}
_THEMES_COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in THEMES.items()}

# ---------------------------------------------------------------- crisis patterns (C3 stage 1)
CRISIS_PATTERNS = [
    r"食物中毒", r"食(到|完).{0,8}(嘢|野|東西|东西).{0,10}(病|吐|瀉|泻|不舒|肚)"
    , r"(肚屙|瀉肚|嘔吐|呕吐|嘔咗|肚痛|腸胃|肠胃)", r"入醫院", r"睇急症", r"見法官", r"食入院",
    r"(hospital|food poisoning|poisoned|vomit|got ill|got sick|foodborne|allergic reaction)",
    r"過敏.{0,10}(發作|休克|氣管|肿)", r"anaphyla", r"律師", r"法律行動", r"投訴委員會",
    r"(lawyer|legal action|sue\b|taking .* legal)", r"賠償", r"(compensation|refund demand)",
    r"衛生處", r"食環署.{0,8}(投訴|举报)", r"(rat|cockroach|insect).{0,12}(in my|found)",
    # A bare "蟲" must not be used: it matches 蟲草花 (cordyceps flower), a soup ingredient,
    # which locked a perfectly ordinary review as a food-safety incident. Require insect
    # context instead.
    r"(有|發現|見到|出入|埋).{0,4}蟲", r"蟲(入|喺|係|在).{0,8}(麵|面|飯|食|湯)",
    r"(worm|maggot|bug in my)", r"蟑螂", r"(頭髮|毛髮).{0,6}(入|喺).{0,6}(麵|面)",
]
_CRISIS_COMPILED = [re.compile(p, re.I) for p in CRISIS_PATTERNS]

# ---------------------------------------------------------------- sentiment lexicon
POS = [r"好味", r"好食", r"好吃", r"推薦", r"推荐", r"必食", r"正", r"抵食", r"心水", r"愛上",
       r"喜歡", r"喜欢", r"滿足", r"满足", r"讚", r"過癮", r"解饞", r"yummy", r"delicious",
       r"great", r"love[ds]?", r"amazing", r"best", r"recommend", r"nice", r"fantastic",
       r"好評", r"回访", r"回购", r"再来", r"下次", r"推介", r"魂", r"上癮"]
NEG = [r"難食", r"唔好食", r"不好吃", r"失望", r"差勁", r"差劲", r"頂唔順", r"唔會再", r"不會再",
       r"避免", r"avoid", r"terrible", r"awful", r"disappoint", r"worst", r"bad ", r"poor ",
       r"angry", r"annoy", r"refuse", r"never again", r"too expensive", r"過貴", r"太貴",
       r"唔值得", r"不值", r"投诉", r"投訴", r"火大", r"嬲", r"激", r"黑面", r"陰沉",
       r"唔衛生", r"不卫生", r"求其", r"敷衍", r"when .{0,10}cold", r"落雨", r"趕客"]
_SARCASM = [r"好快呀", r"真係好快", r"服務真係一流", r"好棒喔", r"真利害", r"好犀利", r"一流",
            r"so quick", r"great service", r"wonderful", r"impressive"]
_NEG_CONTEXT = [r"個?鐘", r"分鐘", r"未嚟", r"没来", r"未上", r"冇上", r"等到", r"排咗", r"都未", r"還沒"]

_pos_c = [re.compile(p, re.I) for p in POS]
_neg_c = [re.compile(p, re.I) for p in NEG]
_sar_c = [re.compile(p, re.I) for p in _SARCASM]
_negctx_c = [re.compile(p, re.I) for p in _NEG_CONTEXT]


def detect_lang(text: str) -> str:
    """Coarse script detection: enough to route Cantonese/Mandarin/English reporting."""
    t = text or ""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if cjk == 0 and lat == 0:
        return "unknown"
    cantonese_markers = any(m in t for m in ["嘅", "唔", "咗", "冇", "佢", "嘢", "俾", "噃", "嗰", "咁"])
    if cjk >= lat:
        return "zh-HK (Cantonese)" if cantonese_markers else "zh (written Chinese)"
    return "en"


# ---------------------------------------------------------------- relevance gate
# Searching "譚仔" returns more than the noodle chain. On Threads it also returns chatter
# about 譚朱凌鋒, son of the murdered socialite 蔡天鳳, whose media nickname is literally
# "譚仔". Those posts are not customer feedback and must not be counted as praise or
# complaint. We require a food/branch context signal, an explicit brand form, or that the
# record already came from a branch-bound page (OpenRice, Google Maps).
BRAND_STRONG = re.compile(r"譚仔雲南|谭仔云南|Tam ?Jai|Tams ?Jai|譚仔米線|谭仔米线|譚仔三哥")
FOOD_CONTEXT = re.compile(
    r"米線|米线|湯底|汤底|酸辣|豬潤|猪润|叉燒|叉烧|茶記|椒鹽|涼瓜|柠檬汁|檸檬汁|豆卜|腩肉|"
    r"外賣|外卖|noodle|restaurant|分店|店鋪|舖位|食飯|開飯|午膳|晚膳|晚餐|午餐|自助餐|buffet|"
    r"排队|排隊|取餐|外送|埋單|埋单", re.I)
MURDER_CTX = re.compile(
    r"蔡天鳳|蔡天凤|Abby ?Choi|崔麗心|崔丽心|陳港品|陈港品|鄺氏|邝氏|鄺家|邝家|洗黑錢|洗黑钱|"
    r"謀殺|谋杀|碎屍|碎尸|審訊|审讯|聽審|听审|判處|判处|遺照|遗照|龍尾|大埔.{0,6}龍尾|"
    r"遇人不淑|毀屍|灭口|人證|供稱|控方|辯方|案件審|綑屍|iron ?maiden|"
    r"律師.{0,14}盤問|盤問.{0,14}律師")


def is_relevant(text: str, store: str = "") -> bool:
    """Decide whether a post is about this chain rather than merely about food.

    Two failure modes had to be handled, and they pull in opposite directions:
      • 譚仔 also names the defendant's son in the 蔡天鳳 trial — pure noise, must go.
      • Xiaohongshu eating-tour roundups mention five restaurants and sometimes never say
        譚仔; matching them on generic food words alone put them into the queue as feedback
        about us. So free-text sources require an explicit brand mention, while records that
        already came from a branch page (OpenRice, Google Maps) need no keyword at all.
    """
    t = text or ""
    # The case content names 譚仔 because the defendant's son is nicknamed that, and some
    # posts also mention 譚仔米線 in hashtag lists. So a brand mention must NOT rescue a
    # post that is clearly about the trial — the trial signal wins.
    if MURDER_CTX.search(t):
        return False
    # Branch-bound sources are relevant by construction.
    if store and str(store).strip():
        return True
    # Free-text sources must name the brand.
    return bool(BRAND_STRONG.search(t))


def label(text: str, rating: str | None = None, stars: int | None = None,
             store: str = ""):
    """Return dict of sentiment, intensity, themes, urgency, crisis flag, confidence."""
    t = (text or "").strip()
    low = t.lower()

    # ---- themes
    hits = []
    for name, pats in _THEMES_COMPILED.items():
        if any(p.search(low) for p in pats):
            hits.append(name)

    # ---- crisis (stage 1: keyword/pattern)
    crisis = any(p.search(low) for p in _CRISIS_COMPILED)

    # ---- sentiment, with explicit sarcasm handling
    pos = sum(1 for p in _pos_c if p.search(low))
    neg = sum(1 for p in _neg_c if p.search(low))
    sarcastic = any(p.search(low) for p in _sar_c) and any(p.search(low) for p in _negctx_c)

    if crisis:
        senti = "negative"
    elif sarcastic:
        senti = "negative"
    elif pos > neg:
        senti = "positive"
    elif neg > pos:
        senti = "negative"
    elif stars is not None:
        senti = "positive" if stars >= 4 else ("neutral" if stars == 3 else "negative")
    elif rating:
        r = str(rating)
        senti = "positive" if "笑" in r else ("negative" if "哭" in r else "neutral")
    else:
        senti = "neutral"

    # ---- intensity 1..5
    excl = t.count("!") + t.count("！") + len(re.findall(r"[A-Z]{4,}", t))
    intensity = 1
    if senti != "neutral":
        intensity += min(2, max(pos, neg))
    if excl:
        intensity += 1
    if crisis:
        intensity = 5
    intensity = max(1, min(5, intensity))

    # ---- urgency
    if crisis:
        urgency = "high"
    elif senti == "negative" and intensity >= 4:
        urgency = "high"
    elif senti == "negative":
        urgency = "medium"
    else:
        urgency = "low"

    # ---- confidence: how much evidence we actually had
    ev = pos + neg + len(hits) + (1 if stars is not None else 0) + (1 if rating else 0)
    conf = "high" if ev >= 3 else ("medium" if ev >= 1 else "low")
    if len(t) < 8:
        conf = "low"

    # ---- one-line summary
    if not t:
        summ = f"{senti} · star-only rating ({stars if stars is not None else 'n/a'})"
    else:
        summ = (t[:110] + "…") if len(t) > 110 else t

    relevant = is_relevant(t, store)
    if not relevant:
        senti, urgency, hits, crisis, conf = "irrelevant", "none", [], False, "low"
    return dict(relevant=relevant, sentiment=senti, intensity=intensity,
                themes=hits or (["other"] if senti == "negative" else []),
                urgency=urgency, crisis=crisis, confidence=conf, lang=detect_lang(t),
                sarcastic=sarcastic, summary=summ)


def priority_score(intensity: int, days_open: float, engagement: int, crisis: bool) -> float:
    """C2 — plain arithmetic, deliberately not a model, so ranking is explainable.

    score = severity × how long unanswered × engagement lift, with a per-platform cap
    so one viral post cannot outrank a hygiene complaint.
    """
    sev = intensity * (2.2 if crisis else 1.0)
    # Age only counts up to 30 days and only lifts the score; beyond a month we cannot tell
    # whether a review is unanswered or simply historical, so it stops being a signal.
    age = 1.0 + min(days_open, 30) / 14.0
    eng = 1.0 + min(engagement, 500) / 250.0             # capped so virality cannot dominate
    return round(sev * age * eng, 2)
