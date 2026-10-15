"""Sending notifications."""

SENT = []


def send_email(to, subject):
    SENT.append((to, subject))


def format_subject(level, text):
    return f"[{level.upper()}] {text}"
