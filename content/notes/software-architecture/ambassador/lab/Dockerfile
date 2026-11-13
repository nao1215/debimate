FROM python:3.13-slim
RUN pip install --no-cache-dir redis==8.0.1
COPY writer.py /writer.py
CMD ["python", "-u", "/writer.py"]
