FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Must use unbuffered output to see python stdout in Docker logs (https://stackoverflow.com/a/29745541/4206279)
CMD ["python", "-u", "./app.py"]