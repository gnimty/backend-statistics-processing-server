import log
from config.mongo import Mongo
from config.config import current_config as config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

logger = log.get_logger()
db = Mongo.get_client("riot")

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--single-process')
chrome_options.add_argument('--disable-dev-shm-usage')

capabilities = DesiredCapabilities.CHROME
capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}


def update_sale_info():
    with webdriver.Remote(
        command_executor=config.SELENIUM_EXECUTER,  # Selenium 호스트 및 포트 설정
        options=chrome_options
    ) as driver:
        driver.get(
            "https://store.leagueoflegends.co.kr/champions?sort=ReleaseDate&order=DESC")

        driver.implicitly_wait(5)

        driver.find_element(
            By.XPATH, '//*[@id="app"]/div[5]/div/div/div[1]/div[2]/div[1]/div[2]/span').click()

        # 할인중 클릭
        driver.find_element(
            By.XPATH, '//*[@id="filterDropdownPanel"]/div/div[1]/div[2]/div[1]').click()
        driver.implicitly_wait(1)

        # div:nth-child(2) > a > div.store-item__detail
        content = driver.find_element(
            By.CSS_SELECTOR, '#champions > div > div:nth-child(1) > div > div > div')

        num = 1

        all_champions = list(db["champion_info"].find({}))
        data = []

        while True:
            try:
                champion = content.find_element(
                    By.CSS_SELECTOR, 'div:nth-child({0}) > a > div.store-item__detail'.format(num))

            except Exception as e:
                break

            result = {}
            name = champion.find_element(By.CLASS_NAME, 'name')
            origin_price = champion.find_element(
                By.CSS_SELECTOR, 'div.prices > span:nth-child(1) > span.price.origin-price')
            price = champion.find_element(
                By.CSS_SELECTOR, 'div.prices > span:nth-child(1) > span:nth-child(3)')
            ip_price = champion.find_element(
                By.CSS_SELECTOR, 'div.prices > span:nth-child(2) > span.price')

            result["name_kr"] = name.text
            result["origin_price"] = int(origin_price.text)
            result["price"] = int(price.text)
            result["ip_price"] = int(ip_price.text)

            target_champion_info = [
                element for element in all_champions if element["kr"] == name.text]

            if target_champion_info:
                result["name_en"] = target_champion_info[0]["en"]
                result["championId"] = target_champion_info[0]["championId"]

            data.append(result)
            num += 1

        if len(data) != 0:
            db["champion_sales_info"].delete_many({})
            db["champion_sales_info"].insert_many(data)

        driver.get(
            "https://store.leagueoflegends.co.kr/skins?sort=ReleaseDate&order=DESC")

    # 페이지가 완전히 로드될 때까지 대기
        driver.implicitly_wait(5)

        # 검색필터 클릭
        driver.find_element(By.XPATH, '//*[@id="app"]/div[5]/div/div/div[1]/div[2]/div[1]/div[2]/span').click()

        # 할인중 클릭
        driver.find_element(By.XPATH, '//*[@id="filterDropdownPanel"]/div/div/div[2]/div[3]').click()

        # 동적으로 로드되는 내용 가져오기
        content = driver.find_element(By.CSS_SELECTOR, '#skins > div > div:nth-child(1) > div > div > div')

        data = []

        # 가져온 내용 data에 저장
        num = 1
        while True:
            try:
                skin = content.find_element(By.CSS_SELECTOR, 'div:nth-child({0}) >a > div.store-item__detail'.format(num))
                image = content.find_element(By.CSS_SELECTOR, 'div:nth-child({0}) >a > div.store-item__image > div'.format(num))
            except:
                break

            result = {}
            name = skin.find_element(By.CLASS_NAME, 'name')
            origin_price = skin.find_element(By.CSS_SELECTOR, 'div.prices > span > span:nth-child(2)')
            price = skin.find_element(By.CSS_SELECTOR, 'div.prices > span > span:nth-child(3)')
            image_url = image.find_element(By.CLASS_NAME, 'asset-media.image').get_attribute("data-asset-url")
            
            result["name_kr"] = name.text
            result["origin_price"] = int(origin_price.text)
            result["price"] = int(price.text)
            result["url"] = image_url
            
            data.append(result)

            num += 1

        if len(data) != 0:
            db["skin_sales_info"].delete_many({})
            db["skin_sales_info"].insert_many(data)

    
    
def update_patch_note_image(latest_version):
    #1. patch note release 링크 가져오기
    baseUrl = "https://www.leagueoflegends.com/ko-kr/news/game-updates/patch-%s-%s-notes/"
    
    split = latest_version.split(".")
    
    baseUrl%=(split[0], split[1])
    
    with webdriver.Remote(
        command_executor=config.SELENIUM_EXECUTER,  # Selenium 호스트 및 포트 설정
        options=chrome_options
    ) as driver:
        driver.get(baseUrl)
        
        img_element = driver.find_element(
            By.XPATH, '//*[@id="gatsby-focus-wrapper"]/div/section/section[1]/div[1]/img')
        
        src = img_element.get_attribute('src')
        
        db["version"].update_one({"version":latest_version}, 
                                 {"$set":{"releaseNoteUrl":baseUrl, "releaseNoteImgUrl":src}})