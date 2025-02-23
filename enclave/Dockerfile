FROM python:3.11-slim
WORKDIR /app
RUN pip install stellar-sdk cryptography
COPY generate_key.py .
COPY mock_enclave_server.py .
CMD ["python", "mock_enclave_server.py"]