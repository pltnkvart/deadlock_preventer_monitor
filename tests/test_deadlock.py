import threading
import time

import pytest

from deadlock_prevent_monitor import DeadlockPreventerMonitor
from logger import ConsoleLogger


@pytest.fixture
def logger():
    return ConsoleLogger()


class DumbMonitor(DeadlockPreventerMonitor):
    """
    Этот монитор проверяет только наличие ресурсов, но не безопасность состояния.
    Он используется, чтобы показать, что без Алгоритма Банкира система зависнет.
    """

    def _is_safe_state(self):
        # Он всегда считает, что состояние безопасное!
        return True


class DeadlockTestThread(threading.Thread):
    def __init__(self, process_id, monitor, logger):
        super().__init__()
        self.process_id = process_id
        self.monitor = monitor
        self.logger = logger
        self.exception = None

    def run(self):
        try:
            if self.process_id == 0:
                self.monitor.set_max_claim(0, [1, 1])
                self.monitor.request_resources(0, [1, 0])
                self.logger.info(0, "Успешно получил R0.")
                time.sleep(0.1)
                self.logger.info(0, "Пытается получить R1.")
                self.monitor.request_resources(0, [0, 1])
                self.logger.info(0, "Успешно получил все ресурсы.")
                self.monitor.release_resources(0, [1, 1])
            else:
                self.monitor.set_max_claim(1, [1, 1])
                self.monitor.request_resources(1, [0, 1])
                self.logger.info(1, "Успешно получил R1.")
                time.sleep(0.1)
                self.logger.info(1, "Пытается получить R0.")
                self.monitor.request_resources(1, [1, 0])
                self.logger.info(1, "Успешно получил все ресурсы.")
                self.monitor.release_resources(1, [1, 1])
        except Exception as e:
            self.exception = e  # Сохраняем исключение для анализа в тесте
        finally:
            self.logger.info(self.process_id, "Завершен.")


def run_test_scenario(monitor_class, logger):
    monitor = monitor_class(available_resources=[1, 1], num_processes=2)
    p0 = DeadlockTestThread(0, monitor, logger)
    p1 = DeadlockTestThread(1, monitor, logger)
    p0.start()
    p1.start()
    p0.join(timeout=3)  # Уменьшим таймаут
    p1.join(timeout=3)
    return not (p0.is_alive() or p1.is_alive())


def test_dumb_monitor_causes_deadlock(logger):
    """Проверяем, что DumbMonitor приводит к deadlock (тест проваливается по таймауту)."""
    print("\n--- ТЕСТ: DumbMonitor должен вызвать deadlock ---")
    result_ok = run_test_scenario(DumbMonitor, logger)
    assert not result_ok, "Ожидался deadlock, но потоки завершились!"


def test_smart_monitor_prevents_deadlock(logger):
    """Проверяем, что DeadlockPreventerMonitor успешно предотвращает deadlock."""
    print("\n--- ТЕСТ: DeadlockPreventerMonitor должен предотвратить deadlock ---")
    result_ok = run_test_scenario(DeadlockPreventerMonitor, logger)
    assert result_ok, "Ожидалось успешное завершение, но произошел deadlock!"
