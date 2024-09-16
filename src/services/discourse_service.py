import requests
from utils.logger import logger


class DiscourseService:   

    def discourse_search(self, search_keyword: str) -> list:
        results = []
        flag = True
        page = 1
        while flag:
            #print(f"Fetching page {page}")
            url = f"https://discourse.onlinedegree.iitm.ac.in/search?q={search_keyword}&{page}"
            headers = {
            "Cookie": "_ga_5HTJMW67XK=GS1.1.1676955975.1.0.1676955975.0.0.0; _ga=GA1.1.929711223.1676955975; _ga_WGM85Z9ZZV=GS1.1.1676955975.1.0.1676955975.0.0.0; _t=JVcQznFPTygnuJ2iyoFgLY27AruyZZY2jhtxouuiuJF5kE0kO2Sw%2BtGmF6Cnap4FKdxyDpD2cS5nS9NgG5%2BZU36UhsJql%2F2uQj88omgQVbM6%2FjxmFPlprJAjuIO1hV6vMIdQ1lvpMIHv4jabp6%2F2CzoUt1NXMX7rueYCa8pP1njLehxtFFUKrFQHM%2Bj6Cfvh92H0az4hWZKSpcAWHTqT%2BjvDvUXlGgdpVU5yOuv8TNbq6meeHg77BNeoM4Zov9bk%2BzFhIcADIQ%2Fz%2FjQugIH%2BGDdbd%2FW8z%2Fwfm95delA2m%2FGL4ZP6GqldLpXCw2s%3D--HJf3Q6mAGcDe8oHm--fWdy%2FQlqcEgD314o1Jln9A%3D%3D; _forum_session=yompkbKJxvoSxjiloFSHnJbqMKOvVdnxp0ZLZyVOlZNk8Vmvkj1Mc8tlPdul03hKbsdZGzScNCoOv3PM0P0VCCM7YG2mZrQE0GzMa7%2FI12xV9nBVZS2bVcBTw0RVW%2Fs%2F9p7Lf1h2JptKcoh6B1QZlsujxSkfM4tdt%2FaJ9IJSgewyMD2M8kdWUvlVDxAs2a6VLup7Czdf6XmiITo6DPFXWFKcDsjDG77fbFDFImluyHNvNkmKvi6pHTn1rdZXvpXm9QF0iHY%2FsBukLR%2BM0OAbCb977AqCgpHgVANsDrWaeSJMxvxJsPL0JS1lyB3XEo5b8UPz9GBv9GIxMKVpmlrtPgiyaa7hSiIow%2B5qI6mhBlVnRWqtxyrf9NVIk7vvTQ%3D%3D--64z0u5gvLqnPCS2J--tuVq6tIwW%2FK0XS5sAcwEEQ%3D%3D",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "x-csrf-token": "hEcPa4oss9rkqm-6bShXc1eGupLwTmkyV0dE4C8UJEYDpBkRBDAvfhfBvBqQfkn1h0Xf9cCP5nEeVMhrBnwitQ",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers)
            #making the request

            if response.status_code == 200:
                #print('Request successful')
                data = response.json()
        
                for topic in data['topics']:
                    if topic['has_accepted_answer']:
                        results.append({
                            'id': topic['id'],
                            'Title': topic['title'],
                            'Tags': ', '.join(topic.get('tags', [])),
                            'Post Link': f"https://discourse.onlinedegree.iitm.ac.in/t/{topic['slug']}/{topic['id']}"
                        })

                #time.sleep(0.5)  # Add a delay to avoid overwhelming the server
            else:
                print(f'Error: Status code {response.status_code}')
                flag = False
            page += 1

            # You might want to add a condition to stop after a certain number of pages
            if page > 20:  # For example, stop after 10 pages
                flag = False

        return results


