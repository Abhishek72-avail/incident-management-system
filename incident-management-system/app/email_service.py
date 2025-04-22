# app/email_service.py
from flask_mail import Mail, Message
from flask import current_app, render_template
from threading import Thread

mail = Mail()

def init_mail(app):
    mail.init_app(app)

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body=None):
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    
    # Send email asynchronously to avoid blocking the main thread
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_incident_notification(incident, recipients):
    send_email(
        subject=f"New Incident: {incident.title}",
        recipients=recipients,
        text_body=render_template("emails/incident_notification.txt", incident=incident),
        html_body=render_template("emails/incident_notification.html", incident=incident)
    )

def send_assignment_notification(incident, recipients):
    send_email(
        subject=f"Incident Assigned: {incident.title}",
        recipients=recipients,
        text_body=render_template("emails/assignment_notification.txt", incident=incident),
        html_body=render_template("emails/assignment_notification.html", incident=incident)
    )

def send_status_update_notification(incident, recipients):
    send_email(
        subject=f"Incident Status Update: {incident.title}",
        recipients=recipients,
        text_body=render_template("emails/status_update_notification.txt", incident=incident),
        html_body=render_template("emails/status_update_notification.html", incident=incident)
    )