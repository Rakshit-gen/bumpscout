"""Sending notifications."""

SENT = []


def send_mail(to, subject):
    SENT.append((to, subject))


def format_subject(level, text):
    return f"[{level.upper()}] {text}"
