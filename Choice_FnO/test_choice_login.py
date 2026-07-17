import os
import sys
import io
import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Fix Windows console encoding for emoji characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# -----------------------------------------
# FILL IN YOUR CREDENTIALS HERE TO TEST
# -----------------------------------------
VENDOR_ID = "NVA0088"
VENDOR_KEY = "WQCBOLGER4WMA57TV6EOZP6LEI5PT7NW"
API_KEY = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkM4M0U2ODlBRjE0NTMwQTc2QTFENzUxN0UwODAwNjdFOTI3NzM1QUYiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiIzY2ExODczOC03N2JiLTQzNzItYjMyZS03ZTNkM2UyMDJkMjIiLCJqdGkiOiI5NDcyODU3Ny1hOWQzLTQzM2YtYTVlMC03ZTdmMTlkYjI3MzAiLCJpYXQiOjE3ODQwNDQyOTAsIlVzZXJJZCI6Ik5WQTAwODgiLCJDbGlJUEFkZHJlc3MiOiIxMDMuNzYuMTAyLjE3OCIsIm5iZiI6MTc4NDA0NDI5MCwiZXhwIjoxNzg2NjM2MjkwLCJpc3MiOiJGSU5YIn0.cN_1FqxW0lD7IOpsLmeUDO189_md7y9RHoQ4EqopbELw7I0P_zEk-SsUEqMHM30m1FQlkPVpn1T-SYo9qUoL8hYJYCx17p4G1Sdy7p55GRkScJLWgvx5K8-FHuGhUrCbVBq5zecgykO2LHKCqlOsUxXTAWQ14y7-ARdty9rIkmW7kkN25uin-cabvE7gWBFvZAnEKECtsp4tTW3uf6O4P1feM2jYNp4HyBYGlEivVsqhsT-4vMw-ZyzpUC6Tdp2rfHeHtbLxHJkXw4HpZOINd9QIgPoIghL_kmJW99F9h2dp1RKYF5txm1G6wrMIlkdatEgoNKMOYFjoM67kPodv0Q"
MOBILE_NO = "7348656787"
AES_KEY = "Dh9j7pan2tRXW2uV59v521JRN2zYwDjr"
AES_IV = "trZdl9rDTCNKbmZR"
BASE_URL = "https://finx.choiceindia.com"
# -----------------------------------------

def get_encrypted_mobile(mobile_no, aes_key_str, aes_iv_str):
    aes_key_bytes = aes_key_str.encode('utf-8')
    aes_iv_bytes = aes_iv_str.encode('utf-8')
    cipher = AES.new(aes_key_bytes, AES.MODE_CBC, aes_iv_bytes)
    padded = pad(mobile_no.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')

def test_login():
    print("="*50)
    print("Choice API Login Diagnostic Script")
    print("="*50)
    
    if "YOUR_" in VENDOR_ID:
        print("❌ Please replace the placeholder credentials in this script before running.")
        return

    try:
        print(f"Encrypting Mobile Number: {MOBILE_NO}...")
        enc_mobile = get_encrypted_mobile(MOBILE_NO, AES_KEY, AES_IV)
        
        headers = {
            "VendorId": VENDOR_ID,
            "VendorKey": VENDOR_KEY,
            "Bearer": API_KEY,
            "Content-Type": "application/json"
        }
        
        # 1. LoginTOTP
        print(f"\n[Step 1] Calling LoginTOTP...")
        url0 = f"{BASE_URL.rstrip('/')}/api/OpenAPIV1/LoginTOTP"
        payload0 = {"MobileNo": enc_mobile}
        resp0 = requests.post(url0, headers=headers, json=payload0)
        
        print(f"Status Code: {resp0.status_code}")
        print(f"Response: {resp0.text}")
        
        if resp0.status_code != 200 or resp0.json().get("Status") != "Success":
            print("❌ LoginTOTP Failed. Check your Bearer API Key, VendorId, and VendorKey.")
            return

        # 2. GetClientLoginTOTP
        print(f"\n[Step 2] Calling GetClientLoginTOTP...")
        url1 = f"{BASE_URL.rstrip('/')}/api/OpenAPIV1/GetClientLoginTOTP"
        payload1 = {"MobileNo": enc_mobile}
        resp1 = requests.post(url1, headers=headers, json=payload1)
        
        print(f"Status Code: {resp1.status_code}")
        print(f"Response: {resp1.text}")
        
        if resp1.status_code != 200 or resp1.json().get("Status") != "Success":
            print("❌ GetClientLoginTOTP Failed. Check your Mobile No and AES Keys.")
            return
            
        otp = resp1.json().get("Response")
        print(f"Extracted OTP: {otp}")
        
        # 3. ValidateTOTP
        print(f"\n[Step 3] Calling ValidateTOTP...")
        url2 = f"{BASE_URL.rstrip('/')}/api/OpenAPIV1/ValidateTOTP"
        payload2 = {"MobileNo": enc_mobile, "OTP": str(otp)}
        resp2 = requests.post(url2, headers=headers, json=payload2)
        
        print(f"Status Code: {resp2.status_code}")
        print(f"Response: {resp2.text}")
        
        if resp2.status_code == 200 and resp2.json().get("Status") == "Success":
            print("\n✅ LOGIN SUCCESSFUL!")
            
            response_data = resp2.json().get("Response", {})
            session_id = None
            if isinstance(response_data, str):
                session_id = response_data
            elif isinstance(response_data, dict):
                session_id = response_data.get("SessionId") or response_data.get("session_id") or response_data.get("AccessToken")
                
            print(f"🎉 Valid Session ID Acquired: {session_id}")
        else:
            print("\n❌ ValidateTOTP FAILED.")

    except Exception as e:
        print(f"\n❌ Error during login execution: {e}")

if __name__ == "__main__":
    test_login()
