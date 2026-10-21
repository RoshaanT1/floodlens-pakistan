"""Write team answers into the blue boxes of the HackInsight guide PDF and tick checkboxes."""
import io
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

SRC, OUT = sys.argv[1], sys.argv[2]
H = 792.0
INK = (0.05, 0.15, 0.45)

# (page, x0, top, x1, bottom, text)  coordinates from pdfplumber (top-left origin)
W = (55.1, 556.1)
BOXES = [
    (2, 55.1, 472.9, 556.1, 481.9, "Spark H"),
    (2, 55.8, 491.0, 556.8, 499.9, "Climate and heat-health (disaster risk), with a secondary food-security model"),
    (2, 55.1, 509.8, 556.1, 528.7, "District planners in Pakistan get provincial rain alerts but no district-specific, calibrated probability of unusually heavy rain 1-3 days ahead. FloodLens gives one for all 160 districts, refreshed every hour."),
    (2, 55.1, 537.7, 556.1, 554.4, "A district / PDMA disaster-management planner deciding, 24-72 h ahead, where to pre-position rescue teams, pumps and relief stock and where to issue local warnings."),
    (2, 55.1, 562.7, 556.1, 581.6, "The 2025 monsoon killed 1,037 people and injured 1,067 between 26 Jun and 1 Oct 2025, 509 of them in KP (NDMA, Monsoon 2025 Final Consolidated Situation Report No. 87, 2 Oct 2025)."),
    (2, 55.1, 589.9, 556.1, 606.6, "All 160 districts (OCHA admin-2); errors reported by province, mountain vs plain, coastal vs inland, 2022 flood-prone vs not, and monsoon vs dry months."),
    (2, 55.8, 614.9, 556.8, 631.6, "Probability that a district's daily wettest-pixel rain (NASA IMERG Late, UTC day) exceeds its own 95th percentile of wet-day rain (2015-2023), for +1, +2 and +3 days; binary, daily, per district."),
    (3, 55.8, 37.2, 556.8, 54.0, "District-by-month climatology (share of 2015-2023 days over the threshold). Better = lower Brier score at 24 h on the test set, and the gain must also hold in monsoon months."),
    (3, 55.8, 62.2, 556.8, 81.2, "Daily 0.1 deg satellite rain smooths out local cloudbursts (Buner, 15 Aug 2025); forecasts are taken at district centroids; forecast archive starts Feb 2024 (17 months to train); heavy rain is not a flood."),
    (3, 55.1, 564.4, 556.1, 580.1, "Open-Meteo Previous Runs API (forecasts issued 1-3 days ahead from ECMWF/NOAA/DWD models), Open-Meteo, open-meteo.com/en/docs/previous-runs-api, CC BY 4.0, model runs every 6 h."),
    (3, 55.1, 588.2, 556.1, 604.0, "NASA GPM IMERG V07 Late Run daily (GPM_3IMERGDL), NASA GES DISC, disc.gsfc.nasa.gov, NASA EOSDIS open data policy, daily (~14 h latency)."),
    (3, 55.1, 612.1, 556.1, 627.8, "NASA IMERG: NASA's standard multi-satellite rainfall product, independent of the weather models used as inputs. Also PBS weekly SPI, Pakistan's official weekly consumer prices."),
    (3, 55.1, 636.0, 556.1, 646.1, "Forecasts 476,640 district-day-lead rows; IMERG 689,120 district-days (2015 to Oct 2026); PBS prices 146,523 rows (169 weeks)."),
    (3, 55.1, 655.2, 556.1, 672.0, "Archived forecasts give real 1-3 day lead time without leaking the future; satellite rain shows what fell even where there is no rain gauge; both cover every district the planner is responsible for."),
    (3, 55.1, 681.1, 556.1, 694.6, "Model A: district-by-month climatology. Model B: no change (next week's price = this week's)."),
    (4, 55.8, 418.3, 556.8, 445.2, "spi_price | rule spi_price_collected | action FLAG | 1,279 rows | reason: PBS published 0 or nothing for this city and item (not collected); kept NULL, never filled | decided 2026-10-21, replayed on every rebuild. Others: spi_min_le_avg_le_max FLAG 822 rows; spi_weekly_jump FLAG 399 rows; rain_district_day_timely FLAG (stale since 16 Oct)."),
    (4, 55.1, 686.9, 556.1, 700.3, "TEST (Jan-Sep 2026, run once): climatology 0.0192 [0.0156, 0.0231] vs model 0.0177 [0.0146, 0.0213] Brier at 24 h; paired diff -0.0014 [-0.0022, -0.0008]; monsoon 0.0251 vs 0.0237. Validation 0.0249 vs 0.0233. Weakest group: Azad Kashmir."),
    (5, 55.1, 281.9, 556.1, 302.0, "Logistic regression -> gradient boosting (both calibrated on validation): val Brier 24 h 0.0238 -> 0.0233; training 2.9 s -> 3.4 s; ~600 MB peak both. Kept."),
    (5, 55.1, 310.3, 556.1, 330.5, "IMERG cropped server-side (OPeNDAP) instead of global daily files: 33.3 MB -> ~74 KB per day; 4,307 days = 182 MB instead of ~143 GB; same values checked. Kept."),
    (5, 55.1, 338.8, 556.1, 358.8, "PBS PDF tables parsed once and cached by SHA-256: price build 286 s (380 MB) -> 3.6 s on rebuild, identical tables. Kept. (Model B quantile GBM: MAE 1.667 vs 1.665 no change: rejected.)"),
    (5, 55.1, 380.3, 556.1, 400.3, "Gradient boosting gained 0.0005 Brier over logistic regression for 0.5 s more training and a less transparent model; kept because it also gained in monsoon months and in every group."),
    (5, 55.1, 565.7, 556.1, 583.6, "The quoted sentence with document title, page and section id; every number with its gold-table row id; \"I don't know\" below the retrieval threshold; \"not an official warning\"; Rescue 1122 / NDMA first in emergencies."),
    (6, 55.1, 462.1, 556.1, 475.6, "District / PDMA planner: where to pre-position teams and relief stock 1-3 days before heavy rain."),
    (6, 55.1, 483.8, 556.1, 495.0, "PDMAs / NDMA (provincial preparedness budgets) or humanitarian donors funding anticipatory action."),
    (6, 55.1, 504.1, 556.1, 517.6, "For district disaster planners, who must decide where to pre-position teams before heavy rain, FloodLens gives an hourly, calibrated district rain-risk 1-3 days ahead with its evidence, unlike provincial alerts."),
    (6, 55.1, 526.7, 556.1, 542.4, "Free public dashboard; contract or grant for PDMAs (alerts, support); triggers for donors' anticipatory action. Fits because the benefit is public safety and the cost is tiny."),
    (6, 55.1, 550.6, 556.1, 566.3, "Measured: 1 CPU; ~28 min rate-limited download + ~5 min rebuild per hour; 1.3 GB storage (+10 MB/day); NASA/OCHA/PBS data free; Open-Meteo free non-commercial (paid if commercial); host free or ~EUR 4/month."),
    (6, 55.1, 574.4, 556.1, 590.2, "Free-tier terms of Open-Meteo and NASA stay as they are (their published terms); PDMA staff check a dashboard daily in monsoon; costs measured on our own runs during the event."),
    (6, 55.1, 598.3, 556.1, 616.2, "Trust (citations, row ids, stated limits); a source blocking access (gpm1 blocked us on Wed; logged, switched to NASA cloud); drift (hourly quality checks); rain risk mistaken for a flood warning (labelled)."),
    (7, 52.4, 119.0, 298.1, 135.0, "The 2025 monsoon killed 1,037 people (NDMA); our user is the district / PDMA planner who must pre-position teams."),
    (7, 305.6, 119.0, 551.3, 135.0, "NDMA's own 87 monsoon 2025 sitreps: 125 districts named, 1,037 deaths in the final report (No. 87)."),
    (7, 52.4, 147.0, 298.1, 163.0, "Archived forecasts (Open-Meteo, CC BY 4.0, ECMWF/NOAA/DWD) for honest lead time; NASA IMERG (open data) as independent truth."),
    (7, 304.9, 147.0, 550.6, 163.0, "NASA's gpm1 server blocked our IP and daily files are 33 MB; we switched to NASA's cloud OPeNDAP, cropped to ~74 KB/day."),
    (7, 52.4, 174.0, 298.1, 190.0, "A price PBS did not collect is unknown; filling it invents data, so 1,279 prices stay NULL and flagged."),
    (7, 305.6, 174.0, 551.3, 190.0, "Test set: climatology 0.0192 vs model 0.0177 Brier at 24 h (~8% better, paired interval excludes zero; holds in monsoon)."),
    (7, 52.4, 202.0, 298.1, 217.9, "Azad Kashmir (smallest gain); single-valley cloudbursts like Buner 15 Aug 2025 are missed by the satellite labels."),
    (7, 304.9, 202.0, 550.6, 217.9, "No model writes numbers: code inserts them from gold tables with row ids; text is quoted with section ids."),
    (7, 52.4, 235.6, 298.1, 251.6, "PDMA planners use it; PDMAs or donors pay from preparedness / anticipatory-action budgets; it runs on one small server."),
    (7, 305.6, 235.6, 551.3, 251.6, "Server-side cropping (143 GB -> 182 MB), a parse cache (286 s -> 3.6 s), gradient boosting (+0.0005 Brier) at some explainability."),
]

# checkboxes to tick: (page, x0, top); only items that are true now
TICKS = [
    (3, 63.1, 461.9), (3, 63.1, 471.7), (3, 63.1, 481.6), (3, 63.1, 491.4), (3, 63.1, 501.4), (3, 63.1, 511.2),
    (5, 63.1, 193.0), (5, 63.1, 202.9), (5, 63.1, 222.6), (5, 63.1, 232.4),
    (5, 63.1, 597.2), (5, 63.1, 607.1), (5, 63.1, 616.9), (5, 63.1, 626.8),
    (6, 63.1, 64.8), (6, 63.1, 74.6), (6, 63.1, 84.5),
    (7, 63.1, 436.7), (7, 63.1, 446.5), (7, 63.1, 456.5),
    (7, 63.1, 521.2), (7, 63.1, 540.8), (7, 63.1, 550.8), (7, 63.1, 560.6), (7, 63.1, 570.5),
    (7, 63.1, 580.4), (7, 63.1, 590.3), (7, 63.1, 600.1),
]


def fit(c, text, x0, top, x1, bottom):
    w, h = x1 - x0 - 4, bottom - top - 1.5
    for size in (7, 6.5, 6, 5.5, 5.2, 5, 4.7, 4.4, 4.2):
        lead = size * 1.12
        lines = simpleSplit(text, "Helvetica", size, w)
        if len(lines) * lead <= h:
            break
    c.setFont("Helvetica", size)
    c.setFillColorRGB(*INK)
    total = len(lines) * lead
    y = H - top - (h - total) / 2 - size * 0.95
    for line in lines:
        c.drawString(x0 + 2, y, line)
        y -= lead
    return size, len(lines)


reader = PdfReader(SRC)
writer = PdfWriter()
for i, page in enumerate(reader.pages, 1):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, H))
    for p, *coords, text in BOXES:
        if p == i:
            size, n = fit(c, text, *coords)
            if size < 5:
                print(f"p{p} top={coords[1]}: small font {size} ({n} lines)")
    c.setFont("ZapfDingbats", 8)
    c.setFillColorRGB(0.05, 0.45, 0.2)
    for p, x0, top in TICKS:
        if p == i:
            c.drawString(x0 + 0.8, H - top - 7.8, "4")  # check mark
    c.save()
    buf.seek(0)
    page.merge_page(PdfReader(buf).pages[0])
    writer.add_page(page)
with open(OUT, "wb") as fh:
    writer.write(fh)
print("written", OUT)
