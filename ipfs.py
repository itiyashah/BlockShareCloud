import os
import requests
from dotenv import load_dotenv

load_dotenv()

class IPFSClient:
    def __init__(self):
        self.api_key = os.getenv("PINATA_API_KEY")
        self.secret_key = os.getenv("PINATA_SECRET_API_KEY")
        self.pinata_endpoint = "https://api.pinata.cloud/pinning/pinFileToIPFS"

    def upload_file(self, file_path):
        # If Pinata keys are provided, upload to Pinata Enterprise Cloud
        if self.api_key and self.secret_key:
            headers = {
                "pinata_api_key": self.api_key,
                "pinata_secret_api_key": self.secret_key
            }
            with open(file_path, "rb") as file_data:
                response = requests.post(
                    self.pinata_endpoint,
                    files={"file": file_data},
                    headers=headers
                )
            if response.status_code == 200:
                return response.json()["IpfsHash"]
        
        # Fallback message or exception if cloud keys are missing
        raise Exception("Pinata API keys not configured or upload failed.")

    def download_file(self, ipfs_hash, download_folder):
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        
        # Public gateway download URL for enterprise retrieval
        gateway_url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"
        response = requests.get(gateway_url)
        
        file_path = os.path.join(download_folder, ipfs_hash)
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        return file_path
