import os
import time
from typing import Any, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



from .base_tool import BaseTool


class WebSearchTool(BaseTool):
    """网络搜索工具，使用selenium实现真实搜索"""
    
    name = "web_search"
    description = "用于搜索互联网上的最新信息，适用于需要实时数据的问题"
    parameters = {
        "query": {
            "type": "string",
            "description": "搜索关键词"
        }
    }

    def _chrome_options(self) -> Options:
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        # opts.add_argument("--headless=new")
        # opts.add_argument("--disable-gpu")
        # opts.add_argument("--window-size=1920,1080")
        # opts.add_argument("--no-sandbox")
        # opts.add_argument("--disable-dev-shm-usage")
        return opts

    def _get_chrome_instance(self):
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if not chromedriver_path:
            raise EnvironmentError("CHROMEDRIVER_PATH 环境变量未设置")

        service = Service(executable_path=chromedriver_path)
        options = self._chrome_options()
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "错误：请提供搜索关键词"

        driver = None
        try:
            driver = self._get_chrome_instance()
            driver.get("https://www.baidu.com")
            time.sleep(1)
            text_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, "chat-textarea"))
                    )

            text_box.send_keys(query)

            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "chat-submit-button"))
            )
            submit_button.click()

            WebDriverWait(driver, 5).until(
                EC.title_contains(query[:10])
            )

            page_text = driver.find_element(By.TAG_NAME, "body").text
            # driver.quit()
            return page_text
        except WebDriverException as e:
            return f"搜索失败：浏览器驱动错误 - {str(e)}"
        except TimeoutException:
            return "搜索失败：请求超时"
        except Exception as e:
            return f"搜索失败：{str(e)}"
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
