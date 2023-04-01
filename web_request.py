"""Testing routine to get data from Auckland Council"""
from bs4 import BeautifulSoup as bs
import requests

LOC = "12342731560"


def main():
    url = f"https://www.aucklandcouncil.govt.nz/rubbish-recycling/rubbish-recycling-collections/Pages/collection-day-detail.aspx?an={LOC}"
    print(url)

    response = requests.get(url)
    html = response.text

    soup = bs(html, "html.parser")
    household = soup.find_all("div", {"id": lambda x: x and "HouseholdBlock" in x})

    result = []
    # We can assume only one Household Block
    for collect_date in household[0].find_all("span", {"class": "m-r-1"}):
        collect_types = []
        for sibling in collect_date.find_next_siblings():
            collect_type = sibling.find("span", {"class": "sr-only"})
            if collect_type:
                collect_types.append(collect_type.text)
        result.append({collect_date.text: collect_types})

    print(result)


if __name__ == "__main__":
    main()
