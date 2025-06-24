import random
import threading
import time

import numpy as np

from logger import logger


class WorkerThread(threading.Thread):
    def __init__(self, process_id, monitor, max_claim):
        super().__init__()
        self.process_id = process_id
        self.monitor = monitor
        self.max_claim = np.array(max_claim, dtype=int)
        self.currently_allocated = np.zeros(monitor.num_resources, dtype=int)

    def run(self):
        logger.info(self.process_id, "Запущен.")
        self.monitor.set_max_claim(self.process_id, self.max_claim)

        for _ in range(random.randint(2, 4)):
            time.sleep(random.uniform(0.5, 1.5))
            needed = self.max_claim - self.currently_allocated
            if np.all(needed == 0):
                break

            request = [random.randint(0, n) if n > 0 else 0 for n in needed]
            request = np.array(request, dtype=int)

            if np.all(request == 0):
                continue

            while not self.monitor.request_resources(self.process_id, request):
                logger.info(self.process_id, "...повторяет попытку после ожидания.")
                time.sleep(random.uniform(0.2, 0.5))

            self.currently_allocated += request
            logger.info(self.process_id, f"Использует ресурсы: {self.currently_allocated}")
            time.sleep(random.uniform(1, 2.0))

            if np.any(self.currently_allocated > 0):
                release = [random.randint(0, a) for a in self.currently_allocated]
                release = np.array(release, dtype=int)
                if np.any(release > 0):
                    self.monitor.release_resources(self.process_id, release)
                    self.currently_allocated -= release

        if np.any(self.currently_allocated > 0):
            logger.info(self.process_id, f"Завершает работу, освобождая всё: {self.currently_allocated}")
            self.monitor.release_resources(self.process_id, self.currently_allocated)

        logger.info(self.process_id, "Завершен.")
