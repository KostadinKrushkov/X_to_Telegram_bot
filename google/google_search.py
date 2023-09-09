import os
from random import randrange

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin


def get_img_from_element(image_element):
    if image_element and 'src' in image_element.attrs:
        image_url = image_element['src']

        base_url = 'https://www.google.com'
        if image_url:
            complete_image_url = urljoin(base_url, image_url)
            return complete_image_url


def get_random_google_image(keyword):
    search_url = f"https://www.google.com/search?q={quote_plus(keyword)}&tbm=isch"

    response = requests.get(search_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    image_elements = soup.find_all('img')

    try:
        random_index = randrange(3, len(image_elements)-3)
        random_url = get_img_from_element(image_elements[random_index])
        if random_url:
            return random_url
    except:
        pass

    for image_element in image_elements[3:]:
        if image_element and 'src' in image_element.attrs:
            image_url = image_element['src']

            base_url = 'https://www.google.com'
            if image_url:
                complete_image_url = urljoin(base_url, image_url)
                return complete_image_url


def save_first_image(keyword, save_path):
    search_url = f"https://www.google.com/search?q={quote_plus(keyword)}&tbm=isch"

    response = requests.get(search_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    image_element = soup.find_all('img')[5]

    if image_element and 'src' in image_element.attrs:
        image_url = image_element['src']
        base_url = 'https://www.google.com'
        complete_image_url = urljoin(base_url, image_url)

        image_response = requests.get(complete_image_url)
        image_response.raise_for_status()

        image_path = f'{save_path}\\{keyword}_pic_latest_search.jpg'
        with open(image_path, 'wb') as image_file:
            image_file.write(image_response.content)

        print(f"Image saved as {image_path}")

        import webbrowser
        webbrowser.open(image_path)
    else:
        print("No image found.")


if __name__ == '__main__':
    keyword = '$TSLA'
    # save_path = 'images'
    #
    # if not os.path.exists(save_path):
    #     os.makedirs(save_path)
    #
    # save_first_image(keyword, save_path)
    print(get_random_google_image(keyword))
