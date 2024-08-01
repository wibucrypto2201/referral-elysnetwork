import os
import csv
import psutil
import random
from time import sleep
from threading import Semaphore, Thread

from selenium import webdriver as uc
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchWindowException

from selenium_authenticated_proxy import SeleniumAuthenticatedProxy

window_width = 1200
window_height = 1000
webs = []

def load_private_keys_and_proxies(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()
    private_keys_and_proxies = [line.strip().split('|') for line in lines]
    return private_keys_and_proxies

def load_links(file_path):
    with open(file_path, "r") as file:
        links = file.readlines()
    links = [link.strip() for link in links]
    return links

def load_user_agents(file_path):
    with open(file_path, "r") as file:
        user_agents = file.readlines()
    user_agents = [ua.strip() for ua in user_agents]
    return user_agents

def arrange_windows(drivers, items_per_row, window_width, window_height):
    if not drivers:
        print("No drivers to arrange.")
        return
    screen_width = drivers[0].execute_script("return window.screen.availWidth")
    screen_height = drivers[0].execute_script("return window.screen.availHeight")
    for i, driver in enumerate(drivers):
        try:
            x_position = (i % items_per_row) * window_width
            y_position = (i // items_per_row) * window_height
            driver.set_window_position(x_position, y_position)
            driver.set_window_size(window_width, window_height)
        except NoSuchWindowException:
            print(f"Window for driver {i} is no longer available. Skipping arrangement.")

def kill_processes(web_pid):
    try:
        parent = psutil.Process(web_pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

def remove_failed_key(line):
    with open("private_keys.txt", "r") as file:
        lines = file.readlines()
    with open("private_keys.txt", "w") as file:
        for l in lines:
            if l.strip() != line.strip():
                file.write(l)
    with open("fail.txt", "a") as file:
        file.write(f"{line}\n")

def task(private_key, proxy, link_ref, line, semaphore, user_agents):
    global webs
    web = None
    web_pid = None
    try:
        user_agent = random.choice(user_agents)
        options = ChromeOptions()
        options.add_argument(f"user-agent={user_agent}")
        options.add_extension("Keplr.crx")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument('--log-level=3')
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--force-device-scale-factor=0.4")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--disable-blink-features=AutomationControlled')

        username, password_host_port = proxy.split('@')[0], proxy.split('@')[1]
        username, password = username.split(':')
        host, port = password_host_port.split(':')

        proxy_url = f"http://{username}:{password}@{host}:{port}"

        proxy_helper = SeleniumAuthenticatedProxy(proxy_url=proxy_url)
        proxy_helper.enrich_chrome_options(options)
        web = uc.Chrome(chrome_options=options)
        web_pid = web.service.process.pid
        webs.append(web)
        arrange_windows(webs, 4, window_width, window_height)
        current = web.current_window_handle
        web.get("https://www.google.com/")

        web.switch_to.window(web.window_handles[-1])
        wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Create a new wallet')]]"))) 

        wait(web, 5).until(EC.presence_of_element_located((
            By.XPATH, "/html/body/div/div/div[2]/div/div/div/div/div/div[3]/div[3]/button"
        ))).click()
        wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Welcome Back to Keplr')]]"))) 
        wait(web, 5).until(EC.presence_of_element_located((
            By.XPATH, "/html/body/div/div/div[2]/div/div/div[2]/div/div/div/div[1]/div/div[5]/button"
        ))).click()
        wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Import Existing Wallet')]]")))
        print("Waiting Import Wallet")
        web.execute_script("""
            document.querySelector("#app > div > div.sc-bczRLJ.hWsPPf > div > div > div:nth-child(3) > div > div > form > div.sc-bczRLJ.gNsQDg > div > button:nth-child(6)").click();
        """)
        #send_keys
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div/div/div[2]/div/div/div[3]/div/div/form/div[3]/div/div/div[1]/div/div[2]/div/div/input",
                )
            )
        ).click()
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div/div/div[2]/div/div/div[3]/div/div/form/div[3]/div/div/div[1]/div/div[2]/div/div/input",
                )
            )
        ).send_keys(private_key)

        web.find_element(By.CSS_SELECTOR, "#app > div > div.sc-bczRLJ.hWsPPf > div > div > div:nth-child(3) > div > div > form > div.sc-bczRLJ.gelWte > div > button").click()
        wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Set Up Your Wallet')]]")))
        web.execute_script("""
            var input1 = document.querySelector("#app > div > div.sc-bczRLJ.hWsPPf > div > div > div:nth-child(4) > div > div > form > div > div:nth-child(1) > div.sc-iTONeN.iLa-DOx > div > div > input");
            input1.value = "1";
        """)
        # Gửi giá trị "WibuneverDie69" vào ô nhập liệu thứ hai
        web.execute_script("""
            var input2 = document.querySelector("#app > div > div.sc-bczRLJ.hWsPPf > div > div > div:nth-child(4) > div > div > form > div > div:nth-child(3) > div.sc-iTONeN.iLa-DOx > div > div > input");
            input2.value = "WibuneverDie69";
        """)

        # Gửi giá trị "WibuneverDie69" vào ô nhập liệu thứ ba
        web.execute_script("""
            var input3 = document.querySelector("#app > div > div.sc-bczRLJ.hWsPPf > div > div > div:nth-child(4) > div > div > form > div > div:nth-child(5) > div.sc-iTONeN.iLa-DOx > div > div > input");
            input3.value = "WibuneverDie69";
        """)
        # Click vào nút button
        for _ in range(4):
            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div/div/div[2]/div/div/div[4]/div/div/form/div/div[7]/button",
                    )
                )
            ).click()
            sleep(0.1)

        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div/div/div[2]/div/div/div/div/div/div[9]/div/button",
                )
            )
        ).click()
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div/div/div[2]/div[5]/div[1]/button",
                )
            )
        ).click()
        print("Import Wallet Successful")
        #connect
        web.switch_to.window(web.window_handles[0])
        web.get(link_ref)
        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[1]/section/div/main/div[3]/div/div[4]/div[1]",
                )
            )
        ).click()
        print("Waiting Connect Wallet")
        max_attempts = 30
        attempts = 0
        while len(web.window_handles) < 2 and attempts < max_attempts:
            sleep(1)
            attempts += 1

        if len(web.window_handles) >= 2:
            web.switch_to.window(web.window_handles[-1])
            wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'Elys Network')]]")))
            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div/div/div/div[3]/div[2]/div/button",
                    )
                )
            ).click()
            web.close()
        web.switch_to.window(web.window_handles[0])
        max_attempts = 30
        attempts = 0
        while len(web.window_handles) < 2 and attempts < max_attempts:
            sleep(1)
            attempts += 1

        if len(web.window_handles) >= 2:
            web.switch_to.window(web.window_handles[-1])
            wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'Confirm Transaction')]]")))

            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div/div/div/div[3]/div[2]/button",
                    )
                )
            ).click()
        print("Connect Wallet Succesful")
        web.switch_to.window(web.window_handles[0])
        wait(web, 100).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Total Reward Pool')]]")))
        web.get("https://testnet.elys.network/faucet")
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Claim Testnet Tokens')]]")))

        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[2]/div[2]/button",
                )
            )
        ).click()
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Sign in to Elys')]]")))

        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/dialog/div/div/div[2]/div[1]/button",
                )
            )
        ).click()
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Connect with')]]")))

        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/dialog[2]/div/div/div[2]/button[1]",
                )
            )
        ).click()
        max_attempts = 30
        attempts = 0
        while len(web.window_handles) < 2 and attempts < max_attempts:
            sleep(1)
            attempts += 1

        if len(web.window_handles) >= 2:
            web.switch_to.window(web.window_handles[-1])
            wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'Requesting Connection')]]")))

            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div/div/form/div[3]/div[2]/div/button",
                    )
                )
            ).click()
        web.switch_to.window(web.window_handles[0])
        wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
        "//*[text()[contains(.,'Claim Tokens')]]")))

        wait(web, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[2]/div[2]/button",
                )
            )
        ).click()
        
        # Check for the success message or the already claimed message
        try:
            wait(web, 30).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'Tokens claimed successfully!')]]")))
            print("Faucet Sucessful")
            web.get("https://testnet.elys.network/swap#ELYS/USDC")
            wait(web, 60).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'0.3')]]")))
            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[2]/div/div[1]/div[2]/div/div[2]/div[1]/div[2]/div[1]/div[1]/input",
                    )
                )
            ).send_keys("0.1")
            print("Waiting swap ELYS/USDC")
            sleep(1)
            waitelement = wait(web, 50)
            button = waitelement.until(EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'flex') and contains(@class, 'box-border') and contains(@class, 'duration-100') and contains(@class, 'heading-auto') and contains(@class, 'justify-center') and contains(@class, 'items-center') and contains(@class, 'disabled:cursor-not-allowed') and contains(@class, 'disabled:opacity-50') and contains(@class, 'transition-none') and contains(@class, 'text-white') and contains(@class, 'active:opacity-70') and contains(@class, 'enabled:bg-secondaryGray-gradient') and contains(@class, 'border-[#384350]') and contains(@class, 'border') and contains(@class, 'hover:opacity-90') and contains(@class, 'disabled:bg-charcoal-800') and contains(@class, 'disabled:text-charcoal-500') and contains(@class, 'disabled:border-[transparent]') and contains(@class, 'disabled:!opacity-100') and contains(@class, 'h-14') and contains(@class, 'min-w-14') and contains(@class, 'px-[26px]') and contains(@class, 'text-lg') and contains(@class, 'leading-normal') and contains(@class, 'font-medium') and contains(@class, 'gap-2.5') and contains(@class, 'rounded-xl') and contains(@class, 'w-full') and contains(@class, '!px-2.5')]")))

            # Click the button
            button.click()
            max_attempts = 30
            attempts = 0
            while len(web.window_handles) < 2 and attempts < max_attempts:
                sleep(1)
                attempts += 1

            if len(web.window_handles) >= 2:
                web.switch_to.window(web.window_handles[-1])
                wait(web, 10).until(EC.presence_of_element_located((By.XPATH, 
                "//*[text()[contains(.,'Confirm Transaction')]]")))

                wait(web, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div/div/div/div[3]/div[2]/button",
                        )
                    )
                ).click()
            web.switch_to.window(web.window_handles[0])
            print("Swap DONE")
            sleep(3)
            web.get("https://testnet.elys.network/earn/staking")
            wait(web, 100).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'0%')]]")))
            sleep(3)
            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[2]/div[1]/div[1]/button[2]",
                    )
                )
            ).click()
            print("Waiting Stake USDC")
            wait(web, 100).until(EC.presence_of_element_located((By.XPATH, 
            "//*[text()[contains(.,'Enter Amount')]]")))
            wait(web, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/dialog/div/div/form/div/div[1]/input",
                    )
                )
            ).send_keys("0.5")
            sleep(2.5)
            js_script = 'document.querySelector("body > dialog > div > div > form > button").click();'

            # Execute the JavaScript
            web.execute_script(js_script)

            max_attempts = 30
            attempts = 0
            while len(web.window_handles) < 2 and attempts < max_attempts:
                sleep(1)
                attempts += 1

            if len(web.window_handles) >= 2:
                web.switch_to.window(web.window_handles[-1])
                wait(web, 50).until(EC.presence_of_element_located((By.XPATH, 
                "//*[text()[contains(.,'Confirm Transaction')]]")))

                wait(web, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "/html/body/div[1]/div/div/div/div[1]/div[2]/div/div/div/div/div[3]/div[2]/button",
                        )
                    )
                ).click()
                sleep(6)
            web.switch_to.window(web.window_handles[0])
            print("Stake USDC DONE")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            remove_failed_key(line)
            if web:
                webs.remove(web)
                web.close()
                web.quit()
                web = None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        remove_failed_key(line)
        if web:
            webs.remove(web)
            web.close()
            web.quit()
            web = None
    finally:
        if web:
            webs.remove(web)
            web.close()
            web.quit()
            web = None
        semaphore.release()
        if web_pid:
            kill_processes(web_pid)

def main():
    private_keys_file = "private_keys.txt"
    linkref_file = "linkref.txt"
    user_agents_file = "ua.txt"
    
    private_keys_and_proxies = load_private_keys_and_proxies(private_keys_file)
    links = load_links(linkref_file)
    user_agents = load_user_agents(user_agents_file)
    
    max_concurrent_tasks = int(input("Enter your threads : "))
    semaphore = Semaphore(max_concurrent_tasks)

    for private_key, proxy in private_keys_and_proxies:
        line = f"{private_key}|{proxy}"
        link_ref = random.choice(links)
        semaphore.acquire()
        Thread(target=task, args=(private_key, proxy, link_ref, line, semaphore, user_agents)).start()

if __name__ == '__main__':
    main()
