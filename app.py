from flask import Flask, render_template, request, send_from_directory
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, parse_qs, unquote
import os

app = Flask(__name__)

# Explicitly set the path to the templates folder
template_dir = os.path.abspath('templates')
app.template_folder = template_dir

def extract_params_from_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    business_name = unquote(query_params.get('search_terms', [''])[0])
    geo_location = unquote(query_params.get('geo_location_terms', [''])[0])
    return business_name, geo_location

def extract(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    return soup.find_all('div', class_='result')

def get_total_pages(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    pagination = soup.find('div', class_='pagination')
    if pagination:
        last_page_elem = pagination.find('a', class_='next')
        if last_page_elem:
            total_pages = int(last_page_elem.find_previous('a').text)
        else:
            total_pages = 1
        return total_pages
    return 1

def transform(articles, business_name, geo_location):
    main_list = []

    for item in articles:
        name_elem = item.find('a', class_='business-name')
        name = name_elem.text.strip() if name_elem else ''

        location_elem = item.find('div', class_='location')
        address = location_elem.text.strip() if location_elem and location_elem.text else ''

        try:
            website_elem = item.find('a', class_='track-visit-website')
            website = website_elem['href'] if website_elem else ''
        except (TypeError, KeyError):
            website = ''

        phones_elem = item.find('div', class_='phones')
        tel = phones_elem.text.strip() if phones_elem and phones_elem.text else ''

        street_address_elem = item.find('div', class_='street-address')
        city_elem = item.find('div', class_='locality')
        state_elem = item.find('div', class_='region')
        zip_code_elem = item.find('div', class_='postal-code')

        street_address = street_address_elem.text.strip() if street_address_elem and street_address_elem.text else ''
        city = city_elem.text.strip() if city_elem and city_elem.text else ''
        state = state_elem.text.strip() if state_elem and state_elem.text else ''
        zip_code = zip_code_elem.text.strip() if zip_code_elem and zip_code_elem.text else ''

        full_address = f"{street_address}, {city}, {state} {zip_code}"

        business_data = {
            'name': name,
            'address': full_address,
            'website': website,
            'tel': tel
        }
        main_list.append(business_data)

    # Save to CSV with the generated filename
    csv_filename = f"{business_name}_{geo_location}.csv"
    df = pd.DataFrame(main_list)
    df.to_csv(csv_filename, index=False)

    return csv_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    business_name, geo_location = extract_params_from_url(url)
    total_pages = get_total_pages(url)

    main_list = []

    for x in range(1, total_pages + 1):
        articles = extract(f'{url}&page={x}')
        csv_filename = transform(articles, business_name, geo_location)

    print(f'CSV Filename: {csv_filename}')  # Add this line for debugging

    return render_template('result.html', filename=csv_filename)

@app.route('/static/<filename>')
def download_csv(filename):
    return send_from_directory(os.getcwd(), filename)

if __name__ == '__main__':
    app.run(debug=True)
