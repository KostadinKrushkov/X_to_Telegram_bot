from datetime import datetime


class Scheduler:
    time_format = '%H:%M:%S'
    start_time = datetime.strptime("10:00:00", time_format).time()
    end_time = datetime.strptime("23:30:00", time_format).time()

    @classmethod
    def get_available_zone(cls):
        return f'{cls.start_time} - {cls.end_time}'

    @classmethod
    def is_time_in_range(cls, current_time):
        return cls.start_time <= current_time <= cls.end_time

    @classmethod
    def is_datetime_in_time_range(cls, current_datetime):
        current_time_str = current_datetime.strftime('%H:%M:%S')
        current_time = datetime.strptime(current_time_str, cls.time_format).time()
        return cls.is_time_in_range(current_time)


if __name__ == "__main__":
    print(Scheduler.start_time)
    print(Scheduler.start_time > Scheduler.end_time)
    print(Scheduler.is_time_in_range(datetime.strptime("22:30:00", Scheduler.time_format).time()))
    print(Scheduler.is_datetime_in_time_range(datetime.now()))
