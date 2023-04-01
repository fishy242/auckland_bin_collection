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
    # We can assume only one Household Block
    for date in household[0].find_all("span", {"class": "m-r-1"}):
        print(date.text)


if __name__ == "__main__":
    main()
