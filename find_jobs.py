# find_jobs.py – finds new job ads, lets Claude score them, saves a sorted list.
import csv
import html as htmllib
import json
import re
import time
import urllib.parse
import urllib.request
from itertools import zip_longest
from pathlib import Path

from rank_job import rank_job  # the scoring function built earlier

JOBINDEX_SEARCHES = ["projektleder", "it-projektleder", "digitaliseringskonsulent",
                     "dataanalytiker", "forretningsanalytiker", "systemejer",
                     "product owner", "projektkoordinator"]
KK_PAGES = 18   # kk.dk has about 18 list pages
MAX_ADS = 25    # max ads scored per run, to spare the Pro allowance

WANTED = ["projekt", "digital", "data", "analy", "it-", "konsulent", "forretning",
          "systemejer", "product owner", "business", " ai ", "ai-", "klima", "natur",
          "biodivers", "partnerskab"]
UNWANTED = ["praktik", "student", "elev", "lærer", "laerer", "pædagog", "paedagog",
            "sosu", "hjemmepleje", "vikarkorps", "chef", "direktør", "direktoer",
            "rengøring", "rengoering",
            # construction and technical installation – not his field
            "bygge", "anlæg", "anlaeg", "entrepris", "ventilation", "isolering",
            "jernbane", "kystbeskyt", "cts", "bms", "teknisk projektleder", "asfalt",
            "byudvikling", "vedligeholdelse", "sikringsprojekt", "el-"]
# Holger's deal-breaker: employers that extract, refine or sell fossil oil or gas
FOSSIL = ["evida", "totalenergies", "shell", "equinor", " bp ", "ineos", "circle k", "q8 "]
SUSPICIOUS = ["ignore previous", "ignore all", "ignorer", "ignorér", "instruktion",
              "instruction", "system prompt", "giv dette job"]

SEEN_FILE = Path("seen.txt")


def get(url):
    """Download one page, then wait 3 seconds to be polite to the site."""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (personal job search)"})
    page = urllib.request.urlopen(request, timeout=20).read().decode("utf-8", errors="ignore")
    time.sleep(3)
    return page


def relevant(title):
    t = f" {title.lower()} "
    return any(w in t for w in WANTED) and not any(w in t for w in UNWANTED)


def jobindex_ads(query):
    """Title + link for each ad on the first page of a Jobindex search."""
    page = get("https://www.jobindex.dk/jobsoegning?q=" + urllib.parse.quote(query))
    found = re.findall(r'-title=\\"(.*?)\\" data-share-url=\\"https:\\/\\/www\.jobindex\.dk'
                       r'\\/vis-job\\/([a-z0-9]+)', page)
    ads = []
    for raw_title, ad_id in found:
        try:
            title = json.loads('"' + raw_title + '"')  # turns \u00f8 into ø
        except ValueError:
            title = raw_title
        ads.append((htmllib.unescape(title), "https://www.jobindex.dk/vis-job/" + ad_id))
    return ads


def kk_ads():
    """Title (from the link) + link for every ad on kk.dk's list pages."""
    ads = []
    for n in range(KK_PAGES):
        page = get(f"https://www.kk.dk/ledigestillinger?page={n}")
        for slug in sorted(set(re.findall(r'href="/ledigestillinger/([a-z0-9-]+)"', page))):
            ads.append((slug.replace("-", " "), "https://www.kk.dk/ledigestillinger/" + slug))
    return ads


def clean(html):
    """Remove code and tags, keep readable text."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", text).strip()


def ad_text(url):
    """Jobindex's summary of the ad, plus the full ad from the employer's site when possible."""
    page = get(url)
    start = page.find('class="PaidJob-inner"')  # Jobindex puts the ad summary here
    if start < 0:
        return clean(page)[:8000]
    block = page[start:start + 40000]
    text = clean(block)[:1500]  # title, location, short intro
    link = re.search(r'href="(https?://(?!www\.jobindex\.dk)[^"]+)"', block, re.I)
    if link:  # the full ad usually lives on the employer's own site
        try:
            text += " FULDT OPSLAG: " + clean(get(htmllib.unescape(link.group(1))))[:6500]
        except Exception:
            pass  # if the employer's site can't be read, the summary is still used
    return text


if __name__ == "__main__":
    seen = set(SEEN_FILE.read_text(encoding="utf-8").split()) if SEEN_FILE.exists() else set()

    sources = []  # one list of ads per search, plus one for kk.dk
    for query in JOBINDEX_SEARCHES:
        print(f"Searching Jobindex: {query}")
        sources.append(jobindex_ads(query))
    print("Reading kk.dk ...")
    sources.append(kk_ads())

    # Take turns between the sources, so every search gets a share of the places
    new, used = [], set()
    for row in zip_longest(*sources):
        for item in row:
            if item and item[1] not in seen and item[1] not in used and relevant(item[0]):
                new.append(item)
                used.add(item[1])
    total = sum(len(s) for s in sources)
    print(f"{total} ads found, {len(new)} new and relevant. Scoring up to {MAX_ADS}.")

    results = []
    for number, (title, url) in enumerate(new[:MAX_ADS], start=1):
        print(f"Scoring {number}: {title}")
        try:
            text = ad_text(url)
            if any(name in f" {text.lower()} " for name in FOSSIL):
                print("   skipped: fossil oil/gas employer")
                seen.add(url)
                continue
            answer = rank_job(text)
        except Exception as error:  # one bad ad must not stop the whole run
            print(f"   skipped: {error}")
            continue
        flag = "⚠ TJEK SELV: mistænkelig tekst i opslaget. " if any(s in text.lower() for s in SUSPICIOUS) else ""
        results.append((answer["score"], title, url, flag + answer["why"]))
        seen.add(url)

    results.sort(reverse=True)
    with open("jobs_found.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["score", "title", "link", "why"])
        writer.writerows(results)
    SEEN_FILE.write_text("\n".join(sorted(seen)), encoding="utf-8")
    print(f"Done. {len(results)} ads saved to jobs_found.csv, best first.")