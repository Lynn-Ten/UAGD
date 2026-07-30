#!/usr/bin/env python3
"""Generate mid-century modern renovation drawings for Unit 05 (90.23㎡)."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)
ART = Path("/opt/cursor/artifacts/screenshots")
ART.mkdir(parents=True, exist_ok=True)

# Color palette — mid-century / 中古风
TEAK = (139, 90, 43)
WALNUT = (92, 64, 40)
CREAM = (245, 237, 222)
SAGE = (138, 154, 123)
OLIVE = (107, 112, 92)
MUSTARD = (196, 154, 72)
TERRACOTTA = (168, 98, 72)  # accent only, restrained
INK = (42, 38, 34)
PAPER = (252, 248, 240)
GRID = (210, 200, 185)
WALL = (55, 48, 40)
SOFT = (232, 222, 205)
WOOD_FLOOR = (186, 148, 98)
TILE = (200, 190, 175)
BALCONY = (220, 228, 220)
FIXTURE = (120, 110, 95)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def save(img, name):
    p1 = OUT / name
    p2 = ART / name
    img.save(p1, "PNG", optimize=True)
    img.save(p2, "PNG", optimize=True)
    print(f"saved {p1}")
    return p1


# Scale: 1m = 45px  |  origin at top-left of drawing area
SCALE = 45
OX, OY = 120, 160  # drawing origin


def m(x, y):
    """meters → pixels"""
    return (OX + int(x * SCALE), OY + int(y * SCALE))


def mr(x, y, w, h):
    x0, y0 = m(x, y)
    return [x0, y0, x0 + int(w * SCALE), y0 + int(h * SCALE)]


def draw_title(draw, w, title, subtitle):
    draw.rectangle([0, 0, w, 110], fill=WALNUT)
    draw.text((40, 28), title, fill=CREAM, font=font(36, True))
    draw.text((40, 72), subtitle, fill=SOFT, font=font(18))


def draw_legend_box(draw, x, y, items):
    draw.rectangle([x, y, x + 280, y + 28 + 26 * len(items)], fill=CREAM, outline=WALNUT, width=2)
    draw.text((x + 12, y + 6), "图例 LEGEND", fill=WALNUT, font=font(14, True))
    for i, (color, label) in enumerate(items):
        yy = y + 32 + i * 26
        draw.rectangle([x + 14, yy, x + 36, yy + 16], fill=color, outline=INK)
        draw.text((x + 46, yy - 1), label, fill=INK, font=font(13))


def draw_north(draw, x, y):
    draw.ellipse([x, y, x + 48, y + 48], outline=INK, width=2)
    draw.polygon([(x + 24, y + 6), (x + 18, y + 28), (x + 30, y + 28)], fill=INK)
    draw.text((x + 16, y + 52), "N", fill=INK, font=font(16, True))


# ---------------------------------------------------------------------------
# Unit outline geometry (meters) — reconstructed from architectural plan
# Overall ~11.2m (E-W) × ~9.0m (N-S incl. balconies)
# North notch for elevator4 + void ≈ 2.8m wide × 2.0m deep, centered-left
# ---------------------------------------------------------------------------
# Coordinate: x=0 left (west), y=0 top (north)

# Main interior rooms (proposed partition):
ROOMS = {
    # name: (x, y, w, h, area_label, fill)
    "玄关": (3.4, 2.0, 2.4, 1.8, "玄关 4.3㎡", SOFT),
    "厨房": (0.2, 2.0, 3.2, 3.0, "厨房 9.6㎡", (230, 210, 185)),
    "餐厅": (3.4, 3.8, 3.6, 2.4, "餐厅 8.6㎡", CREAM),
    "客厅": (3.4, 6.2, 4.4, 2.6, "客厅 11.4㎡", CREAM),
    "主卧": (0.2, 5.0, 3.2, 3.8, "主卧 12.2㎡", (235, 225, 210)),
    "次卧": (7.8, 2.0, 3.2, 3.6, "次卧 11.5㎡", (235, 225, 210)),
    "书房": (7.8, 5.6, 3.2, 3.2, "书房 10.2㎡", (228, 220, 205)),
    "卫生间": (5.8, 2.0, 2.0, 2.8, "卫生间 5.6㎡", (210, 218, 215)),
    "衣帽": (5.8, 4.8, 2.0, 1.4, "衣帽间 2.8㎡", SOFT),
    "半阳2": (0.2, 8.8, 3.2, 1.0, "半阳2", BALCONY),
    "半阳1": (7.0, 8.8, 4.0, 1.0, "半阳1", BALCONY),
}

# Exterior walls path (closed polygon in meters)
OUTER = [
    (0.0, 2.0), (3.4, 2.0), (3.4, 0.0), (6.2, 0.0), (6.2, 2.0),
    (11.2, 2.0), (11.2, 9.8), (7.0, 9.8), (7.0, 8.8), (3.4, 8.8),
    (3.4, 9.8), (0.0, 9.8), (0.0, 2.0),
]


def draw_unit_shell(draw, fill=PAPER):
    pts = [m(x, y) for x, y in OUTER]
    draw.polygon(pts, fill=fill, outline=WALL, width=4)


def draw_room_rects(draw, furniture=False):
    for name, (x, y, w, h, label, fill) in ROOMS.items():
        r = mr(x, y, w, h)
        draw.rectangle(r, fill=fill, outline=WALL, width=2)
        cx = (r[0] + r[2]) // 2
        cy = (r[1] + r[3]) // 2
        # label
        bbox = draw.textbbox((0, 0), label, font=font(14, True))
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, cy - 10), label, fill=INK, font=font(14, True))


def draw_doors_windows(draw):
    # Entrance door from elevator lobby (north of 玄关)
    x0, y0 = m(4.2, 2.0)
    draw.arc([x0 - 40, y0 - 40, x0 + 40, y0 + 40], 180, 270, fill=TEAK, width=3)
    draw.line([x0, y0, x0, y0 - 40], fill=TEAK, width=3)
    draw.text((x0 + 8, y0 - 55), "入户门", fill=TEAK, font=font(12))

    # Internal doors (simplified swing arcs)
    doors = [
        # kitchen
        (3.4, 3.2, 90),
        # bath
        (5.8, 3.2, 90),
        # master
        (3.4, 6.0, 90),
        # secondary
        (7.8, 3.5, 270),
        # study
        (7.8, 6.8, 270),
        # closet
        (5.8, 5.2, 90),
    ]
    for dx, dy, start in doors:
        px, py = m(dx, dy)
        draw.arc([px - 28, py - 28, px + 28, py + 28], start, start + 90, fill=FIXTURE, width=2)

    # South windows / balcony doors
    # Master → 半阳2
    draw.rectangle(mr(0.8, 8.8, 2.0, 0.08), fill=(140, 180, 200))
    # Living → south glass
    draw.rectangle(mr(4.0, 8.8, 2.4, 0.08), fill=(140, 180, 200))
    # Study → 半阳1
    draw.rectangle(mr(8.0, 8.8, 2.4, 0.08), fill=(140, 180, 200))
    # Living opens to balcony gap
    draw.rectangle(mr(3.4, 8.8, 3.6, 0.12), fill=TEAK)

    # North windows near notch (kitchen / bath light shafts limited)
    draw.rectangle(mr(1.0, 2.0, 1.5, 0.06), fill=(140, 180, 200))


def draw_adjacency_notes(draw):
    draw.text(m(3.6, 0.6), "电梯4 / 中空", fill=FIXTURE, font=font(12))
    draw.text(m(-1.8, 1.0), "强电2", fill=FIXTURE, font=font(12))
    draw.text(m(11.4, 1.0), "弱电水2", fill=FIXTURE, font=font(12))
    draw.text(m(-1.6, 5.5), "06套", fill=FIXTURE, font=font(13))
    draw.text(m(11.4, 5.5), "04套", fill=FIXTURE, font=font(13))
    draw.text(m(4.0, -0.7), "电梯厅兼前室2 →", fill=FIXTURE, font=font(13))


def draw_furniture(draw):
    """Mid-century furniture symbols."""
    # --- Living: sofa, coffee table, TV console, lounge chair ---
    # Sofa (teak frame)
    r = mr(4.0, 7.4, 2.6, 0.85)
    draw.rounded_rectangle(r, radius=6, fill=SAGE, outline=WALNUT, width=2)
    draw.text((r[0] + 30, r[1] + 8), "沙发 Sofa", fill=CREAM, font=font(11))
    # Coffee table oval
    ct = mr(4.5, 6.6, 1.4, 0.7)
    draw.ellipse(ct, fill=TEAK, outline=WALNUT, width=2)
    # TV console
    tv = mr(6.6, 6.4, 0.45, 1.8)
    draw.rectangle(tv, fill=WALNUT, outline=INK, width=1)
    # Lounge chair
    lc = mr(3.6, 6.4, 0.7, 0.7)
    draw.ellipse(lc, fill=MUSTARD, outline=WALNUT, width=2)

    # --- Dining: round table + 4 chairs ---
    dx, dy = m(5.0, 4.9)
    draw.ellipse([dx - 38, dy - 38, dx + 38, dy + 38], fill=TEAK, outline=WALNUT, width=2)
    for ang_off in [(-50, 0), (50, 0), (0, -50), (0, 50)]:
        cx, cy = dx + ang_off[0], dy + ang_off[1]
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=CREAM, outline=WALNUT, width=1)
    draw.text((dx - 28, dy - 8), "餐桌", fill=CREAM, font=font(11))

    # --- Kitchen: L-counter + island hint ---
    draw.rectangle(mr(0.35, 2.2, 2.9, 0.6), fill=WALNUT, outline=INK, width=1)  # north counter
    draw.rectangle(mr(0.35, 2.2, 0.6, 2.6), fill=WALNUT, outline=INK, width=1)  # west counter
    # sink
    sk = mr(1.4, 2.3, 0.55, 0.4)
    draw.rounded_rectangle(sk, radius=3, fill=(180, 195, 200), outline=INK)
    # stove
    st = mr(0.45, 3.5, 0.4, 0.55)
    draw.rectangle(st, fill=INK)
    draw.text(m(1.2, 4.2), "中古厨柜", fill=WALNUT, font=font(11))
    # fridge
    draw.rectangle(mr(2.7, 4.2, 0.55, 0.65), fill=(90, 90, 95), outline=INK)

    # --- Master bed + nightstands ---
    bed = mr(0.5, 5.5, 2.0, 1.8)
    draw.rounded_rectangle(bed, radius=4, fill=CREAM, outline=WALNUT, width=2)
    draw.rectangle(mr(0.5, 5.5, 2.0, 0.35), fill=WALNUT)  # headboard
    draw.rectangle(mr(0.35, 5.7, 0.15, 0.4), fill=TEAK)
    draw.rectangle(mr(2.5, 5.7, 0.15, 0.4), fill=TEAK)
    draw.text(m(1.0, 6.2), "双人床 1.8m", fill=INK, font=font(11))
    # wardrobe
    draw.rectangle(mr(0.35, 7.8, 2.8, 0.55), fill=WALNUT, outline=INK)
    draw.text(m(1.1, 7.9), "衣柜", fill=CREAM, font=font(11))

    # --- Second bedroom ---
    bed2 = mr(8.3, 2.4, 2.2, 1.6)
    draw.rounded_rectangle(bed2, radius=4, fill=CREAM, outline=WALNUT, width=2)
    draw.rectangle(mr(8.3, 2.4, 2.2, 0.3), fill=WALNUT)
    draw.text(m(8.8, 3.0), "床 1.5m", fill=INK, font=font(11))
    draw.rectangle(mr(8.0, 5.0, 2.8, 0.45), fill=WALNUT, outline=INK)
    draw.text(m(8.8, 5.05), "衣柜", fill=CREAM, font=font(11))

    # --- Study: desk + bookshelf + daybed ---
    draw.rectangle(mr(8.1, 6.0, 2.6, 0.55), fill=TEAK, outline=WALNUT, width=2)
    draw.text(m(8.8, 6.1), "书桌 Desk", fill=CREAM, font=font(11))
    draw.rectangle(mr(10.5, 6.7, 0.4, 1.8), fill=WALNUT, outline=INK)
    draw.rounded_rectangle(mr(8.1, 7.6, 2.0, 0.9), radius=4, fill=SAGE, outline=WALNUT, width=2)
    draw.text(m(8.5, 7.85), "躺椅", fill=CREAM, font=font(11))

    # --- Bathroom fixtures ---
    draw.rectangle(mr(6.0, 2.2, 0.7, 0.45), fill=(200, 210, 215), outline=INK)  # vanity
    draw.ellipse(mr(7.0, 2.3, 0.5, 0.5), fill=(200, 210, 215), outline=INK)  # toilet
    draw.rectangle(mr(5.95, 3.6, 1.1, 1.0), fill=(170, 190, 195), outline=INK)  # shower
    draw.text(m(6.1, 3.9), "淋浴", fill=INK, font=font(10))

    # --- Entry console ---
    draw.rectangle(mr(3.55, 2.2, 0.45, 1.4), fill=WALNUT, outline=INK)
    draw.text(m(3.55, 3.0), "鞋柜", fill=CREAM, font=font(10))

    # --- Rug in living ---
    draw.ellipse(mr(4.2, 6.5, 2.0, 1.4), outline=MUSTARD, width=2)


def draw_dimensions(draw):
    # Overall width
    y = OY + int(9.8 * SCALE) + 40
    x0 = OX
    x1 = OX + int(11.2 * SCALE)
    draw.line([x0, y, x1, y], fill=INK, width=1)
    draw.line([x0, y - 6, x0, y + 6], fill=INK, width=1)
    draw.line([x1, y - 6, x1, y + 6], fill=INK, width=1)
    draw.text(((x0 + x1) // 2 - 40, y + 8), "11.20 m", fill=INK, font=font(13))

    # Overall depth
    x = OX - 50
    y0 = OY
    y1 = OY + int(9.8 * SCALE)
    draw.line([x, y0, x, y1], fill=INK, width=1)
    draw.line([x - 6, y0, x + 6, y0], fill=INK, width=1)
    draw.line([x - 6, y1, x + 6, y1], fill=INK, width=1)
    # rotated-ish label
    draw.text((x - 55, (y0 + y1) // 2), "9.80 m", fill=INK, font=font(13))


def sheet_a01_partition():
    W, H = 1400, 1100
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-01  平面分隔图  PARTITION PLAN", "05套 · 建筑面积 90.23㎡ · 中古风 Mid-Century · 比例 1:50")
    draw_unit_shell(draw)
    draw_room_rects(draw)
    draw_doors_windows(draw)
    draw_adjacency_notes(draw)
    draw_dimensions(draw)
    draw_north(draw, W - 100, 140)

    # Area schedule
    ax, ay = 40, H - 220
    draw.rectangle([ax, ay, ax + 520, ay + 180], fill=CREAM, outline=WALNUT, width=2)
    draw.text((ax + 14, ay + 10), "面积表 AREA SCHEDULE", fill=WALNUT, font=font(15, True))
    schedule = [
        "主卧 12.2  ·  次卧 11.5  ·  书房 10.2  ·  客厅 11.4",
        "餐厅 8.6  ·  厨房 9.6  ·  卫生间 5.6  ·  衣帽 2.8",
        "玄关 4.3  ·  半阳1+2 ≈ 7.2  ·  走道/墙体余量",
        "套内合计约 90.23㎡（含阳台折算，按原建筑图）",
        "格局：两室一厅一卫 + 书房（可改第三卧）",
    ]
    for i, line in enumerate(schedule):
        draw.text((ax + 14, ay + 40 + i * 24), line, fill=INK, font=font(13))

    draw_legend_box(draw, W - 320, H - 250, [
        (CREAM, "公区 Living / Dining"),
        ((235, 225, 210), "卧室 Bedrooms"),
        ((230, 210, 185), "厨房 Kitchen"),
        ((210, 218, 215), "卫浴 Bath"),
        (BALCONY, "阳台 Balcony"),
    ])

    # Design notes
    draw.text((40, 120), "设计说明：北侧入户 · 南向双半阳台采光 · 客餐厅贯通南向 · 主卧西侧安静 · 书房可改儿童房", fill=INK, font=font(14))
    return save(img, "A01_平面分隔图.png")


def sheet_a02_furniture():
    W, H = 1400, 1100
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-02  家具布置图  FURNITURE LAYOUT", "05套 · 中古风家具配置 · 柚木 / 胡桃木 · 比例 1:50")
    draw_unit_shell(draw, fill=(248, 244, 236))
    # lighter room fills
    for name, (x, y, w, h, label, fill) in ROOMS.items():
        r = mr(x, y, w, h)
        draw.rectangle(r, fill=fill, outline=WALL, width=2)
        # small corner label
        draw.text((r[0] + 6, r[1] + 4), name, fill=FIXTURE, font=font(11))
    draw_doors_windows(draw)
    draw_furniture(draw)
    draw_dimensions(draw)
    draw_north(draw, W - 100, 140)

    # Furniture list
    ax, ay = 40, H - 240
    draw.rectangle([ax, ay, ax + 680, ay + 200], fill=CREAM, outline=WALNUT, width=2)
    draw.text((ax + 14, ay + 10), "中古风家具清单 KEY PIECES", fill=WALNUT, font=font(15, True))
    items = [
        "客厅：三人布艺沙发（鼠尾草绿）· 柚木椭圆茶几 · 胡桃木电视柜 · 芥末黄休闲椅 · 圆形地毯",
        "餐厅：柚木圆桌 Ø900 · 弯木餐椅 ×4 · 黄铜吊灯",
        "厨房：胡桃木柜门 + 奶油台面 · 复古把手 · 独立冰箱位",
        "主卧：1.8m 实木床 · 一体化床头板 · 通长衣柜 · 壁灯",
        "次卧：1.5m 床 · 衣柜 · 书桌可选",
        "书房：通长书桌 · 落地书架 · 躺椅阅读角（可改为儿童房）",
        "玄关：竖向鞋柜 + 穿衣镜 · 黄铜挂钩",
    ]
    for i, line in enumerate(items):
        draw.text((ax + 14, ay + 40 + i * 22), line, fill=INK, font=font(12))
    return save(img, "A02_家具布置图.png")


def sheet_a03_materials():
    W, H = 1400, 1000
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-03  材质与色彩  MATERIALS & PALETTE", "中古风 · 暖木 × 奶油 × 鼠尾草 × 黄铜")

    swatches = [
        (WALNUT, "胡桃木 Walnut", "地板 / 柜体 / 门"),
        (TEAK, "柚木 Teak", "家具 / 餐桌 / 细节"),
        (CREAM, "奶油白 Cream", "墙面主色"),
        (SOFT, "暖米色 Warm Beige", "天花 / 踢脚"),
        (SAGE, "鼠尾草绿 Sage", "沙发 / 软装"),
        (OLIVE, "橄榄灰 Olive", "局部墙面"),
        (MUSTARD, "芥末黄 Mustard", "单椅 / 抱枕"),
        ((180, 150, 90), "黄铜 Brass", "灯具 / 把手"),
        ((90, 90, 95), "炭黑 Charcoal", "五金点缀"),
        (TILE, "复古花砖 Tile", "卫生间 / 厨房腰线"),
    ]
    for i, (color, name, use) in enumerate(swatches):
        col = i % 5
        row = i // 5
        x = 60 + col * 260
        y = 160 + row * 220
        draw.rounded_rectangle([x, y, x + 230, y + 180], radius=12, fill=CREAM, outline=WALNUT, width=2)
        draw.rounded_rectangle([x + 20, y + 20, x + 210, y + 100], radius=8, fill=color, outline=INK, width=1)
        draw.text((x + 20, y + 115), name, fill=INK, font=font(16, True))
        draw.text((x + 20, y + 142), use, fill=FIXTURE, font=font(13))

    # Material notes
    draw.rectangle([60, 620, W - 60, 920], fill=CREAM, outline=WALNUT, width=2)
    draw.text((80, 640), "选材与工艺说明", fill=WALNUT, font=font(20, True))
    notes = [
        "1. 地面：客厅/卧室铺设人字拼或直铺橡木/胡桃木地板，保留木纹；厨卫用复古花砖或哑光水泥砖。",
        "2. 墙面：乳胶漆奶油白为主；餐厅局部可做橄榄灰或木饰面背景墙；不做大面积石膏线。",
        "3. 吊顶：简洁平顶 + 局部木格栅/木梁装饰，避免复杂欧式造型；灯具选用飞碟灯、黄铜枝形吊灯。",
        "4. 柜体：全屋定制胡桃木色柜门，圆角或斜边收口，黄铜圆形把手；开放格可放置黑胶/陶瓷。",
        "5. 软装：亚麻窗帘、羊毛地毯、皮革与布艺混搭；绿植（龟背竹、琴叶榕）增加呼吸感。",
        "6. 灯光：分层照明 — 主灯暖白 2700K + 落地灯 + 壁灯；避免冷白光。",
        "7. 阳台：木地板或仿木砖 + 休闲椅；半阳可做生活阳台（洗衣）与观景阳台分区。",
    ]
    for i, n in enumerate(notes):
        draw.text((80, 680 + i * 30), n, fill=INK, font=font(14))
    return save(img, "A03_材质色彩.png")


def sheet_a04_elevations():
    W, H = 1400, 1100
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-04  立面示意  ELEVATIONS", "客餐厅南立面 · 厨房立面 · 主卧床头立面")

    def elev_frame(x, y, w, h, title):
        draw.rectangle([x, y, x + w, y + h], fill=CREAM, outline=WALL, width=3)
        draw.text((x, y - 28), title, fill=WALNUT, font=font(16, True))
        # floor line
        draw.line([x, y + h - 40, x + w, y + h - 40], fill=WALL, width=2)
        # ceiling
        draw.line([x, y + 20, x + w, y + 20], fill=GRID, width=1)
        return y + h - 40  # floor y

    # --- Living south elevation ---
    x, y, w, h = 60, 170, 620, 380
    fl = elev_frame(x, y, w, h, "① 客餐厅南立面（面向阳台）")
    # window
    draw.rectangle([x + 40, y + 60, x + 280, fl], fill=(200, 220, 230), outline=WALNUT, width=2)
    draw.line([x + 160, y + 60, x + 160, fl], fill=WALNUT, width=2)
    draw.line([x + 40, y + 160, x + 280, y + 160], fill=WALNUT, width=1)
    draw.text((x + 100, y + 100), "落地窗", fill=INK, font=font(12))
    # TV wall wood panel
    draw.rectangle([x + 320, y + 50, x + 580, fl], fill=WALNUT, outline=INK, width=2)
    draw.rectangle([x + 360, y + 100, x + 540, y + 220], fill=INK)  # TV
    draw.text((x + 400, y + 140), "TV", fill=CREAM, font=font(14))
    draw.rectangle([x + 340, fl - 50, x + 560, fl], fill=TEAK)  # console
    draw.text((x + 390, fl - 38), "胡桃木电视柜", fill=CREAM, font=font(11))
    # sofa hint
    draw.ellipse([x + 80, fl - 55, x + 240, fl - 5], fill=SAGE, outline=WALNUT)

    # --- Kitchen elevation ---
    x, y, w, h = 740, 170, 580, 380
    fl = elev_frame(x, y, w, h, "② 厨房A立面（北柜）")
    # upper cabinets
    for i in range(4):
        cx = x + 30 + i * 130
        draw.rectangle([cx, y + 40, cx + 120, y + 140], fill=WALNUT, outline=INK, width=2)
        draw.ellipse([cx + 50, y + 85, cx + 70, y + 105], outline=MUSTARD, width=2)  # brass knob
    # backsplash
    draw.rectangle([x + 30, y + 150, x + 540, y + 220], fill=TILE, outline=INK)
    for i in range(8):
        for j in range(2):
            draw.rectangle([x + 40 + i * 60, y + 160 + j * 30, x + 90 + i * 60, y + 185 + j * 30], outline=FIXTURE)
    # counter
    draw.rectangle([x + 30, y + 220, x + 540, y + 250], fill=CREAM, outline=INK, width=2)
    # lower cabinets
    for i in range(4):
        cx = x + 30 + i * 130
        draw.rectangle([cx, y + 250, cx + 120, fl], fill=WALNUT, outline=INK, width=2)
        draw.ellipse([cx + 50, (y + 250 + fl) // 2 - 8, cx + 70, (y + 250 + fl) // 2 + 12], outline=MUSTARD, width=2)
    draw.text((x + 180, y + 175), "复古花砖腰线", fill=INK, font=font(12))

    # --- Master headboard elevation ---
    x, y, w, h = 60, 620, 620, 380
    fl = elev_frame(x, y, w, h, "③ 主卧床头立面")
    # wood headboard wall
    draw.rectangle([x + 80, y + 40, x + 540, fl], fill=(160, 120, 80), outline=WALNUT, width=2)
    # soft panel
    draw.rectangle([x + 160, y + 80, x + 460, y + 200], fill=SAGE, outline=WALNUT, width=2)
    draw.text((x + 260, y + 130), "软包床头", fill=CREAM, font=font(14))
    # sconces
    for sx in [x + 130, x + 480]:
        draw.ellipse([sx, y + 100, sx + 30, y + 130], fill=MUSTARD, outline=WALNUT, width=2)
        draw.line([sx + 15, y + 130, sx + 15, y + 160], fill=WALNUT, width=2)
    draw.text((x + 100, y + 170), "壁灯", fill=CREAM, font=font(11))
    draw.text((x + 470, y + 170), "壁灯", fill=CREAM, font=font(11))
    # bed
    draw.rectangle([x + 140, fl - 70, x + 480, fl], fill=CREAM, outline=WALNUT, width=2)
    draw.text((x + 270, fl - 50), "床", fill=INK, font=font(13))

    # --- Entry elevation ---
    x, y, w, h = 740, 620, 580, 380
    fl = elev_frame(x, y, w, h, "④ 玄关立面")
    # shoe cabinet
    draw.rectangle([x + 40, y + 60, x + 200, fl], fill=WALNUT, outline=INK, width=2)
    for i in range(5):
        yy = y + 80 + i * 45
        draw.line([x + 50, yy, x + 190, yy], fill=TEAK, width=1)
    draw.text((x + 70, y + 200), "鞋柜", fill=CREAM, font=font(13))
    # mirror
    draw.rectangle([x + 240, y + 50, x + 400, y + 280], fill=(210, 220, 225), outline=MUSTARD, width=3)
    draw.text((x + 290, y + 150), "穿衣镜", fill=INK, font=font(13))
    # bench
    draw.rectangle([x + 240, fl - 50, x + 420, fl], fill=TEAK, outline=WALNUT, width=2)
    draw.text((x + 300, fl - 38), "换鞋凳", fill=CREAM, font=font(12))
    # hooks
    for i in range(3):
        hx = x + 450 + i * 35
        draw.ellipse([hx, y + 100, hx + 16, y + 116], outline=MUSTARD, width=2)

    return save(img, "A04_立面示意.png")


def sheet_a05_ceiling_lighting():
    W, H = 1400, 1000
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-05  天花照明图  CEILING & LIGHTING", "暖光 2700K · 主灯 + 灯带 + 壁灯分层")

    draw_unit_shell(draw, fill=(250, 246, 238))
    for name, (x, y, w, h, label, fill) in ROOMS.items():
        r = mr(x, y, w, h)
        draw.rectangle(r, fill=(248, 244, 236), outline=WALL, width=2)
        draw.text((r[0] + 8, r[1] + 6), name, fill=FIXTURE, font=font(12))

    def pendant(mx, my, label="吊灯"):
        px, py = m(mx, my)
        draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=MUSTARD, outline=WALNUT, width=2)
        draw.text((px - 16, py + 16), label, fill=INK, font=font(10))

    def downlight(mx, my):
        px, py = m(mx, my)
        draw.ellipse([px - 5, py - 5, px + 5, py + 5], outline=INK, width=1)

    def sconce(mx, my):
        px, py = m(mx, my)
        draw.rectangle([px - 6, py - 4, px + 6, py + 4], fill=MUSTARD, outline=WALNUT)

    # Living pendant (flying saucer)
    pendant(5.2, 7.2, "飞碟灯")
    # Dining pendant
    pendant(5.0, 4.9, "黄铜吊灯")
    # Bedroom pendants / flush
    pendant(1.5, 6.5, "吸顶")
    pendant(9.4, 3.5, "吸顶")
    pendant(9.4, 7.0, "落地灯位")
    # Kitchen downlights
    for xx in [0.8, 1.6, 2.4]:
        downlight(xx, 2.6)
        downlight(xx, 4.0)
    # Bath
    downlight(6.5, 2.5)
    downlight(6.5, 4.0)
    # Hall / entry
    downlight(4.4, 2.6)
    downlight(4.4, 3.4)
    # Cove light indication in living
    r = mr(3.6, 6.4, 4.0, 2.2)
    draw.rectangle(r, outline=MUSTARD, width=1)
    draw.text(m(4.5, 6.45), "灯带 cove", fill=MUSTARD, font=font(11))
    # Sconces master
    sconce(0.6, 5.8)
    sconce(2.6, 5.8)

    # Legend
    draw_legend_box(draw, 40, H - 200, [
        (MUSTARD, "吊灯 / 主灯 Pendant"),
        (INK, "筒灯 Downlight（空心圆）"),
        (MUSTARD, "壁灯 Wall sconce"),
        (MUSTARD, "灯带 Cove（虚线框）"),
    ])

    draw.rectangle([400, H - 200, W - 40, H - 40], fill=CREAM, outline=WALNUT, width=2)
    draw.text((420, H - 185), "照明设计要点", fill=WALNUT, font=font(15, True))
    tips = [
        "色温统一 2700–3000K，营造中古暖调；客厅飞碟灯为视觉焦点。",
        "餐厅黄铜吊灯降至桌面上方约 750mm；厨房操作台面增加灯带。",
        "卧室以吸顶灯 + 床头壁灯为主，避免强光直射；书房设落地灯阅读角。",
        "玄关感应灯带；卫生间防雾吸顶 + 镜前灯。",
    ]
    for i, t in enumerate(tips):
        draw.text((420, H - 155 + i * 28), t, fill=INK, font=font(13))

    draw_north(draw, W - 100, 140)
    return save(img, "A05_天花照明图.png")


def sheet_cover():
    W, H = 1400, 900
    img = Image.new("RGB", (W, H), WALNUT)
    draw = ImageDraw.Draw(img)
    # cream panel
    draw.rounded_rectangle([80, 80, W - 80, H - 80], radius=8, fill=CREAM)
    # accent bar
    draw.rectangle([80, 80, 120, H - 80], fill=TEAK)
    draw.text((180, 160), "05 套", fill=WALNUT, font=font(28))
    draw.text((180, 210), "中古风装修设计图纸", fill=INK, font=font(48, True))
    draw.text((180, 280), "MID-CENTURY MODERN RENOVATION SET", fill=FIXTURE, font=font(20))
    draw.line([180, 330, 700, 330], fill=TEAK, width=3)

    info = [
        "建筑面积｜90.23 ㎡",
        "格局方案｜两室一厅一卫 + 书房（可改三房）",
        "风格定位｜中古风 · 暖木 · 奶油 · 鼠尾草 · 黄铜",
        "图纸目录｜A-01 分隔  A-02 家具  A-03 材质  A-04 立面  A-05 照明",
        "采光策略｜南向双半阳台贯通客餐厅，北侧入户",
    ]
    for i, line in enumerate(info):
        draw.text((180, 370 + i * 42), line, fill=INK, font=font(18))

    draw.text((180, H - 160), "DESIGN DRAWING SET  ·  FOR REFERENCE", fill=FIXTURE, font=font(14))
    # decorative circles
    draw.ellipse([1000, 200, 1200, 400], outline=TEAK, width=3)
    draw.ellipse([1050, 250, 1150, 350], fill=SAGE)
    draw.ellipse([1080, 450, 1280, 650], outline=MUSTARD, width=2)
    return save(img, "A00_封面.png")


def sheet_concept():
    """Concept diagram with flow."""
    W, H = 1400, 900
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_title(draw, W, "A-00b  设计概念  DESIGN CONCEPT", "动线 · 采光 · 中古氛围")

    # Three columns
    cols = [
        (60, "动线 FLOW", [
            "北侧电梯厅入户 → 玄关收纳",
            "西侧厨房靠近入户，动线短",
            "客餐厅南向开敞，无遮挡",
            "主卧独立西翼，安静私密",
            "东侧次卧+书房，灵活可变",
            "卫生间居中，管线集中",
        ]),
        (480, "采光 LIGHT", [
            "南向双半阳台为主要采光面",
            "客餐厅落地窗最大化日照",
            "主卧、书房均享阳台光线",
            "厨房借北向/门洞间接采光",
            "暖光照明 2700K 统一氛围",
            "木饰面反射柔和光线",
        ]),
        (900, "中古氛围 MOOD", [
            "胡桃/柚木贯穿全屋",
            "奶油墙面 + 鼠尾草绿软装",
            "黄铜五金与飞碟灯",
            "圆角家具、椭圆茶几",
            "复古花砖点缀厨卫",
            "黑胶架/陶瓷/绿植点景",
        ]),
    ]
    for x, title, bullets in cols:
        draw.rounded_rectangle([x, 150, x + 380, 780], radius=10, fill=CREAM, outline=WALNUT, width=2)
        draw.rectangle([x, 150, x + 380, 210], fill=WALNUT)
        draw.text((x + 24, 165), title, fill=CREAM, font=font(20, True))
        for i, b in enumerate(bullets):
            draw.ellipse([x + 28, 240 + i * 80, x + 40, 252 + i * 80], fill=TEAK)
            draw.text((x + 55, 232 + i * 80), b, fill=INK, font=font(15))

    return save(img, "A00b_设计概念.png")


def main():
    sheet_cover()
    sheet_concept()
    sheet_a01_partition()
    sheet_a02_furniture()
    sheet_a03_materials()
    sheet_a04_elevations()
    sheet_a05_ceiling_lighting()
    print("All sheets generated.")


if __name__ == "__main__":
    main()
