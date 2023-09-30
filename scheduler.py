from datetime import datetime


class Scheduler:
    TIME_FORMAT = '%H:%M:%S'
    DATE_FORMAT = ''

    # Deployment environment is UTC -> UTC to Sofia time is -3 Hours = 10:00 - 23:30 is 07:00 to 20:30 in UTC
    start_time = datetime.strptime("7:00:00", TIME_FORMAT).time()
    end_time = datetime.strptime("20:30:00", TIME_FORMAT).time()

    @classmethod
    def get_available_zone(cls):
        return f'{cls.start_time} - {cls.end_time}'

    @classmethod
    def is_time_in_range(cls, current_time):
        return cls.start_time <= current_time <= cls.end_time

    @classmethod
    def is_datetime_in_time_range(cls, datetime_obj):
        date_time_str = datetime_obj.strftime(cls.TIME_FORMAT)
        time_obj = datetime.strptime(date_time_str, cls.TIME_FORMAT).time()
        return cls.is_time_in_range(time_obj)

    @classmethod
    def is_datetime_from_today(cls, datetime_obj: datetime):
        current_datetime = datetime.now()
        return datetime_obj.day == current_datetime.day and datetime_obj.month == current_datetime.month and datetime_obj.year == current_datetime.year


if __name__ == "__main__":
    print(Scheduler.start_time)
    print(Scheduler.start_time > Scheduler.end_time)
    print(Scheduler.is_time_in_range(datetime.strptime("22:30:00", Scheduler.TIME_FORMAT).time()))
    print(Scheduler.is_datetime_in_time_range(datetime.now()))
