import threading

import numpy as np

from logger import logger


class DeadlockPreventerMonitor:
    def __init__(self, available_resources, num_processes, matrix_logger=None):
        self.num_resources = len(available_resources)
        self.num_processes = num_processes
        self.available = np.array(available_resources, dtype=int)
        self.max_claim = np.zeros((num_processes, self.num_resources), dtype=int)
        self.allocation = np.zeros((num_processes, self.num_resources), dtype=int)
        self.need = np.zeros((num_processes, self.num_resources), dtype=int)
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.matrix_logger = matrix_logger

        logger.system(f"Инициализирован с ресурсами: {self.available}")

    def _log_matrix_state(self, description):
        if self.matrix_logger:
            self.matrix_logger.log_state(description, self)

    def set_max_claim(self, process_id, max_needs):
        with self.lock:
            self.max_claim[process_id] = np.array(max_needs, dtype=int)
            self.need[process_id] = self.max_claim[process_id] - self.allocation[process_id]
            logger.info(process_id, f"Объявил макс. потребность: {self.max_claim[process_id]}")
            self._log_matrix_state(f"P{process_id} объявил максимальную потребность")

    def _is_safe_state(self):
        # 1. Банкир считает свои деньги в сейфе.
        work = np.copy(self.available)

        # 2. Составляет список клиентов, которых еще нужно обслужить.
        finish = [False] * self.num_processes

        # 3. Повторяет попытки, пока находит кого обслужить.
        while True:
            found_process = False
            # 4. Просматривает всех клиентов.
            for i in range(self.num_processes):
                # 5. Ищет клиента (i), которого еще не обслужили И которому хватит денег из сейфа.
                if not finish[i] and np.all(self.need[i] <= work):
                    # 6. НАШЕЛ! Гипотетически обслуживает его и забирает весь его кредит.
                    #    Денег в сейфе (work) становится больше.
                    work += self.allocation[i]
                    finish[i] = True  # Помечает клиента как обслуженного.
                    found_process = True
                    break  # Начинает поиск заново с увеличенным капиталом.

            # 7. Если просмотрел всех клиентов и ни одного не смог обслужить - выхода нет.
            if not found_process:
                break

        # 8. Если в итоге все клиенты помечены как обслуженные - план существует, состояние безопасное.
        return all(finish)

    def request_resources(self, process_id, request):
        request = np.array(request, dtype=int)
        with self.lock:
            logger.request(process_id, request)

            if np.any(request > self.need[process_id]):
                logger.error(process_id, f"Запрос {request} превышает оставшуюся потребность {self.need[process_id]}")
                return False

            while np.any(request > self.available):
                logger.wait(process_id, request, self.available)
                self.condition.wait()

            self.available -= request
            self.allocation[process_id] += request
            self.need[process_id] -= request
            self._log_matrix_state(f"P{process_id} запросил {request}. Гипотетическое выделение.")

            if self._is_safe_state():
                logger.success(process_id, request, self.available)
                self._log_matrix_state(f"ЗАПРОС P{process_id} УДОВЛЕТВОРЕН. Состояние безопасное.")
                return True
            else:
                self.available += request
                self.allocation[process_id] -= request
                self.need[process_id] += request
                logger.deferred(process_id, request)
                self._log_matrix_state(f"ЗАПРОС P{process_id} ОТЛОЖЕН. Откат к предыдущему состоянию.")
                self.condition.wait()
                return False

    def release_resources(self, process_id, release):
        release = np.array(release, dtype=int)
        with self.lock:
            if np.any(release > self.allocation[process_id]):
                logger.error(process_id, f"Попытка освободить {release}, когда выделено {self.allocation[process_id]}")
                return

            self.allocation[process_id] -= release
            self.available += release
            self.need[process_id] += release
            logger.release(process_id, release, self.available)
            self._log_matrix_state(f"P{process_id} освободил {release}")

            self.condition.notify_all()
