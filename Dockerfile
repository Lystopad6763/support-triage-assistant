# One image, one process: Python serves both the API and the page.
#
# There is no node in here on purpose. web/dist is committed, so a deploy never
# runs npm install against the network while a machine is trying to boot. The
# slowest and least reliable step happens once, on a laptop, before the push.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Its own layer, so it rebuilds only when requirements.txt changes and editing
# a prompt redeploys in seconds instead of reinstalling numpy. All seven
# packages ship cp313 wheels, so this image needs no compiler.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what answers a request. The 37 MB corpus, the runs, the benchmarks and
# the 282 raw store dumps stay out: they are how the numbers were produced,
# not what the page needs to produce an answer.
COPY app/ app/
COPY prompts/ prompts/
COPY web/dist/ web/dist/
COPY data/kb/index.json data/kb/vectors__*.json data/kb/
COPY data/collect/raw/helpcenter/en-us.json data/collect/raw/helpcenter/
COPY data/collect/raw/faq/asknebula.json data/collect/raw/faq/
COPY data/collect/raw/policies/asknebula_policies.json data/collect/raw/policies/

# Not root. The sqlite cache opened at runtime lands under /srv, which this
# user owns; that cache is deliberately ephemeral and nothing depends on it
# surviving a restart.
RUN useradd --create-home --shell /bin/bash srvuser && chown -R srvuser /srv
USER srvuser

EXPOSE 8080

# No --reload, and one worker rather than several. This process holds the index
# and the daily-spend counter in memory; a second worker would keep its own copy
# of the counter and the $5 ceiling would quietly become $10.
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]
