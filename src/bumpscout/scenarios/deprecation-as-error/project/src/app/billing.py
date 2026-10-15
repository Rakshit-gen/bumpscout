from datekit import parse


def days_overdue(due, today):
    return max(0, (parse(today) - parse(due)).days)
