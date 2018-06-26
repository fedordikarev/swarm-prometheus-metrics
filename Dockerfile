FROM python:3.6-alpine

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY app.py /app/
EXPOSE 5000

CMD ["/app/app.py"]
