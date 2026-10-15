import notifykit

ONCALL = "oncall@example.com"


def subject(level, text):
    return notifykit.format_subject(level, text)


def page(text):
    """Only runs in production when something is on fire."""
    notifykit.send_mail(ONCALL, subject("critical", text))
