FROM python:3.11-slim
WORKDIR /app
RUN pip install stellar-sdk cryptography
COPY generate_key.py .
CMD ["python", "generate_key.py"]