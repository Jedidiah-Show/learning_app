# Image tag: ruach-python-sandbox:3.12-v1
# Keep this tag in sync with SANDBOX_IMAGE in app/core/config.py (and
# app/services/judge.py). Bump the tag and rebuild whenever pins change;
# no digest pin is declared because a verified digest is not available here.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

RUN groupadd -g 65532 sandbox \
    && useradd -u 65532 -g sandbox -s /bin/false -M sandbox

# Pinned for reproducible builds. numpy/pandas/scipy/scikit-learn match
# requirements-dev.txt; the remaining pins are the current compatible
# releases verified against the same Python 3.12 scientific stack.
RUN pip install --no-cache-dir \
    numpy==2.4.6 \
    pandas==3.1.0 \
    scipy==1.17.1 \
    scikit-learn==1.9.1 \
    matplotlib==3.11.2 \
    sympy==1.14.0 \
    networkx==3.7

WORKDIR /runner
COPY runner.py /runner/runner.py
RUN chown -R 65532:65532 /runner

USER 65532:65532
ENTRYPOINT ["python", "-I", "/runner/runner.py"]
