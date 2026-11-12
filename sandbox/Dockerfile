FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

RUN groupadd -g 65532 sandbox \
    && useradd -u 65532 -g sandbox -s /bin/false -M sandbox

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    scipy \
    scikit-learn \
    matplotlib \
    sympy \
    networkx

WORKDIR /runner
COPY runner.py /runner/runner.py
RUN chown -R 65532:65532 /runner

USER 65532:65532
ENTRYPOINT ["python", "-I", "/runner/runner.py"]
