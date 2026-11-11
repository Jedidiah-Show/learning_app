FROM python:3.13-alpine

RUN addgroup -S -g 65532 sandbox \
    && adduser -S -D -H -u 65532 -G sandbox sandbox
WORKDIR /runner
COPY runner.py /runner/runner.py
USER 65532:65532
ENTRYPOINT ["python", "-I", "/runner/runner.py"]
