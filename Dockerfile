# One image, one process: Python serves both the API and the page.
#
# There is no node in here on purpose. web/dist is committed, so a deploy never
# runs npm install against the network while a machine is trying to boot. The
# slowest and least reliable step happens once, on a laptop, before the push.
#
# Single stage, and that is measured rather than assumed: a multi-stage version
# of this file was built side by side and came out at exactly the same 354 MB.
# There is nothing for a builder stage to discard - seven pinned packages that
# all ship cp313 wheels, no compiler, no apt cache, and pip's own cache already
# off. Multi-stage earns its 5x against torch and CUDA, not against this.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Its own layer, so it rebuilds only when requirements.txt changes and editing
# a prompt redeploys in seconds instead of reinstalling numpy. Every version in
# that file is pinned, which is the same reason a run file records the model
# that produced its numbers: a result you cannot rebuild is not a result.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what answers a request. The 37 MB corpus, the runs, the benchmarks and
# the 282 raw store dumps stay out: they are how the numbers were produced,
# not what the page needs to produce an answer. Measured inside the image:
# 119 MB of packages (70 of them numpy), 21 MB of stdlib, 9 MB of ours.
COPY app/ app/
COPY prompts/ prompts/
COPY web/dist/ web/dist/
COPY data/kb/index.json data/kb/vectors__*.json data/kb/
COPY data/collect/raw/helpcenter/en-us.json data/collect/raw/helpcenter/
COPY data/collect/raw/faq/asknebula.json data/collect/raw/faq/
COPY data/collect/raw/policies/asknebula_policies.json data/collect/raw/policies/

# Not root. Whoever gets through Python gets a user who owns one directory and
# nothing else. The sqlite cache opened at runtime lands under /srv, which this
# user owns; that cache is deliberately ephemeral.
RUN useradd --create-home --uid 1000 --shell /bin/bash srvuser \
 && chown -R srvuser /srv
USER srvuser

EXPOSE 8080

# Not a bare GET. /health answers 200 even when the index failed to load - it
# reports that in a field, not in the status code - so a check that reads only
# the code would call a broken container healthy. This one reads the field.
#
# fly.io ignores this instruction and runs the check from fly.toml instead; it
# is here for docker run and for anyone who drops this into a compose file.
#
# start-period 20s against a measured 2s boot: the margin is for a cold host,
# not for anything this process does. Worth knowing why it can afford to be
# small - uvicorn runs the startup handler BEFORE it binds the socket, so the
# port does not answer at all until the index is in memory, and a failure to
# load it kills the process rather than serving a page that cannot answer.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx, sys; sys.exit(0 if httpx.get('http://127.0.0.1:8080/health', timeout=3).json().get('ok') else 1)"

# No --reload, and one worker rather than several. This process holds the index
# and the daily-spend counter in memory; a second worker would keep its own copy
# of the counter and the $5 ceiling would quietly become $10.
#
# --timeout-graceful-shutdown: a redeploy that arrives while somebody is waiting
# on a draft should let that request finish. Fifteen seconds is well past the
# measured p50 of 1.5 s and past any provider call that has not already timed
# out on its own.
CMD ["uvicorn", "app.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--timeout-graceful-shutdown", "15"]
