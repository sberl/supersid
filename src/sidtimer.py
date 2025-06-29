#!/usr/bin/env python3
"""Class SidTimer.

Define a timer with autocorrection to ensure that data acquisition is done
on the 'interval' and as accurately as possible.
The autocorrection compensates for the micro-seconds lost from one tick
    to the next.
Implementation examples are provided at the source's end,
    which can be used to test the module/class.
"""
import time
from datetime import datetime, timezone
import threading


class SidTimer:
    """Keep track of time."""

    def __init__(self, interval, callback):
        """Synchronize the timer and start the trigger mechanism.

        Public properties:
        - start_time: reference starting time.time() in local time
            *on the interval* (synchro)
        - expected_time: theoretical time the trigger should happen
            as 'start_time synchronized to a multiple of interval'
        - time_now: real time.time() when the trigger happened
        """
        self.version = "1.3.1 20130907"
        self.callback = callback
        self.interval = interval
        self.lock = threading.Lock()

        self.time_now = time.time()
        self.utc_now = datetime.now(timezone.utc)
        self.data_index = 0

        # wait for synchro on the next 'interval' sec
        now = time.gmtime()
        while now.tm_sec % self.interval != 0:
            time.sleep(0.05)
            now = time.gmtime()
        #  request a Timer
        self.start_time = int(time.time() / self.interval) \
            * self.interval
        self.expected_time = self.start_time + self.interval
        self._timer = threading.Timer(self.expected_time - time.time(),
                                      self._ontimer)
        self._timer.start()

    def _ontimer(self):
        """Retrigger a timer for the next INTERVAL.

        with adjustment if necessary
        i.e. running late/fast then perform callback

        If _ontimer() triggers before expected_time or after expected_time_max,
        this is an error that can cause the hourly save to be missed. Even worse
        the creation of a new day could be missed. Let's create a warning on the
        console if an issue with the timer reliabilitry is identified.
        """
        with self.lock:     # only one timer callback at a time
            self.time_now = time.time()
            if (self.time_now < self.expected_time):
                print(f"{datetime.fromtimestamp(self.time_now, timezone.utc)} busy waiting "
                      f"{int((self.expected_time - self.time_now) * 1000000)} µs")
                while self.time_now < self.expected_time:
                    self.time_now = time.time()

            self.utc_now = datetime.fromtimestamp(self.time_now, timezone.utc)
            self._timer = threading.Timer(self.interval
                                          + self.expected_time
                                          - self.time_now, self._ontimer)
            self._timer.start()
            self.data_index = int((self.utc_now.hour
                                   * 3600
                                   + self.utc_now.minute
                                   * 60 + self.utc_now.second) / self.interval)

            expected_time_max = self.expected_time + self.interval
            if (self.time_now < self.expected_time) or (self.time_now >= expected_time_max):
                print("WARNING: Hard realtime violation in SidTimer._ontimer(). "
                      f"expected: [{self.expected_time}..{expected_time_max}) "
                      f"found: {self.time_now}. "
                      "Please report at 'https://github.com/sberl/supersid/issues/107'. ")

            self.expected_time += self.interval
            # callback to perform tasks
            self.callback()

    def stop(self):
        """Cancel the timer currently running in background."""
        self._timer.cancel()

    def get_utc_now(self):
        """Get the UTC time now."""
        return self.utc_now.strftime("%Y-%m-%d %H:%M:%S.%f")


if __name__ == '__main__':
    TIME_INTERVAL = 5.0  # seconds
    TEST_LENGTH = 90.0  # seconds
    FORCE_ERROR = True

    class TestSidTimerSubclass(SidTimer):
        """Example of SidTimer implementation.

        by extending SidTimer class and inheriting its properties
        """

        def __init__(self, interval):
            print("Waiting for synchronization ... ", end='')
            SidTimer.__init__(self, interval, self.on_timer_event)
            print("done.")
            self.max_plus_error, self.max_minus_error = 0, 0

        def on_timer_event(self):
            """Call back function to do tasks when Timer is triggered.

            In this test class, only display some tracking on the
            timer's accuracy.
            """
            time_error = self.time_now - (self.expected_time - self.interval)
            if time_error > 0 and time_error > self.max_plus_error:
                self.max_plus_error = time_error
            elif time_error < 0 and time_error < self.max_minus_error:
                self.max_minus_error = time_error

            print("Idx", self.data_index, "now:", self.time_now,
                  "expect_time:", self.expected_time - self.interval)
            print(" err:", time_error,
                  f"interval: {self.expected_time - self.time_now}",
                  datetime.now(timezone.utc))
            if FORCE_ERROR and ((self.time_now % 60) >= (60 - TIME_INTERVAL)):
                # will trigger at hh:mm:55
                # and cause hh:mm:00 .. hh:mm:04.9999 to be missed
                print(f"FORCE_ERROR: sleeping {2 * TIME_INTERVAL} seconds at "
                      f"{self.time_now} ...")
                time.sleep(2 * TIME_INTERVAL)
                print(f"FORCE_ERROR: ... wakeup at {time.time()}")

        def cancel_timer(self):
            """ Cancel the timer. """
            self.stop()

    class TestSidTimerSimple:
        """Example of SidTimer implementation.

        Using a local variable 'sid_timer' to handle the new SidTimer instance
        """

        def __init__(self, interval):
            print("Waiting for synchronization ... ", end='')
            self.sid_timer = SidTimer(interval, self.on_timer_event)
            print("done.")
            self.max_plus_error, self.max_minus_error = 0, 0

        def on_timer_event(self):
            """Call back function to do tasks when Timer is triggered.

            In this test class, only display some tracking on the
            timer's accuracy.
            """
            time_error = self.sid_timer.time_now - \
                (self.sid_timer.expected_time - self.sid_timer.interval)
            if time_error > 0 and time_error > self.max_plus_error:
                self.max_plus_error = time_error
            elif time_error < 0 and time_error < self.max_minus_error:
                self.max_minus_error = time_error

            print("Idx", self.sid_timer.data_index, "now:",
                  self.sid_timer.time_now, "expect_time:",
                  self.sid_timer.expected_time - self.sid_timer.interval)
            print(" err:", time_error,
                  f"interval: {self.sid_timer.expected_time - self.sid_timer.time_now}",
                  datetime.now(timezone.utc))
            if FORCE_ERROR and ((self.sid_timer.time_now % 60) >= (60 - TIME_INTERVAL)):
                # will trigger at hh:mm:55
                # and cause hh:mm:00 .. hh:mm:04.9999 to be missed
                print(f"FORCE_ERROR: sleeping {2 * TIME_INTERVAL} seconds at "
                      f"{self.sid_timer.time_now} ...")
                time.sleep(2 * TIME_INTERVAL)
                print(f"FORCE_ERROR: ... wakeup at {time.time()}")

        def cancel_timer(self):
            """ Cancel the timer. """
            self.sid_timer.stop()

# ------------------------------------------------------------------------
    # Test both 'TestSidTimerSimple' and 'TestSidTimerSubclass'.
    # Results shall be the same.

    print("\nTestSidTimerSimple")
    tst = TestSidTimerSimple(TIME_INTERVAL)
    try:
        time.sleep(TEST_LENGTH)  # do nothing while testing timer's accuracy
    except (KeyboardInterrupt, SystemExit):
        pass

    # cleanup and show max errors
    tst.cancel_timer()
    print(f"maximum too late by: {tst.max_plus_error} seconds")
    print(f"maximum too early by: {tst.max_minus_error} seconds")

    print("\nTestSidTimerSubclass")
    tst = TestSidTimerSubclass(TIME_INTERVAL)
    try:
        time.sleep(TEST_LENGTH)  # do nothing while testing timer's accuracy
    except (KeyboardInterrupt, SystemExit):
        pass

    # cleanup and show max errors
    tst.cancel_timer()
    print(f"maximum too late by: {tst.max_plus_error} seconds")
    print(f"maximum too early by: {tst.max_minus_error} seconds")
