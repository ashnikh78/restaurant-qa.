D:\softwares\python\python.exe -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000

pip install -r requirements.txt && mkdir data && uvicorn src.main:app --reload

 uvicorn src.main:app --reload