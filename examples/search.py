import requests
from examples.utils import get_token, get_env_var

def main():
    token = get_token()
    
    url = f"{get_env_var('CRM_BASE_URL')}/rest/external/site/1/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
        
    query = "SELECT FD_316 FROM MODULE_14 WHERE FD_316 = 2828" 

    params = {"returnAllFields": False, "limit": 5, "start": 1}

    resp = requests.post(url, headers=headers, data=query, params=params, timeout=30)
    
    res = resp.json()['result']
       
    print(res)


if __name__ == "__main__":
    main()
