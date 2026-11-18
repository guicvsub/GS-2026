# Imagem do Airflow com as dependências do pipeline.
# As versões seguem o arquivo de constraints oficial do Airflow para não quebrar o scheduler.
FROM apache/airflow:2.10.5-python3.12

ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.12

RUN pip install --no-cache-dir \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
      PyMySQL pyarrow cryptography

# O código do pipeline e os DAGs entram por volume (docker-compose.yml) para
# permitir editar sem rebuild; o PYTHONPATH aponta para /opt/airflow.
ENV PYTHONPATH=/opt/airflow
