FROM ghcr.io/astral-sh/uv:alpine@sha256:abba5681efde355627953bb7a07b5091292628a071ebfe3ca3929fe3edb248b1 AS builder

RUN adduser -D pyuser

USER pyuser

WORKDIR /home/pyuser/app

COPY pyproject.toml uv.lock .

RUN uv sync

FROM alpine:3.22@sha256:8a1f59ffb675680d47db6337b49d22281a139e9d709335b492be023728e11715

RUN adduser -D pyuser

USER pyuser

# python is fetched here
COPY --from=builder /home/pyuser/.local /home/pyuser/.local

WORKDIR /home/pyuser/app

COPY --from=builder /home/pyuser/app .

COPY *.py .

#TODO: user
CMD ["/home/pyuser/app/.venv/bin/python", "/home/pyuser/app/main.py"]
