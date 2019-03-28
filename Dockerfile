FROM python:3.6-alpine

RUN apk add --no-cache curl

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY app.py /app/
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s\
  CMD curl -fs localhost:5000/healthcheck || exit 1

CMD ["/app/app.py"]
