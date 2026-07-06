import functools

from textual.worker import WorkerCancelled

# A `@work` method can be cancelled mid-flight — the app shutting down, or a
# newer `@work(exclusive=True)` call superseding it — while it's still
# awaiting a slow/failed network call. If its own error handling then tries
# to `query_one(...).update(...)` a widget, the screen may already be torn
# down, and that update itself raises NoMatches — crashing on shutdown
# instead of exiting cleanly. Every screen's worker had its own copy of this
# guard; centralized here so a worker only needs one extra line.


def safe_worker(func):

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            await func(self, *args, **kwargs)
        except WorkerCancelled:
            return
        except Exception:
            if not self.is_running:
                return
            raise

    return wrapper
