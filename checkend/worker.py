"""Background worker for async error sending."""

import queue
import threading
import time
from typing import Optional

from checkend.client import Client
from checkend.configuration import Configuration
from checkend.notice import Notice


class Worker:
    """Background worker that sends notices asynchronously."""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.client = Client(configuration)
        self.queue: queue.Queue[Optional[Notice]] = queue.Queue(
            maxsize=configuration.max_queue_size
        )
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self._flush_event = threading.Event()
        self._flush_complete = threading.Event()

    def start(self) -> None:
        """Start the worker thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.configuration.log("debug", "Worker started")

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the worker thread and wait for pending notices."""
        if not self.running:
            return

        self.running = False

        # Signal the worker to stop
        try:
            self.queue.put(None, block=False)
        except queue.Full:
            pass

        # Wait for the thread to finish
        if self.thread:
            self.thread.join(timeout=timeout)
            self.thread = None

        self.configuration.log("debug", "Worker stopped")

    def push(self, notice: Notice) -> bool:
        """
        Add a notice to the queue.

        Returns:
            True if the notice was added, False if the queue is full
        """
        if not self.running:
            return False

        try:
            self.queue.put(notice, block=False)
            return True
        except queue.Full:
            self.configuration.log("warning", "Queue full, notice dropped")
            return False

    def flush(self, timeout: float = 5.0) -> None:
        """Wait for all queued notices to be sent."""
        if not self.running or self.queue.empty():
            return

        self._flush_complete.clear()
        self._flush_event.set()

        # Wait for flush to complete
        self._flush_complete.wait(timeout=timeout)
        self._flush_event.clear()

    def _run(self) -> None:
        """Worker thread main loop."""
        while self.running:
            try:
                # Check if we need to flush
                if self._flush_event.is_set() and self.queue.empty():
                    self._flush_complete.set()

                # Get next notice (with timeout to check running flag)
                try:
                    notice = self.queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # None signals shutdown
                if notice is None:
                    break

                # Send the notice
                self._send_with_retry(notice)
                self.queue.task_done()

            except Exception as e:
                self.configuration.log("error", f"Worker error: {e}")

        # Drain remaining items on shutdown
        self._drain_queue()

    def _send_with_retry(self, notice: Notice, max_retries: int = 3) -> None:
        """Send a notice with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                self.client.send(notice)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = (2**attempt) * 0.1  # 0.1s, 0.2s, 0.4s
                    self.configuration.log(
                        "debug", f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    msg = f"Failed to send notice after {max_retries} attempts: {e}"
                    self.configuration.log("error", msg)

    def _drain_queue(self) -> None:
        """Send all remaining notices in the queue."""
        while not self.queue.empty():
            try:
                notice = self.queue.get(block=False)
                if notice is not None:
                    self.client.send(notice)
                    self.queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                self.configuration.log("error", f"Error draining queue: {e}")
